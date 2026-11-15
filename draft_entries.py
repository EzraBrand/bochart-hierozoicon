"""Draft the fixed work of a tranche from the chapter heads in the OCR (15-Nov-2026): for each "CAP. N." the
pages, the start and end patterns, first_col, the column range of 1663 and the Latin summary of the head. The
agent then writes only the slug, the English title, the subject ("about") and the fixed terms.

  uv run draft_entries.py 3 1 125 --book "Part 2, Book 2"     # volume, first page, last page

Reads the voted OCR where it is, else the Opus OCR (the MDZ OCR misses some heads: ch. 29 of this tranche,
chs. 22-23 of tranche 5). first_col is the last column mark before the head; it is left out when the head's own
block carries the mark (entry.py then takes it from the text). The last chapter's end pattern is a guess
("LIBER"): look at the page.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
DATA = Path(__file__).resolve().parent / "data" / "ocr"
HEAD = re.compile(r"^\s*(?:<i>)?C\s?A\s?P\s?\.\s*([XVILC]+)\s*\.", re.M)
COL = re.compile(r"⟦p\. (\d+)⟧")
ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def arabic(r: str) -> int:
    n = 0
    for a, b in zip(r, r[1:] + "I"):
        n += -ROMAN[a] if ROMAN[a] < ROMAN[b] else ROMAN[a]
    return n


def main():
    p = argparse.ArgumentParser()
    p.add_argument("vol", type=int)
    p.add_argument("first", type=int)
    p.add_argument("last", type=int)
    p.add_argument("--book", default="Part 2, Book 2")
    a = p.parse_args()
    heads, col = [], None  # (page, numeral, summary, first_col or None, col at the head)
    cols_at = {}
    for page in range(a.first, a.last + 1):
        key = f"v{a.vol}-{page:04d}"
        f = next((d / f"{key}.json" for d in (DATA / "or-claude-opus-5.5@low+vote", DATA / "or-claude-opus-5.5@low")
                  if (d / f"{key}.json").exists()), None)
        if f is None:
            sys.exit(f"{key}: no OCR yet")
        blocks = [b for b in json.loads(f.read_text(encoding="utf-8"))["blocks"] if b["type"] not in ("furniture", "footnote")]
        for i, b in enumerate(blocks):
            m = HEAD.search(b["text"])
            if m:
                own = COL.search(b["text"][m.start():])
                nxt = " ".join(x["text"] for x in blocks[i:i + 3])
                summary = " ".join(nxt[nxt.index(m.group(0)) + len(m.group(0)):].split())[:260]
                heads.append({"page": page, "num": m.group(1), "summary": summary,
                              "first_col": None if own else col, "col": int(own.group(1)) if own else col})
            for c in COL.finditer(b["text"]):
                col = int(c.group(1))
        cols_at[page] = col
    for h, nxt in zip(heads, heads[1:] + [None]):
        end_page = nxt["page"] if nxt else a.last
        last = end_page if nxt else a.last
        # the chapter's last page: the next head's page, unless that head is the first text of its page
        n = arabic(h["num"])
        end = rf'^CAP\.\s*{nxt["num"]}\.' if nxt else "LIBER"
        end_col = (nxt["col"] if nxt else cols_at.get(end_page)) or "?"
        fc = f', "first_col": {h["first_col"]}' if h["first_col"] else ""
        print(f'# ch. {n} ({h["num"]}), pp. {h["page"]}-{last}: {h["summary"]}')
        print(f'    "SLUG": {{"vol": {a.vol}, "pages": list(range({h["page"]}, {last + 1})),\n'
              f'             "title": "{a.book}, chapter {n}: TITLE (vol. {a.vol}, pp. {h["page"]}–{last})",\n'
              f'             "start": r"^CAP\\.\\s*{h["num"]}\\.", "end": r"{end}"{fc},\n'
              f'             "about": "ABOUT",\n             "terms": TERMS}},')
        print(f'    {{"slug": "SLUG", "kind": "entry", "entry": "SLUG", "vol": {a.vol}, "pages": list(range({h["page"]}, {last + 1})),\n'
              f'     "title": "{a.book}, chapter {n}: SHORT",\n'
              f'     "sub": "Vol. {a.vol}, pp. {h["page"]}–{last} · cols. {h["col"] or "?"}–{end_col} of 1663 (Part 2) · SUB"}},\n')
    nums = [arabic(h["num"]) for h in heads]
    gaps = [n for n in range(nums[0], nums[-1]) if n not in nums] if nums else []
    print(f"# {len(heads)} heads: {nums}" + (f"; MISSING {gaps}: grep the OCR for the head" if gaps else ""))


if __name__ == "__main__":
    main()
