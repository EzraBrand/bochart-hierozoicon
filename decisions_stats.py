"""What did the scan check decide, by kind of item? (14-Nov-2026; from the ideas backlog of AGENTS.md)

  uv run decisions_stats.py            # table to the screen, rows to logs/decisions_stats.csv

Joins every scan-check decision (logs/review/*/decisions.tsv) to its row in the vote tables
(logs/vote_v2-*.csv: the readings of Opus = main, Flash, MDZ and the image judge) and counts, per kind of
item, who was right on the scan:

  judge   the judge's reading is what is printed (verdict OK, or APPLY with the judge's text)
  main    the first reading stays (UNDO, KEEP)
  other   the print has a third reading (APPLY with another text)

Kind = script, who agrees with the judge (F = Flash, M = MDZ), and what differs (accent, punctuation or
spacing, capital, letters). A kind where one side is right nearly always can be decided by rule; a kind
near 50% is where the scan check is needed.
"""

import csv
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "logs"


def strip_marks(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def letters(s: str) -> str:
    return "".join(c for c in strip_marks(s) if c.isalnum())


def difference(a: str, b: str) -> str:
    if a == b:
        return "same"
    if letters(a).casefold() == letters(b).casefold():
        if letters(a) != letters(b):
            return "capital"
        if strip_marks(a) == strip_marks(b):
            return "accent"
        return "punctuation"
    la, lb = letters(a), letters(b)
    if len(la) == len(lb) and sum(x != y for x, y in zip(la, lb)) == 1:
        return "one letter"
    return "letters"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    votes = {}
    for f in sorted(LOGS.glob("vote_v2-*-*.csv")):
        if f.name.count(".") > 1:  # test runs (vote_v2-408-429.argon-opus.csv)
            continue
        for r in csv.DictReader(f.open(encoding="utf-8-sig")):
            votes.setdefault((r["page"], r["main"]), r)
    rows, missing = [], 0
    for g in sorted((LOGS / "review").iterdir()):
        d = g / "decisions.tsv"
        if not d.exists():
            continue
        for r in csv.DictReader(d.open(encoding="utf-8"), delimiter="\t"):
            v = votes.get((r["page"], r["main"]))
            verdict, text = r["verdict"].strip(), (r.get("text") or "").strip()
            if v is None or verdict in ("SKIP", ""):
                missing += 1
                continue
            judge = v["judge"]
            support = ("F" if judge and judge == v["flash"] else "") + ("M" if judge and judge == v["mdz"] else "")
            if verdict == "OK" or (verdict in ("APPLY", "OTHER") and text and text in (judge, v["new"])):
                right = "judge"
            elif verdict in ("UNDO", "KEEP", "UNSURE"):
                right = "main"
            else:
                right = "other"
            rows.append({"group": g.name, "page": r["page"], "script": v["script"], "support": support or "none",
                         "difference": difference(v["main"], judge) if judge else "no judge text",
                         "right": right, "verdict": verdict, "main": v["main"], "judge": judge,
                         "flash": v["flash"], "mdz": v["mdz"], "text": text})
    with (LOGS / "decisions_stats.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} decisions joined ({missing} without a vote row or skipped)\n")
    for keys in (("support",), ("script",), ("difference",), ("support", "difference"), ("script", "support", "difference")):
        t = defaultdict(lambda: defaultdict(int))
        for r in rows:
            t[tuple(r[k] for k in keys)][r["right"]] += 1
        print(" / ".join(keys))
        for k, c in sorted(t.items(), key=lambda kv: -sum(kv[1].values())):
            n = sum(c.values())
            if n < 8:
                continue
            print(f"  {' / '.join(k):42} n={n:4}  judge {100 * c['judge'] / n:3.0f}%  main {100 * c['main'] / n:3.0f}%  "
                  f"other {100 * c['other'] / n:3.0f}%")
        print()


if __name__ == "__main__":
    main()
