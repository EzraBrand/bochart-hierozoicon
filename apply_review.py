"""Turn the scan-check decisions (logs/review/*/decisions.tsv, written by the readers) into the lines
for vote.ACCEPT, vote.REJECT and entry.FIXES, and print them for pasting (10-Nov-2026; the one-off
logs/apply_review.py of tranche 1 made general).

  uv run apply_review.py 524 590 --tag "tranche 2 (scan check 10-Nov-2026)"

Verdicts: OK (a change is right: nothing to do), UNDO (a change is wrong: REJECT), APPLY with text =
the proposal (a review item is right: ACCEPT), APPLY/OTHER with another text (the print differs:
FIXES, old -> text), KEEP, SKIP, UNSURE (nothing; UNSURE is listed). A FIXES pair must be unique on
the page: the word is widened with its neighbours from the line until it is.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent
VOTED = ROOT / "data" / "ocr" / "or-claude-opus-5.5@low+vote"


def unique_pair(page: int, old: str, new: str, line: str) -> tuple[str, str] | None:
    blocks = [b["text"] for b in json.loads((VOTED / f"v2-{page:04d}.json").read_text(encoding="utf-8"))["blocks"]]
    words = line.split()
    cands = [old]
    if old in words:
        i = words.index(old)
        cands += [" ".join(words[max(i - k, 0):i + k + 1]) for k in range(1, 4)]
    for c in cands:
        if sum(b.count(c) for b in blocks) == 1:
            return c, c.replace(old, new, 1)
    return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("first", type=int)
    p.add_argument("last", type=int)
    p.add_argument("--tag", default="scan check")
    p.add_argument("--groups", nargs="*", help="review folders to read (default: all with a decisions.tsv)")
    a = p.parse_args()
    accept, reject, fixes, unsure, bad = [], [], {}, [], []
    for g in sorted((ROOT / "logs" / "review").iterdir()):
        if not (g / "decisions.tsv").exists() or (a.groups and g.name not in a.groups):
            continue
        items = {r["id"]: r for r in csv.DictReader(open(g / "items.tsv", encoding="utf-8"), delimiter="\t")}
        for d in csv.DictReader(open(g / "decisions.tsv", encoding="utf-8"), delimiter="\t"):
            r = items.get(d["id"])
            if r is None or not a.first <= int(r["page"][3:]) <= a.last:
                continue
            v, t, note = d["verdict"].strip(), (d.get("text") or "").strip(), (d.get("note") or "").strip()
            key = (r["page"], r["main"])
            if v == "UNDO":
                reject.append((key, note or "scan check"))
            elif v == "UNSURE":
                unsure.append((g.name, d["id"], r["page"], r["main"], r["new"], note))
            elif v in ("APPLY", "OTHER"):
                if r["kind"] == "review" and t and t == r["new"]:
                    accept.append(key)
                elif t and t != r["main"]:
                    # the text in the voted page is `new` for a change, `main` for a review item
                    old = r["new"] if r["kind"] == "change" and r["new"] else r["main"]
                    if r["kind"] == "change":
                        reject.append((key, f"print {t} ({note})" if note else f"print {t}"))
                        old = r["main"]
                    pair = unique_pair(int(r["page"][3:]), old, t, r["line"])
                    if pair:
                        fixes.setdefault(int(r["page"][3:]), []).append(pair)
                    else:
                        bad.append((r["page"], old, t))
    print(f"# vote.ACCEPT ({len(accept)}): paste into ACCEPT\n    # {a.tag}")
    for pg, w in accept:
        print(f"    ({pg!r}, {w!r}),")
    print(f"\n# vote.REJECT ({len(reject)}): paste into REJECT\n    # {a.tag}")
    for (pg, w), why in reject:
        print(f"    ({pg!r}, {w!r}): {why!r},")
    print(f"\n# entry.FIXES ({sum(len(v) for v in fixes.values())} pairs on {len(fixes)} pages): paste into FIXES "
          f"(append to a page's list if it has one)\n    # {a.tag}: the print differs from the vote's text")
    for pg in sorted(fixes):
        print(f"    {pg}: {fixes[pg]!r},")
    if bad:
        print(f"\n# NOT UNIQUE / NOT FOUND in the voted page ({len(bad)}): fix by hand")
        for b in bad:
            print("   ", b)
    print(f"\n# UNSURE ({len(unsure)}): look at the crop")
    for u in unsure:
        print("   ", " | ".join(u))


if __name__ == "__main__":
    main()
