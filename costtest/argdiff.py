import sys, json, difflib
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import eval as ev
ev.LOOSE = True
eng = sys.argv[1]
for p in range(408, 430):
    k = f"v2-{p:04d}"
    a = ev.norm(ev.page_text(json.load(open(ROOT / f"data/ocr/or-claude-opus-5.5@low+vote/{k}.json", encoding="utf-8")))).split()
    f = ROOT / f"data/ocr/{eng}/{k}.json"
    if not f.exists(): continue
    b = ev.norm(ev.page_text(json.load(open(f, encoding="utf-8")))).split()
    out = [f"[{' '.join(a[i1:i2])}→{' '.join(b[j1:j2])}]" for op, i1, i2, j1, j2 in
           difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if op != "equal"]
    print(p, " ".join(out))
