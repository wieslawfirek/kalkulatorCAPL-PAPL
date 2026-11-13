import csv
import io
import json
import math
import re
import os
import base64
import hmac
import zipfile
from datetime import date, datetime
from individual import report
from aggregate import aggregate_pdf, group_history, reference_rosters
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent
METRICS = dict(zip(
    ('Wynik CAMSA', 'Wynik Beep Testu', 'Wynik Deski', 'Średnia dzienna liczba kroków',
     'Kompetencje fizyczne (pkt)', 'Zachowania codzienne (pkt)',
     'Motywacja i pewność siebie (pkt)', 'Wiedza i zrozumienie (pkt)', 'Ogólny wynik alfabetyzacji ruchowej (pkt)'),
    ('camsa_skill_time_score', 'pacer_20m_laps', 'plank_time', 'step_average',
     'pc_score', 'db_score', 'mc_score', 'ku_score', 'capl_score')
))
FIELDS = ('Identyfikator ucznia', 'Imię', 'Nazwisko', 'Płeć', 'Szkoła', 'Klasa',
          'Numer pomiaru', 'Data urodzenia', 'Data wykonania testu')
LEVELS = ('Początkujący', 'Dokonujący postępów', 'Sprawny', 'Wyróżniający się')
TURNS = {1: 'Pretest', 2: 'Posttest', 3: 'Pomiar po roku'}
with (ROOT / 'normy.csv').open(encoding='utf-8', newline='') as f:
    NORMS = {(int(r['sex']), int(r['age']), r['metric']): (
        int(r['precision']), float(r['threshold1']), float(r['threshold2']), float(r['threshold3'])
    ) for r in csv.DictReader(f)}

def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

def category(sex, age, metric, score):
    norm = NORMS.get((sex, age, metric))
    if norm is None or score is None:
        return None
    precision, first, second, third = norm
    score = round(score, precision)
    if score < first:
        return 0
    if score <= second:
        return 1
    if score <= third:
        return 2
    return 3

def import_excel(raw):
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if sum(entry.file_size for entry in archive.infolist()) > 64 * 1024 * 1024:
                raise ValueError('Rozpakowany arkusz przekracza 64 MB.')
        workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except (zipfile.BadZipFile, OSError, KeyError) as exc:
        raise ValueError('Wybierz prawidłowy plik .xlsx.') from exc
    records = []
    seen = set()
    try:
        if 'Wyniki pomiarów' not in workbook.sheetnames:
            raise ValueError('Brakuje arkusza „Wyniki pomiarów”.')
        sheet = workbook['Wyniki pomiarów']
        if (sheet.max_row or 0) > 30000 or (sheet.max_column or 0) > 100:
            raise ValueError('Arkusz przekracza limit 30 000 wierszy lub 100 kolumn.')
        source = sheet.values
        header = [v.strip() if isinstance(v, str) else v for v in next(source, ())]
        required = (*FIELDS, *METRICS)
        missing = [field for field in required if header.count(field) != 1]
        if missing:
            raise ValueError('Brakujące lub powtórzone nagłówki: ' + ', '.join(missing))
        positions = {field: header.index(field) for field in required}
        for i, row in enumerate(source, 2):
            values = [row[positions[field]] for field in required]
            if not any(value not in (None, '') for value in values):
                continue
            student, first, last, sex, school, classroom, turn, birth, test, *scores = values
            scores = [None if value == '' else value for value in scores]
            if not all(value is not None and str(value).strip() for value in (student, school, classroom)):
                raise ValueError(f'Wiersz {i}: uzupełnij identyfikator, szkołę i klasę.')
            if turn not in (1, 2, 3) and turn not in ('1', '2', '3'):
                raise ValueError(f'Wiersz {i}: numer pomiaru musi wynosić 1, 2 lub 3.')
            if sex not in (None, '', 1, 2, '1', '2'):
                raise ValueError(f'Wiersz {i}: kod płci musi wynosić 1 lub 2.')
            if any(value is not None and not number(value) for value in scores):
                raise ValueError(f'Wiersz {i}: wynik musi być liczbą albo pustą komórką.')
            student, school, classroom = (str(v).strip() for v in (student, school, classroom))
            turn = int(turn)
            if (student, turn) in seen:
                raise ValueError(f'Wiersz {i}: powtórzony identyfikator w tym samym pomiarze.')
            seen.add((student, turn))
            age = None
            if isinstance(birth, date) and isinstance(test, date):
                birth = birth.date() if isinstance(birth, datetime) else birth
                test = test.date() if isinstance(test, datetime) else test
                if test < birth:
                    raise ValueError(f'Wiersz {i}: data testu poprzedza datę urodzenia.')
                age = test.year - birth.year - ((test.month, test.day) < (birth.month, birth.day))
            records.append(dict(student=student, name=' '.join(str(v).strip() for v in (first, last) if v) or student,
                sex=int(sex) if sex else None, age=age, test=test if isinstance(test, date) else None, school=school, classroom=classroom, turn=turn,
                scores=scores, levels=[category(int(sex) if sex else None, age, m, v)
                                      for m, v in zip(METRICS.values(), scores)]))
    finally:
        workbook.close()
    if not any(has_results(record) for record in records):
        raise ValueError('Arkusz nie zawiera wyników do raportowania.')
    return records

