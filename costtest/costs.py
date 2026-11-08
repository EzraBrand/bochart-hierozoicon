"""Cost per OCR page from token counts and OpenRouter prices (batch runs report no per-request cost)."""
import glob
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
PRICES = {m["id"]: (float(m["pricing"]["prompt"]), float(m["pricing"]["completion"]))
          for m in json.load(open(ROOT / "costtest/models.json", encoding="utf-8"))}


def price(model: str, batch: bool):
    base = model.split("-2026")[0] if model not in PRICES else model  # dated snapshot ids
    for k in ([base + ":batch"] if batch else []) + [base]:
        if k in PRICES:
            return PRICES[k]
    return None


def cost(model, batch, tin, tout):
    p = price(model, batch)
    return None if p is None else tin * p[0] + tout * p[1]


if __name__ == "__main__":
    for d in sorted((ROOT / "data/ocr").iterdir()):
        if d.name.startswith("_") or d.name == "mdz" or "vote" in d.name:
            continue
        rows = [json.load(open(f, encoding="utf-8"))["meta"] for f in sorted(glob.glob(str(d / "*.json")))]
        rows = [m for m in rows if m.get("input_tokens")]
        if not rows:
            continue
        model = "/".join(rows[0]["model"].split("/")[:2])
        batch = "batch" in rows[0].get("engine", "")
        n = len(rows)
        tin = sum(m["input_tokens"] for m in rows) / n
        tout = sum(m["output_tokens"] for m in rows) / n
        c = cost(model, batch, tin, tout)
        print(f"{d.name:34s} pages {n:2d}  in {tin:7.0f}  out {tout:6.0f}  $/page {c if c is None else round(c, 4)}")
