"""Crops for the scan check of a vote: one 2x line crop per review item and per applied change.

  uv run review_pack.py 455 524 --group B:463-487 --group C:488-505
  -> logs/review/{group}/NNN.jpg + items.tsv (id, page, kind, outcome, main, flash, mdz, judge, new, line, image)

The check itself is done by reading the crops (09-Nov-2026: one subagent per group; its answers in
logs/review/{group}/decisions.tsv: OK / UNDO for changes, APPLY / KEEP for review items, SKIP, UNSURE).
The answers go into vote.ACCEPT / vote.REJECT, or entry.FIXES where the print differs from the proposal.
"""
import argparse
import csv
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "logs" / "review"
sys.stdout.reconfigure(encoding="utf-8")


def items_of(lo: int, hi: int) -> list[dict]:
    rng = f"v2-{lo}-{hi}"
    boxes = {}
    for r in csv.DictReader(open(ROOT / "logs" / f"check_{rng}.csv", encoding="utf-8-sig")):
        boxes.setdefault((r["page"], r["line"]), (r["box"], r["box_match"]))
    out = []
    for r in csv.DictReader(open(ROOT / "logs" / f"vote_{rng}.csv", encoding="utf-8-sig")):
        o = r["outcome"]
        if o == "keep" or o.startswith("rejected"):
            continue
        r["kind"] = "change" if o == "change" else "review"
        r["box"], r["box_match"] = boxes.get((r["page"], r["line"]), ("", "0"))
        out.append(r)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("first", type=int)
    p.add_argument("last", type=int)
    p.add_argument("--group", action="append", default=[], help="NAME:FIRST-LAST (default: one group)")
    a = p.parse_args()
    groups = [(g.split(":")[0], *map(int, g.split(":")[1].split("-"))) for g in a.group] or \
             [(f"{a.first}-{a.last}", a.first, a.last)]
    items = items_of(a.first, a.last)
    for name, lo, hi in groups:
        d = OUT / name
        d.mkdir(parents=True, exist_ok=True)
        rows = []
        for it in items:
            if not lo <= int(it["page"][3:]) <= hi:
                continue
            n = len(rows) + 1
            img_name = ""
            if it["box"]:
                img = Image.open(ROOT / "data" / "raw" / f"{it['page']}.jpg").convert("L")
                x0, y0, x1, y1 = map(int, it["box"].split())
                h = y1 - y0
                pad = 2 * h if float(it["box_match"] or 0) < 60 else int(0.7 * h)  # weak match: wider strip
                c = img.crop((max(x0 - 40, 0), max(y0 - pad, 0), min(x1 + 40, img.width), min(y1 + pad, img.height)))
                c = c.resize((c.width * 2, c.height * 2), Image.LANCZOS)
                img_name = f"{n:03d}.jpg"
                c.save(d / img_name, quality=90)
            rows.append({"id": n, "page": it["page"], "kind": it["kind"], "outcome": it["outcome"],
                         "main": it["main"], "flash": it["flash"], "mdz": it["mdz"], "judge": it["judge"],
                         "new": it["new"], "line": it["line"].replace("\n", " "), "image": img_name})
        if not rows:
            print(name, "no items")
            continue
        with open(d / "items.tsv", "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter="\t")
            w.writeheader()
            w.writerows(rows)
        print(name, len(rows), "items;", sum(r["kind"] == "review" for r in rows), "review")


if __name__ == "__main__":
    main()