def has_results(record):
    return any(value is not None for value in record['scores'])

def individual(history, use_ai=True):
    return report([record for record in history if has_results(record)], NORMS, METRICS.values(), use_ai=use_ai)

def download_template():
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.utils import get_column_letter

    book = Workbook()
    sheet = book.active
    sheet.title = 'Wyniki pomiarów'
    sheet.append([*FIELDS, 'Wiek w dniu testu (pełne lata)', *METRICS])
    sheet.freeze_panes = 'D2'
    sheet.row_dimensions[1].height = 33
    for cell in sheet[1]:
        cell.fill = PatternFill('solid', fgColor='00685F')
        cell.font = Font(color='FFFFFF', bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical='center')
        sheet.column_dimensions[get_column_letter(cell.column)].width = 24
    for column, allowed in (('D', '"1,2"'), ('G', '"1,2,3"')):
        validation = DataValidation(type='list', formula1=allowed, allow_blank=True, showErrorMessage=True)
        sheet.add_data_validation(validation)
        validation.add(f'{column}2:{column}30000')
    for column in ('H', 'I'):
        sheet.column_dimensions[column].number_format = 'dd.mm.yyyy'
    guide = book.create_sheet('Instrukcja')
    for line in ('Jeden wiersz to jeden pomiar ucznia. Zachowaj identyfikator we wszystkich turach.',
                 'Płeć: 1 = chłopiec, 2 = dziewczynka.',
                 'Numer pomiaru: 1 = pretest, 2 = posttest, 3 = pomiar po roku.',
                 'Daty wpisuj jako daty Excela. Kolumnę wieku możesz zostawić pustą, wiek obliczy generator.',
                 'CAMSA: łączny wynik punktowy za czas i umiejętności.',
                 'Beep Test: liczba odcinków 20 m. Deska: czas w sekundach.',
                 'Brak wyniku pozostaw pusty.'):
        guide.append([line])
    guide.column_dimensions['A'].width = 100
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()

