"""Score a judge: vote with it, then compare (a) gold-page CER of the voted text, (b) its changes
with the reviewed baseline changes (vote.py with judge.py's Opus answers + REJECT list)."""
import sys, json, csv, subprocess
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
def changes(sfx):
    rows = list(csv.DictReader(open(ROOT / f"logs/vote_v2-408-429{sfx}.csv", encoding="utf-8-sig")))
    ch = {(r["page"], r["main"], r["new"]) for r in rows if r["outcome"] == "change"}
    rej = {(r["page"], r["main"]) for r in rows if r["outcome"].startswith("rejected")}
    rev = sum(r["outcome"].startswith("review") or r["outcome"] == "no answer" for r in rows)
    return ch, rej, rev, len(rows)
base, _, _, _ = changes("")
for tag in sys.argv[1:]:
    judge, _, skip = tag.partition("+")
    args = ["uv", "run", "vote.py", "408", "429"] + (["--judge", judge] if judge != "base" else []) + (["--skip-mdz-only"] if skip else [])
    subprocess.run(args, cwd=ROOT, capture_output=True)
    sfx = (f".{judge}" if judge != "base" else "") + (".nomdz" if skip else "")
    ch, rej, rev, n = changes(sfx)
    eng = "or-claude-opus-5.5@low+vote" + sfx.replace(".", "-")
    ev = subprocess.run(["uv", "run", "eval.py", "--loose"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
    line = next((l for l in ev.splitlines() if l.split() and l.split()[0] == eng), "")
    print(f"{tag:28s} flags {n:3d} changes {len(ch):2d} same-as-base {len(ch & base):2d} missed {len(base - ch):2d} "
          f"extra {len(ch - base):2d} hit-REJECT {len(rej):2d} review {rev:2d} | gold {' '.join(line.split()[1:4])}")
