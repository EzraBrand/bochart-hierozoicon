"""List the words where one OCR engine differs from the others, to check them on the scan.

  uv run diffwords.py v2-0422 --main "or-claude-opus-5.5@low"

Compares the main engine's text with every other engine in data/ocr/, word by word (after the
eval.py --loose normalization; <i> tags, margin marks and ^{} wrappers removed; ſ -> s). Prints
each differing stretch once, with the engines that read it otherwise. A help for making a gold
page, not a score.
"""

import argparse
import difflib
import json
import sys
from pathlib import Path

import eval as ev

sys.stdout.reconfigure(encoding="utf-8")

DATA = Path(__file__).parent / "data"


def words(engine: str, page: str) -> list[str]:
    f = DATA / "ocr" / engine / f"{page}.json"
    if not f.exists():
        return []
    return ev.norm(ev.page_text(json.loads(f.read_text(encoding="utf-8")))).replace("ſ", "s").split()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("page")
    p.add_argument("--main", required=True)
    a = p.parse_args()
    ev.LOOSE = True
    main = words(a.main, a.page)
    diffs = {}  # (main index, main stretch) -> {other reading: [engines]}
    for eng in sorted(x.name for x in (DATA / "ocr").iterdir() if not x.name.startswith("_")):
        if eng == a.main:
            continue
        other = words(eng, a.page)
        sm = difflib.SequenceMatcher(None, main, other, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                continue
            key = (i1, " ".join(main[max(i1 - 1, 0):i2 + 1]))
            diffs.setdefault(key, {}).setdefault(" ".join(other[max(j1 - 1, 0):j2 + 1]), []).append(eng)
    for (i, mw), others in sorted(diffs.items()):
        print(f"{i:5d}  {mw}")
        for ow, engs in others.items():
            print(f"         {ow}   <- {', '.join(e.split('@')[0].removeprefix('or-') for e in engs)}")


if __name__ == "__main__":
    main()
