import re
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader

ROOT = Path(__file__).resolve().parent
GREEN = HexColor('#174A3A')
INK = HexColor('#173029')
MUTED = HexColor('#52655B')
RULE = HexColor('#D7E2DA')
PAPER = HexColor('#F4F7F4')
BANDS = tuple(map(HexColor, ('#F2BAAA', '#F4D794', '#A9D7AD', '#68B8A2')))
LOGOS = (('alfabet.jpg', 42, 115), ('wfz-awf.jpg', 168, 48))


_SINGLE_LETTER = re.compile(r"(?<!\w)([aiouwzAIUOWZ]) +(?=\S)")

def keep_single_letters(text):
    return _SINGLE_LETTER.sub(lambda match: match[1] + "\u00a0", text)


def report_frame(canvas, width, height, page):
    canvas.setFillColor(PAPER)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.rect(0, height - 47, width, 47, fill=1, stroke=0)
    canvas.setFillColor(GREEN)
    canvas.rect(0, height - 49, width, 2, fill=1, stroke=0)
    for name, x, max_width in LOGOS:
        image = ImageReader(str(ROOT / name))
        iw, ih = image.getSize()
        scale = min(max_width / iw, 36 / ih)
        canvas.drawImage(image, x, height - 24 - ih * scale / 2, iw * scale, ih * scale)
    canvas.setFont('PAPL', 9)
    canvas.drawRightString(width - 42, height - 28, 'Polskie normy PAPL')
    canvas.setFillColor(MUTED)
    canvas.drawString(42, 24, 'Ocena alfabetyzacji ruchowej')
    canvas.drawRightString(width - 42, 24, str(page))