class App(BaseHTTPRequestHandler):
    def authorize(self):
        password = os.getenv('PAPL_PASSWORD')
        if not password and not os.getenv('VERCEL'):
            return True
        if password:
            expected = 'Basic ' + base64.b64encode(f'papl:{password}'.encode()).decode()
            if hmac.compare_digest(self.headers.get('Authorization', ''), expected):
                return True
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="Raporty PAPL"')
        else:
            self.send_response(503)
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(b'Dostep wymaga konfiguracji hasla PAPL_PASSWORD.')
        return False

    def send(self, body, kind, status=200, filename=None, inline=False):
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        if filename:
            disposition = 'inline' if inline else 'attachment'
            self.send_header('Content-Disposition', f'{disposition}; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def json(self, data, status=200):
        self.send(json.dumps(data, ensure_ascii=False).encode(), 'application/json; charset=utf-8', status)

    def route(self):
        url = urlsplit(self.path)
        return parse_qs(url.query).get("route", [url.path])[0]

    def do_GET(self):
        if not self.authorize():
            return
        path = self.route()
        if path in ('/alfabet.jpg', '/wfz-awf.jpg'):
            return self.send((ROOT / path[1:]).read_bytes(), 'image/jpeg')
        if path == '/szablon.xlsx':
            return self.send(download_template(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename='Szablon_wynikow_PAPL.xlsx')
        if path in ('/', '/api/handler'):
            return self.send((ROOT/'app-page.html').read_bytes(), 'text/html; charset=utf-8')
        self.send_error(404)

    def do_POST(self):
        if not self.authorize():
            return
        if self.headers.get('X-PAPL-Request') != '1':
            return self.send_error(403)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 4 * 1024 * 1024:
                raise ValueError('Wybierz plik .xlsx do 4 MB.')
            records = import_excel(self.rfile.read(size))
            path = self.route()
            if path == '/import':
                keys = ('student', 'name', 'school', 'classroom', 'turn')
                measured = [r for r in records if has_results(r)]
                return self.json({'roster': [{k:r[k] for k in keys} for r in reference_rosters(records)],
                                  'rows': [{k:r[k] for k in keys} for r in measured],
                                  'ageMissing':sum(r['age'] is None for r in measured),
                                  'sexMissing':sum(r['sex'] is None for r in measured)})
            if path != '/report':
                return self.send_error(404)
            raw = self.headers.get('X-PAPL-Selection','')
            fields = {k:v[0] for k,v in parse_qs(raw).items()}
            school, room, student, mode = (fields.get(k,'') for k in ('school','classroom','student','mode'))
            selected = [r for r in reference_rosters(records) if r['school'] == school
                        and (mode=='school' or r['classroom']==room)]
            history = {}
            for record in records:
                history.setdefault(record['student'], []).append(record)
            if mode=='individual':
                if not any(r['student']==student for r in selected):
                    raise ValueError('Wybierz ucznia z listy.')
                return self.send(individual(history[student]),'application/pdf',filename='raport-ucznia.pdf',inline=True)
            if not selected or mode not in ('school','class','bundle'):
                raise ValueError('Brak danych dla wybranego zakresu.')
            title = school if mode=='school' else f'{school} · klasa {room}'
            report_bytes = aggregate_pdf(group_history(records,selected),selected,title,by_class=mode=='school', use_ai=mode!='bundle')
            if mode!='bundle' or fields.get('preview')=='1':
                return self.send(report_bytes,'application/pdf',filename='raport-zbiorczy.pdf',inline=True)
            out = io.BytesIO()
            with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('raport-klasy.pdf', report_bytes)
                for i,r in enumerate(selected,1):
                    safe = re.sub(r'[^A-Za-z0-9_-]','_',r['student'])[:80]
                    archive.writestr(f'indywidualne/{i:03d}-{safe}.pdf',individual(history[r['student']], use_ai=False))
            if out.tell()>4*1024*1024:
                raise ValueError('Paczka jest za duża. Pobierz raport zbiorczy i raporty uczniów osobno.')
            return self.send(out.getvalue(),'application/zip',filename='raporty-klasy.zip')
        except ValueError as exc:
            return self.json({'error':str(exc)},400)

    def log_message(self,*_):
        pass

if __name__ == '__main__':
    HTTPServer(('127.0.0.1',8765),App).serve_forever()
