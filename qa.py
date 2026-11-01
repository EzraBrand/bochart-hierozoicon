"""Checks on the OCR of a range of pages, before joining and translating them.

  uv run qa.py 408 429                                   # vol. 2; writes logs/qa_v2-408-429.csv
  uv run qa.py 408 429 --main "or-claude-opus-5.5@low" --second "or-gemini-3.8-flash@low"

Per page: blocks, characters per script, the length against the MDZ OCR and the second engine
(a low ratio means dropped text: a column or a note lost), the margin column marks (they must
run without a gap from page to page), note marks in the text against notes (Rosenmüller's (n),
Bochart's letters), footnote blocks before the body text, and the last and first words at each
page break (for the join check by eye). Prints the pages that need a look.
Ported from lewysohn-zoologie.
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import eval as ev

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
OCR = ROOT / "data" / "ocr"
MARGIN = re.compile(r"⟦p\. (\d+)⟧")
R_MARK = re.compile(r"\^\{\((\d+)\)\}")  # Rosenmüller: ^{(13)}
B_MARK = re.compile(r"\^\{([a-z])\)\}")   # Bochart: ^{c)}
SENTENCE_END = re.compile(r"[.!?:;)\]]\s*$")


def load(engine: str, key: str) -> list[dict] | None:
    f = OCR / engine / f"{key}.json"
    return json.loads(f.read_text(encoding="utf-8"))["blocks"] if f.exists() else None


def size(blocks: list[dict]) -> int:
    ev.LOOSE = True
    return len(re.sub(r"\s", "", ev.norm("".join(b["text"] for b in blocks if b["type"] != "furniture"))))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("first", type=int)
    p.add_argument("last", type=int)
    p.add_argument("--vol", type=int, default=2)
    p.add_argument("--main", default="or-claude-opus-5.5@low", help="OCR folder in data/ocr/")
    p.add_argument("--second", default="or-gemini-3.8-flash@low")
    a = p.parse_args()
    rows, prev_end, prev_col = [], None, None
    for page in range(a.first, a.last + 1):
        key = f"v{a.vol}-{page:04d}"
        blocks = load(a.main, key)
        if blocks is None:
            rows.append({"page": key, "problem": "no OCR"})
            continue
        main = [b for b in blocks if b["type"] in ("body", "heading")]
        notes = [b for b in blocks if b["type"] == "footnote"]
        text = "\n".join(b["text"] for b in blocks if b["type"] != "furniture")
        maintext = "\n".join(b["text"] for b in main)
        n = size(blocks)
        ratios = {}
        for eng in ("mdz", a.second):
            other = load(eng, key)
            ratios[eng] = round(n / size(other), 2) if other else ""
        cols = [int(c) for c in MARGIN.findall(text)]
        rmarks, bmarks = R_MARK.findall(maintext), B_MARK.findall(maintext)
        rnotes = [b["marker"] for b in notes if re.fullmatch(r"\(\d+\)", b["marker"])]
        bnotes = [b["marker"] for b in notes if re.fullmatch(r"[a-z]\)", b["marker"])]
        scripts = {}
        for ch in text:
            s = ev.script(ch)
            scripts[s] = scripts.get(s, 0) + 1
        problems = []
        body = [b for b in blocks if b["type"] != "furniture"]
        first = next((i for i, b in enumerate(body) if b["type"] in ("body", "heading")), len(body))
        if any(b["type"] == "footnote" and b["marker"] for b in body[:first]):
            problems.append("marked footnote before the body text")
        for eng, r in ratios.items():
            if r and not 0.9 <= r <= 1.1:
                problems.append(f"length {r}x {eng}")
        if cols and prev_col is not None and cols[0] != prev_col + 1:
            problems.append(f"margin {cols} after {prev_col}")
        if cols != sorted(cols) or any(b - a_ != 1 for a_, b in zip(cols, cols[1:])):
            problems.append(f"margin marks {cols}")
        if sorted(rmarks, key=int) != sorted((m.strip("()") for m in rnotes), key=int):
            problems.append(f"R marks {rmarks}, notes {rnotes}")
        if sorted(bmarks) != sorted(m.rstrip(")") for m in bnotes):
            problems.append(f"B marks {bmarks}, notes {bnotes}")
        start = main[0]["text"].strip().split("\n")[0][:50] if main else ""
        end = main[-1]["text"].strip().split("\n")[-1][-50:] if main else ""
        rows.append({"page": key, "blocks": len(blocks), "chars": n,
                     **{s: scripts.get(s, 0) for s in ("Latin", "Greek", "Hebrew", "Arabic", "Syriac")},
                     "ratio_mdz": ratios["mdz"], "ratio_second": ratios[a.second],
                     "margin": " ".join(map(str, cols)), "r_marks": len(rmarks), "r_notes": len(rnotes),
                     "b_marks": len(bmarks), "b_notes": len(bnotes),
                     "join": "" if prev_end is None else
                     ("break" if SENTENCE_END.search(prev_end) else "continue"),
                     "prev_end": prev_end or "", "start": start, "problem": "; ".join(problems)})
        prev_end = end
        prev_col = cols[-1] if cols else prev_col
    out = ROOT / "logs" / f"qa_v{a.vol}-{a.first}-{a.last}.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(max(rows, key=len).keys()))
        w.writeheader()
        w.writerows(rows)
    bad = [r for r in rows if r.get("problem")]
    print(f"{len(rows)} pages, {sum(r.get('chars', 0) for r in rows)} characters; "
          f"{len(bad)} to look at; wrote {out}")
    for r in bad:
        print(f"  {r['page']}: {r['problem']}")


if __name__ == "__main__":
    main()
