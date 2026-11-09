"""List chapter heads (CAP. ..., LIBER ...) in the MDZ hOCR of vol. 2, canvases FIRST..LAST (fetches missing hOCR).

  uv run find_chapters.py 470 560      # canvas, page label, head, the first words after it
"""
import html
import re
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import fetch

sys.stdout.reconfigure(encoding="utf-8")
cs = fetch.canvases(2)
lo, hi = int(sys.argv[1]), int(sys.argv[2])
PAT = re.compile(r"(C\s*A\s*P\s*\.?\s*[XVIL]+\s*\.|LIBER\s+\w+)")
for c in cs[lo - 1:hi]:
    key = fetch.page_key(c)
    p = fetch.DATA / "mdz_hocr" / f"{key}.hocr"
    if not p.exists() and c["hocr"]:
        fetch.download(c["hocr"], p)
    t = html.unescape(re.sub(r"<[^>]+>", " ", p.read_text(encoding="utf-8")))
    for m in PAT.finditer(t):
        print(c["canvas"], c["label"], " ".join(m.group(0).split()), "|",
              " ".join(t[m.end():m.end() + 140].split())[:110], flush=True)
