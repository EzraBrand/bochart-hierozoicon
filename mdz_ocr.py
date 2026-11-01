"""The MDZ (Munich) OCR layer as a baseline engine: hOCR -> data/ocr/mdz/{page}.json and .md.

  py -3.13 mdz_ocr.py                 # all pages in data/mdz_hocr/
  py -3.13 mdz_ocr.py v2-0409 v2-0428

The hOCR files are fetched by fetch.py (canvas seeAlso: https://api.digitale-sammlungen.de/ocr/{id}/{canvas}).
Each ocrx_block becomes one block (type "body": the hOCR has no block types), one line per ocr_line.
Words are joined with the spaces of the hOCR. No language runs (the page says lang="la").
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DATA = Path(__file__).parent / "data"
SRC = DATA / "mdz_hocr"
OUT = DATA / "ocr" / "mdz"

BLOCK = re.compile(r'<div class="ocrx_block".*?</div>', re.S)
LINE = re.compile(r'<span class="ocr_line"[^>]*>(.*?)</span>\s*(?=<span class="ocr_line"|</p>)', re.S)
TAG = re.compile(r"<[^>]+>")


def parse(text: str) -> list[dict]:
    blocks = []
    for b in BLOCK.findall(text):
        lines = [html.unescape(TAG.sub("", ln)).strip() for ln in LINE.findall(b)]
        lines = [ln for ln in lines if ln]
        if lines:
            blocks.append({"type": "body", "marker": "", "runs": [{"lang": "lat", "text": "\n".join(lines)}],
                           "text": "\n".join(lines)})
    return blocks


def main():
    p = argparse.ArgumentParser()
    p.add_argument("pages", nargs="*")
    a = p.parse_args()
    files = [SRC / f"{k}.hocr" for k in a.pages] if a.pages else sorted(SRC.glob("*.hocr"))
    OUT.mkdir(parents=True, exist_ok=True)
    for f in files:
        blocks = parse(f.read_text(encoding="utf-8"))
        key = f.stem
        (OUT / f"{key}.json").write_text(json.dumps({"page": key, "engine": "mdz", "blocks": blocks},
                                                    ensure_ascii=False, indent=1), encoding="utf-8")
        (OUT / f"{key}.md").write_text("\n\n".join(b["text"] for b in blocks) + "\n", encoding="utf-8")
        print(f"{key}: {len(blocks)} blocks, {sum(len(b['text']) for b in blocks)} chars", flush=True)


if __name__ == "__main__":
    main()
