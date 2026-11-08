import sys, json, difflib
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
import eval as ev
ev.LOOSE = True
for eng in sys.argv[1:]:
    print("=====", eng)
    for g in sorted((ROOT / "data/gold").glob("v2-*.txt")):
        f = ROOT / "data/ocr" / eng / f"{g.stem}.json"
        if not f.exists(): continue
        a = ev.norm(g.read_text(encoding="utf-8")).split()
        b = ev.norm(ev.page_text(json.loads(f.read_text(encoding="utf-8")))).split()
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if op != "equal":
                print(f"  {g.stem} {op}: gold [{' '.join(a[i1:i2])}]  ocr [{' '.join(b[j1:j2])}]")
