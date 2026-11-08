"""Image judge, one request per page (all flagged lines of the page), through the Batch API.

  uv run judge_page.py 408 429 --model anthropic/claude-opus-5.5
  uv run judge_page.py 408 429 --model google/gemini-4-argon --pages v2-0410 v2-0422

The same task and rules as judge.py, but (1) the fixed instructions are sent once per page, not
once per line, (2) each line is its own image (an IIIF crop URL of the MDZ scan, the box from the
MDZ hOCR as in judge.py), and (3) the requests go through the OpenRouter Batch API (half price).
Writes data/fix/{range}.judge.{tag}.jsonl in the format of judge.py, so vote.py --judge can read it.
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import orbatch

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
DATA = ROOT / "data"

PROMPT = """\
The images show printed lines of one page of Samuel Bochart, "Hierozoicon", in the Leipzig \
edition of 1793-96: Latin (roman and italic type, with the long s "ſ"), with Greek in an old type \
with ligatures, unpointed square Hebrew, Arabic in naskh type, Syriac and Ethiopic. Each image is \
one printed line (with a part of the lines above and below); the images are numbered L1, L2 ... \
in the order given. For each line you get the OCR text of the line and the item(s) where OCR \
engines disagree.

For each item, find that place in its line image and write exactly what is PRINTED there, \
character by character, as many words as the readings cover. Do not correct the print to the \
word you expect: if the print has an unusual spelling, an old form or a misprint, write what is \
printed. It may be that no reading is right.
- Latin: write the long s as "s"; "f" only where the letter has the full cross bar of f. Keep \
the spelling (causa vs. caussa), the punctuation (comma vs. full stop) and hyphens at the line end.
- Greek: the accents and breathings as printed (acute ´, grave `, circumflex ῀; smooth vs. rough \
breathing); write the ligature ȣ as ου.
- Hebrew: the letters as printed; ״ for the double stroke of an abbreviation; easy to confuse: \
ם/ס, ו/ז/י, ח/ת/ה, ד/ר, ב/כ, ג/נ. Do not add a letter of the full word to an abbreviation.
- Arabic: the letters and their dots as printed: count the dots (ب ت ث ن ي; ف ق; ع غ; د ذ; ر ز; \
ه ة; ي ى). Do not add a dot, a hamza or a letter that is not printed. Leave out vowel signs.
- Syriac, Ethiopic: the letters as printed, in Unicode.

Answer with JSON only: {"items": [{"line": "L1", "id": 1, "printed": "...", "confident": true or false}, ...]}, \
one entry for every item of every line.

Lines and items:
"""

SCHEMA = {"type": "object", "properties": {"items": {"type": "array", "items": {
    "type": "object", "properties": {"line": {"type": "string"}, "id": {"type": "integer"},
                                     "printed": {"type": "string"}, "confident": {"type": "boolean"}},
    "required": ["line", "id", "printed", "confident"], "additionalProperties": False}}},
    "required": ["items"], "additionalProperties": False}


def crop_url(pg: dict, box: str, weak: bool) -> str:
    x0, y0, x1, y1 = map(int, box.split())
    h = y1 - y0
    pad = 3 * h if weak else int(0.6 * h)
    top, bottom = max(y0 - pad, 0), min(y1 + pad, pg["height"])
    return f"{pg['image_service']}/60,{top},{pg['width'] - 100},{bottom - top}/full/0/default.jpg"


def to_data_uri(url: str) -> str:
    """The IIIF crop URL -> the same crop of the local scan, as a data URI."""
    import base64
    import io
    import re
    from PIL import Image
    m = re.search(r"_(\d{5})/(\d+),(\d+),(\d+),(\d+)/", url)
    canvas, x, y, w, h = map(int, m.groups())
    pg = next(pg for pg in json.loads((DATA / "raw" / "manifest.json").read_text(encoding="utf-8"))["pages"]
              if pg["canvas"] == canvas)
    img = Image.open(DATA / pg["file"]).convert("L").crop((x, y, x + w, y + h))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.standard_b64encode(buf.getvalue()).decode()


def run_sync(model: str, bodies: dict) -> dict:
    import requests
    out = {}
    for i, (cid, body) in enumerate(bodies.items(), 1):
        for c in body["messages"][0]["content"]:
            if c["type"] == "image_url":
                c["image_url"]["url"] = to_data_uri(c["image_url"]["url"])
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                          headers={"Authorization": "Bearer " + orbatch.KEY_FILE.read_text(encoding="utf-8").strip()},
                          json={"model": model, **body}, timeout=900)
        out[cid] = r.json()
        print(f"[{i}/{len(bodies)}] {cid}: ${(out[cid].get('usage') or {}).get('cost', 0):.4f}", flush=True)
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("first", type=int)
    p.add_argument("last", type=int)
    p.add_argument("--vol", type=int, default=2)
    p.add_argument("--pages", nargs="*")
    p.add_argument("--model", required=True)
    p.add_argument("--effort", default="low")
    p.add_argument("--tag", default="", help="output tag (default: model name)")
    p.add_argument("--run", default="", help="suffix of the check CSV, e.g. .argon (another main OCR)")
    p.add_argument("--sync", action="store_true", help="normal API (full price), base64 crops: for providers that cannot fetch MDZ URLs in time")
    p.add_argument("--skip-mdz-only", action="store_true", help="do not judge flags where only MDZ differs")
    a = p.parse_args()
    rng = f"v{a.vol}-{a.first}-{a.last}"
    tag = a.tag or a.model.split("/")[-1]
    manifest = {pg["key"]: pg for pg in json.loads((DATA / "raw" / "manifest.json").read_text(encoding="utf-8"))["pages"]}
    flags = [r for r in csv.DictReader((ROOT / "logs" / f"check_{rng}{a.run}.csv").open(encoding="utf-8-sig"))
             if r["kind"] == "replace" and (not a.pages or r["page"] in a.pages)]
    if a.skip_mdz_only:
        flags = [r for r in flags if r["flash"] and r["flash"] != r["main"]]
    pages = {}
    for r in flags:
        pages.setdefault(r["page"], {}).setdefault(r["line_no"], []).append(r)
    bodies, index = {}, {}
    for page, lines in sorted(pages.items()):
        content, text = [], [PROMPT]
        index[page] = []
        for li, (line_no, rows) in enumerate(sorted(lines.items(), key=lambda kv: int(kv[0])), 1):
            weak = not rows[0]["box_match"] or float(rows[0]["box_match"]) < 70
            content.append({"type": "text", "text": f"Image L{li}:"})
            content.append({"type": "image_url", "image_url": {"url": crop_url(manifest[page], rows[0]["box"], weak)}})
            text.append(f"\nL{li}. OCR line: {rows[0]['line']}")
            for j, r in enumerate(rows, 1):
                readings = sorted({r["main"], r["flash"], r["mdz"]} - {""})
                text.append(f"  item {j}. readings: " + " | ".join(f'"{x}"' for x in readings))
            index[page].append((f"L{li}", line_no, rows, weak))
        content.append({"type": "text", "text": "\n".join(text)})
        bodies[page] = {"max_tokens": 16000, "messages": [{"role": "user", "content": content}],
                        "response_format": {"type": "json_schema",
                                            "json_schema": {"name": "items", "strict": True, "schema": SCHEMA}},
                        "reasoning": {"effort": a.effort}, "usage": {"include": True}}
    n_lines = sum(len(v) for v in index.values())
    print(f"{len(flags)} flags on {n_lines} lines, {len(bodies)} page requests", flush=True)
    if a.sync:
        res = run_sync(a.model, bodies)
    else:
        res = orbatch.run_batch(a.model, bodies, log_name=f"judge_{rng}_{tag}")
    out = DATA / "fix" / f"{rng}.judge.{tag}.jsonl"
    total, bad = 0.0, 0
    with out.open("w", encoding="utf-8") as fh:
        for page in sorted(index):
            d = res.get(page, {"error": "no result"})
            try:
                txt = d["choices"][0]["message"]["content"].strip()
                if txt.startswith("```"):
                    txt = txt.split("\n", 1)[1].rsplit("```", 1)[0]
                ans = {(x["line"], x["id"]): x for x in json.loads(txt)["items"]}
                cost = (d.get("usage") or {}).get("cost", 0)
            except Exception as e:
                print(f"{page}: FAILED {type(e).__name__}: {str(d)[:300]}", flush=True)
                bad += 1
                continue
            total += cost
            for lid, line_no, rows, weak in index[page]:
                rec = {"page": page, "line_no": line_no, "line": rows[0]["line"], "weak_box": weak,
                       "cost": round(cost / len(index[page]), 5), "model": f"{a.model}@{a.effort} page-batch",
                       "items": [{"main": r["main"], "flash": r["flash"], "mdz": r["mdz"], "script": r["script"],
                                  "printed": ans.get((lid, j), {}).get("printed"),
                                  "confident": ans.get((lid, j), {}).get("confident")}
                                 for j, r in enumerate(rows, 1)]}
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"{len(index) - bad}/{len(index)} pages judged, cost ${total:.4f}; wrote {out}")


if __name__ == "__main__":
    main()
