import sys, json, difflib, collections
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import eval as ev
ev.LOOSE = True
ref = "or-claude-opus-5.5@low+vote"
for eng in sys.argv[1:]:
    n = 0; words = 0; by = collections.Counter(); ex = []
    for p in range(408, 430):
        k = f"v2-{p:04d}"
        f = ROOT / "data/ocr" / eng / f"{k}.json"
        if not f.exists(): continue
        a = ev.norm(ev.page_text(json.load(open(ROOT / "data/ocr" / ref / f"{k}.json", encoding="utf-8")))).split()
        b = ev.norm(ev.page_text(json.load(open(f, encoding="utf-8")))).split()
        words += len(a)
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if op == "equal": continue
            n += max(i2 - i1, j2 - j1)
            s = ev.script(next((c for c in " ".join(a[i1:i2] or b[j1:j2]) if c.isalpha()), "a"))
            by[s] += 1
            if len(ex) < 400: ex.append((k, " ".join(a[i1:i2]), " ".join(b[j1:j2])))
    print(f"{eng:34s} words {words} diff-words {n} ({n / words:.1%}) by script {dict(by)}")
