"""Image judge for the flags of check.py: what is printed, read from a crop of the scan line.

  uv run judge.py 408 429                          # all "replace" flags of logs/check_v2-408-429.csv
  uv run judge.py 408 429 --pages v2-0410 v2-0422  # only these pages (a test on gold pages)
  uv run judge.py 408 429 --start 1 --stride 4     # parallel workers (each skips lines already judged)

Ported from lewysohn-zoologie's hebjudge.py (image mode), for all scripts. The flags of one printed
line go to the model in one call, with a crop of that line (and half a line above and below) at
full resolution; the box of the line comes from the MDZ hOCR (check.py). The readings are given
without engine names and in a fixed order (sorted), so the judge cannot favour one engine.
No text judge: on these pages the main OCR's errors are corrections toward the expected word, and a
judge that decides from the sense makes the same errors.
Answers are appended to data/fix/{range}.judge.jsonl (one line per printed line); a stopped run
resumes.
"""

import argparse
import base64
import csv
import io
import json
import os
import sys
import time
from pathlib import Path

import requests
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
DATA = ROOT / "data"
KEY_FILE = Path(os.environ.get("OPENROUTER_KEY_FILE", Path.home() / "Desktop/Misc/key.txt"))

PROMPT = """\
The image shows one printed line (with a part of the lines above and below) of Samuel Bochart, \
"Hierozoicon", in the Leipzig edition of 1793-96: Latin (roman and italic type, with the long s \
"ſ"), with Greek in an old type with ligatures, unpointed square Hebrew, Arabic in naskh type, \
Syriac and Ethiopic. OCR read the line as:

{line}

OCR engines disagree about the item(s) below. For each item, find that place in the line and \
write exactly what is PRINTED there, character by character, as many words as the readings \
cover. Do not correct the print to the word you expect: if the print has an unusual spelling, an \
old form or a misprint, write what is printed. It may be that no reading is right.
- Latin: write the long s as "s"; "f" only where the letter has the full cross bar of f. Keep \
the spelling (causa vs. caussa), the punctuation (comma vs. full stop) and hyphens at the line end.
- Greek: the accents and breathings as printed (acute ´, grave `, circumflex ῀; smooth vs. rough \
breathing); write the ligature ȣ as ου.
- Hebrew: the letters as printed; ״ for the double stroke of an abbreviation; easy to confuse: \
ם/ס, ו/ז/י, ח/ת/ה, ד/ר, ב/כ, ג/נ. Do not add a letter of the full word to an abbreviation.
- Arabic: the letters and their dots as printed: count the dots (ب ت ث ن ي; ف ق; ع غ; د ذ; ر ز; \
ه ة; ي ى). Do not add a dot, a hamza or a letter that is not printed. Leave out vowel signs.
- Syriac, Ethiopic: the letters as printed, in Unicode.

Items:
{items}

Answer with JSON only: {{"items": [{{"id": 1, "printed": "...", "confident": true or false}}, ...]}}"""

SCHEMA = {"type": "object", "properties": {"items": {"type": "array", "items": {
    "type": "object", "properties": {"id": {"type": "integer"}, "printed": {"type": "string"},
                                     "confident": {"type": "boolean"}},
    "required": ["id", "printed", "confident"], "additionalProperties": False}}},
    "required": ["items"], "additionalProperties": False}


def crop(page: str, box: str, weak: bool) -> Image.Image:
    img = Image.open(DATA / "raw" / f"{page}.jpg").convert("L")
    x0, y0, x1, y1 = map(int, box.split())
    h = y1 - y0
    pad = 3 * h if weak else int(0.6 * h)  # a weak line match: a wider strip, so the line is in it
    return img.crop((60, max(y0 - pad, 0), img.width - 40, min(y1 + pad, img.height)))


def ask(model: str, effort: str, img: Image.Image, prompt: str) -> tuple[dict, float]:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    content = [{"type": "image_url", "image_url": {
        "url": "data:image/jpeg;base64," + base64.standard_b64encode(buf.getvalue()).decode()}},
        {"type": "text", "text": prompt}]
    r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                      headers={"Authorization": "Bearer " + KEY_FILE.read_text(encoding="utf-8").strip()},
                      json={"model": model, "max_tokens": 6000, "messages": [{"role": "user", "content": content}],
                            "response_format": {"type": "json_schema",
                                                "json_schema": {"name": "items", "strict": True, "schema": SCHEMA}},
                            "reasoning": {"effort": effort}, "usage": {"include": True}}, timeout=300)
    d = r.json()
    if not r.ok or "error" in d:
        raise RuntimeError(f"HTTP {r.status_code}: {d.get('error', d)}")
    text = d["choices"][0]["message"]["content"].strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(text), d.get("usage", {}).get("cost", 0)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("first", type=int)
    p.add_argument("last", type=int)
    p.add_argument("--vol", type=int, default=2)
    p.add_argument("--pages", nargs="*")
    p.add_argument("--model", default="anthropic/claude-opus-5.5")
    p.add_argument("--effort", default="low")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--stride", type=int, default=1)
    a = p.parse_args()
    rng = f"v{a.vol}-{a.first}-{a.last}"
    flags = [r for r in csv.DictReader((ROOT / "logs" / f"check_{rng}.csv").open(encoding="utf-8-sig"))
             if r["kind"] == "replace" and (not a.pages or r["page"] in a.pages)]
    groups = {}
    for r in flags:
        groups.setdefault((r["page"], r["line_no"]), []).append(r)
    todo = sorted(groups.items())[a.start::a.stride]
    out = DATA / "fix" / f"{rng}.judge.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    total, n = 0.0, 0
    for i, ((page, line_no), rows) in enumerate(todo, 1):
        done = set()
        if out.exists():  # re-read each time: parallel workers share the file
            done = {(d["page"], d["line_no"]) for d in map(json.loads, out.read_text(encoding="utf-8").splitlines())}
        if (page, line_no) in done:
            continue
        items = []
        for j, r in enumerate(rows, 1):
            readings = sorted({r["main"], r["flash"], r["mdz"]} - {""})
            items.append(f'{j}. readings: ' + " | ".join(f'"{x}"' for x in readings))
        weak = not rows[0]["box_match"] or float(rows[0]["box_match"]) < 70
        try:
            ans, cost = ask(a.model, a.effort, crop(page, rows[0]["box"], weak),
                            PROMPT.format(line=rows[0]["line"], items="\n".join(items)))
        except Exception as e:
            print(f"[{i}/{len(todo)}] {page} line {line_no}: FAILED {type(e).__name__}: {e}", flush=True)
            continue
        by_id = {x["id"]: x for x in ans["items"]}
        rec = {"page": page, "line_no": line_no, "line": rows[0]["line"], "weak_box": weak, "cost": round(cost, 4),
               "model": f"{a.model}@{a.effort}",
               "items": [{"main": r["main"], "flash": r["flash"], "mdz": r["mdz"], "script": r["script"],
                          "printed": by_id.get(j, {}).get("printed"), "confident": by_id.get(j, {}).get("confident")}
                         for j, r in enumerate(rows, 1)]}
        with out.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        total += cost
        n += 1
        print(f"[{i}/{len(todo)}] {page} line {line_no}: {len(rows)} flags, ${cost:.4f}", flush=True)
        time.sleep(0.3)
    print(f"{n} lines judged this run, cost ${total:.4f}; wrote {out}")


if __name__ == "__main__":
    main()
