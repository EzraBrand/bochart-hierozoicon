"""Crops for Hebrew words to check on the scan: for (page, word) find the concordance row, then the hOCR line
that best matches the Latin around it, and save lines i-1..i+1 at 3x. Sheets of 4 crops.
uv run hebcrops.py OUTNAME page:word page:word ..."""
import csv, re, sys
from PIL import Image, ImageDraw, ImageFont
from rapidfuzz import fuzz

sys.stdout.reconfigure(encoding="utf-8")
out = sys.argv[1]
occ = list(csv.DictReader(open("data/concordance/hebrew.csv", encoding="utf-8-sig")))
font = ImageFont.truetype("arial.ttf", 50)
crops = []
for n, spec in enumerate(sys.argv[2:], 1):
    page, word = spec.split(":")
    page = int(page)
    rows = sorted((r for r in occ if page <= int(r["page"]) <= page + 4 and word in r["hebrew"]), key=lambda r: int(r["page"]))
    if not rows:
        print(n, spec, "not in the concordance")
        continue
    r = rows[0]
    page = int(r["page"])
    ctx = (r["before"][-45:] + " " + r["after"][:45])
    t = open(f"data/mdz_hocr/v2-{page:04d}.hocr", encoding="utf-8").read()
    L = [(tuple(map(int, m.groups()[:4])), re.sub(r"<[^>]+>", "", m.group(5)).replace("ſ", "s"))
         for m in re.finditer(r'class="ocr_line" title="bbox (\d+) (\d+) (\d+) (\d+)"[^>]*>(.*?)</span>\s*(?=<span class="ocr_line"|</p>)', t, re.S)]
    lat = re.sub(r"[^A-Za-z ,.]", " ", ctx)
    i = max(range(len(L)), key=lambda k: fuzz.partial_ratio(lat, L[k][1]))
    sel = L[max(i - 1, 0):i + 2]
    im = Image.open(f"data/raw/v2-{page:04d}.jpg").convert("L")
    box = (max(min(b[0][0] for b in sel) - 20, 0), sel[0][0][1] - 10, min(max(b[0][2] for b in sel) + 20, im.width), sel[-1][0][3] + 10)
    c = im.crop(box)
    crops.append((n, c.resize((c.width * 3, c.height * 3), Image.LANCZOS)))
    print(n, page, spec, "|", r["hebrew"], "|", r["romanization"], "|", ctx)
for s in range(0, len(crops), 4):
    ims = crops[s:s + 4]
    W = max(c.width for _, c in ims) + 120
    H = sum(c.height for _, c in ims) + 8 * len(ims)
    sheet = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(sheet)
    y = 0
    for n, c in ims:
        sheet.paste(c, (120, y))
        d.text((10, y + c.height // 2 - 25), str(n), fill=0, font=font)
        y += c.height + 8
        d.line((0, y - 4, W, y - 4), fill=0, width=3)
    sheet.save(f"logs/review/heb/{out}_{s // 4 + 1}.jpg", quality=90)
    print("sheet", s // 4 + 1, sheet.size)
