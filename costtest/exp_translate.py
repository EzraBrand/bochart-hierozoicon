"""Translation test: the same chunks as the pilot, other models/efforts, through the Batch API.

  uv run costtest/exp_translate.py anthropic/claude-opus-5.5 low
Writes costtest/translate_exp/{model}@{effort}/{kind}-{i}.json.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
import entry  # noqa: E402
import orbatch  # noqa: E402
import translate as T  # noqa: E402

PICK = {("text", 1), ("text", 5), ("text", 10), ("notes", 1)}

model, effort = sys.argv[1], sys.argv[2]
la = json.loads((ROOT / "data/entries/shafan/la.json").read_text(encoding="utf-8"))
bodies, src = {}, {}
for kind, blocks in (("text", la["main"]), ("notes", la["notes"])):
    for i, ch in enumerate(entry.chunks(blocks), 1):
        if (kind, i) in PICK:
            bodies[f"{kind}-{i}"] = T.request_body(ch, effort, notes=kind == "notes")
            src[f"{kind}-{i}"] = ch
name = f"{model.split('/')[-1]}@{effort}"
t = time.monotonic()
res = orbatch.run_batch(model, bodies, log_name=f"translate_exp_{name}")
out = ROOT / "costtest/translate_exp" / name
out.mkdir(parents=True, exist_ok=True)
total = 0
for cid, d in res.items():
    try:
        r = T.parse(d, len(src[cid]), model, effort, time.monotonic() - t)
    except Exception as e:
        print(cid, "FAILED", e)
        continue
    total += r["meta"]["cost_usd"]
    (out / f"{cid}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(cid, r["meta"])
print(f"{name}: ${total:.4f}")
