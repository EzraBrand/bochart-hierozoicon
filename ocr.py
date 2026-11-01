"""OCR pages of Bochart, Hierozoicon, ed. Rosenmüller (Leipzig 1793-96), with a vision model on OpenRouter.

  uv run ocr.py v2-0409 v2-0422 v2-0428 --model anthropic/claude-opus-5.5 --effort low
  uv run ocr.py --model google/gemini-3.8-flash --effort low       # all pages in data/raw/manifest.json
  uv run ocr.py v2-0428 --model anthropic/claude-sonnet-5.5 --force  # redo a page

Writes data/ocr/or-{model}@{effort}[+tag]/{page}.json and .md. Pages with output are skipped, so
parallel workers can split the pages (--start / --stride). Ported from lewysohn-zoologie; the
prompt is for Latin with Greek, Hebrew, Arabic and Syriac, two layers of notes and the margin
column numbers.
"""

import argparse
import base64
import io
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8")

DATA = Path(__file__).parent / "data"
MAX_EDGE, MAX_PIXELS = 2576, 3_750_000  # the API downscales images beyond either limit

BLOCK_TYPES = ["heading", "body", "footnote", "furniture"]
LANGS = ["lat", "grc", "heb", "arc", "syc", "ara", "fas", "translit", "deu", "fra", "eng", "ita", "other"]

PROMPT = """\
These images are one printed page of Samuel Bochart, "Hierozoicon" (first ed. London 1663), in \
the edition of E. F. C. Rosenmüller (Leipzig 1793-96): a Latin study of the animals of the Bible. \
The Latin quotes Greek, Hebrew and Aramaic (unpointed square script), Syriac (Estrangela type) \
and much Arabic (naskh type, often whole lines), with Bochart's own transliterations in italics. \
The page is split into {n} image(s), top to bottom, cut at blank space between lines. \
Transcribe the whole page as one page.

Transcription rules:
- Transcribe exactly what is printed. Never translate, normalize, modernize, correct or expand \
abbreviations. Keep the spelling, capitals and punctuation as printed (Palaestina, caussa, \
quum, ae and æ as printed, the accents of the Latin: "à", "quàm").
- Write the long s (ſ) as "s". Write the type ligatures (ct, st, ff, fi, fl) as plain letters.
- Greek: in Unicode, with the accents and breathings as printed. Write the old type ligatures \
as plain letters (ȣ -> ου, the καί ligature -> καὶ, στ -> στ). Do not change the spelling.
- Hebrew and Aramaic: unpointed, as printed, in logical order.
- Arabic and Persian: the letters and dots as printed, even where the print looks wrong. Vowel \
signs (fatḥa, kasra, ḍamma, sukūn, shadda, tanwīn) only where printed. Never add a hamza or a \
dot that is not printed. Do not write the stretching stroke (tatweel, ـ). Logical order.
- Syriac: in Syriac Unicode letters (ܐ ܒ ܓ ...), as printed, in logical order.
- Mixed lines: the page is left-to-right. Give the parts of a line in their order from left to \
right; a Hebrew, Arabic or Syriac stretch is one run in its own reading order, put where it \
stands. Example: a line printed as "Et paullo infra, [Arabic stretch]" gives the runs \
"Et paullo infra, " and the Arabic stretch, in that order.
- Keep each printed line as one line: separate lines with "\\n". Keep a hyphen at a line end as \
printed. Do not join lines.
- Margin numbers: the old column numbers of the 1663 edition stand in the outer margin \
("p. 1001", "p.1002"). Write each one as "⟦p. 1001⟧" (normalized: "p.", one space, the number) \
at the end of the printed line beside which it stands.
- Note marks in the text: Rosenmüller's raised numbers in brackets as "^{{(13)}}"; Bochart's \
raised letters as "^{{c)}}". Other superscripts: "^{{a}}"; subscripts "_{{14}}".
- Small capitals: write them as capitals ("SCHULTENSIUS", "BOCHARTI"). Letter-spaced words: \
write them with normal spacing.
- Italics: wrap italic Latin text in <i>...</i>. Open and close the tag inside one run; if an \
italic stretch continues into the next run, close it and open it again there. Punctuation after \
an italic word stays outside the tag unless it is clearly italic. Greek, Hebrew, Arabic and \
Syriac are never marked italic.
- Text you cannot read: write [?] for each unreadable stretch. Do not guess.

Blocks, in reading order:
- "furniture": running head with page number, signature ("Fff", "Hhh 3", "BOCHARTI Hieroz. \
Tom. II.") and the catchword at the foot of the page. One block each.
- "heading": a chapter number ("CAP. XXXIII.") and the chapter argument under it (one block \
each).
- "body": a paragraph of main text. A new paragraph starts at an indented line. A quotation set \
on its own centred line(s) is its own body block.
- "footnote": one note. Notes stand at the foot of the page. Bochart's notes have a letter \
("c) Pag. 1003."); Rosenmüller's notes have a number in brackets ("(13)") and are set in two \
columns: read the whole left column, then the whole right column. Put the mark ("c)", "(13)") \
in "marker" and not in the runs. A note that continues from the page before has no mark: give \
it marker "" and put it first. A note that runs from the left into the right column is one \
block.
For other block types, "marker" is "".

Runs: split each block into runs of one language each, in reading order. Codes: lat Latin, \
grc Greek, heb Hebrew, arc Aramaic (Chaldaic, Targum), syc Syriac, ara Arabic, fas Persian, \
translit Bochart's romanized form of a Semitic word (e.g. "sephanim", "aljarbuo"), deu German, \
fra French, eng English, ita Italian, other. Numbers, references and punctuation go with the run \
around them. Concatenating the runs of a block must give the block text exactly (spaces and \
"\\n" included). If Hebrew vs. Aramaic is unclear, use heb.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "blocks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": BLOCK_TYPES},
                    "marker": {"type": "string"},
                    "runs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "lang": {"type": "string", "enum": LANGS},
                                "text": {"type": "string"},
                            },
                            "required": ["lang", "text"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["type", "marker", "runs"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["blocks"],
    "additionalProperties": False,
}


# ---------- image preparation ----------

def _span(profile: np.ndarray, thr: float, gap: int) -> tuple[int, int]:
    """Largest run of indices where profile > thr, bridging gaps up to `gap`."""
    idx = np.flatnonzero(profile > thr)
    breaks = np.flatnonzero(np.diff(idx) > gap)
    starts = np.r_[idx[0], idx[breaks + 1]]
    ends = np.r_[idx[breaks], idx[-1]] + 1
    k = int(np.argmax(ends - starts))
    return int(starts[k]), int(ends[k])


def text_box(gray: Image.Image, gap: float = 0.04) -> tuple[int, int, int, int]:
    """Bounding box of the text block, without the scan borders around the page."""
    small = np.asarray(gray.reduce(4)) < 140
    h, w = small.shape
    small[small.mean(axis=1) > 0.25, :] = False
    small[:, small.mean(axis=0) > 0.25] = False
    x0, x1 = _span(small.mean(axis=0), 0.003, int(w * gap))
    rows = small[:, x0:x1].mean(axis=1)
    rows = np.where(rows > 0.4, 0, rows)
    ys = np.flatnonzero(rows > 0.002)
    if not len(ys):
        raise ValueError("no text found: blank page?")
    pad = 6
    # wide side margins: the margin column numbers stand apart from the text block
    side = max(pad, int(w * 0.06))
    return (max(x0 - side, 0) * 4, max(ys[0] - pad, 0) * 4,
            min(x1 + side, w) * 4, min(ys[-1] + 1 + pad, h) * 4)


def page_images(path: Path) -> list[Image.Image]:
    """Crop to the text block; cut in two at a blank row if one image would be downscaled.

    Full resolution matters for the Arabic dots and vowel signs, so a page is split whenever it
    is over the API's pixel limit (Rosenmüller's pages are about 1900x2500 px after the crop).
    """
    gray = Image.open(path).convert("L")
    page = gray.crop(text_box(gray))
    w, h = page.size
    if w * h <= MAX_PIXELS and max(w, h) <= MAX_EDGE:
        return [page]
    ink = (np.asarray(page) < 140).mean(axis=1)
    lo, hi = int(h * 0.4), int(h * 0.6)
    cut = lo + int(np.argmin(np.convolve(ink[lo:hi], np.ones(15) / 15, "same")))
    return [page.crop((0, 0, w, cut)), page.crop((0, cut, w, h))]


def jpeg_b64(img: Image.Image) -> str:
    s = min(1, MAX_EDGE / max(img.size), (MAX_PIXELS / (img.width * img.height)) ** 0.5)
    if s < 1:  # resize here, so we control the filter
        img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return base64.standard_b64encode(buf.getvalue()).decode()


# ---------- engine ----------

def parse_blocks(text: str) -> list[dict]:
    """Model JSON -> blocks; block lang = the language with the most characters."""
    text = text.strip()
    if text.startswith("```"):  # models without schema enforcement may fence the JSON
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    blocks = []
    for b in json.loads(text)["blocks"]:
        chars = {}
        for r in b["runs"]:
            chars[r["lang"]] = chars.get(r["lang"], 0) + len(r["text"].strip())
        blocks.append({"type": b["type"], "lang": max(chars, key=chars.get) if chars else "other",
                       "text": "".join(r["text"] for r in b["runs"]),
                       "marker": b.get("marker", ""), "runs": b["runs"]})
    return blocks


def run_openrouter(path: Path) -> dict:
    import requests

    key = Path(os.environ.get("OPENROUTER_KEY_FILE", Path.home() / "Desktop/Misc/key.txt"))
    imgs = page_images(path)
    content = [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{jpeg_b64(im)}"}}
               for im in imgs]
    content.append({"type": "text", "text": PROMPT.format(n=len(imgs)) + "\nAnswer with the JSON object only."})
    t = time.monotonic()
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": "Bearer " + key.read_text(encoding="utf-8").strip()},
        json={"model": ARGS.model, "max_tokens": 32000,
              "messages": [{"role": "user", "content": content}],
              "response_format": {"type": "json_schema",
                                  "json_schema": {"name": "page", "strict": True, "schema": SCHEMA}},
              "reasoning": {"effort": ARGS.effort},
              "usage": {"include": True}},
        timeout=900)
    d = r.json()
    raw = DATA / "ocr" / "_raw" / f"{ARGS.model.split('/')[-1]}_{path.stem}.json"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    if not r.ok or "error" in d:
        raise RuntimeError(f"HTTP {r.status_code}: {d.get('error', d)}")
    ch = d["choices"][0]
    u = d.get("usage", {})
    if ch.get("finish_reason") not in ("stop", "end_turn"):
        raise RuntimeError(f"finish_reason={ch.get('finish_reason')}, cost ${u.get('cost', 0):.4f}")
    return {"blocks": parse_blocks(ch["message"]["content"]), "meta": {
        "engine": "openrouter", "model": d.get("model", ARGS.model), "provider": d.get("provider"),
        "effort": ARGS.effort, "reasoning_tokens":
            (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
        "images": [list(im.size) for im in imgs],
        "input_tokens": u.get("prompt_tokens"), "output_tokens": u.get("completion_tokens"),
        "cost_usd": round(u.get("cost", 0), 4), "seconds": round(time.monotonic() - t, 1)}}


def to_md(page: dict, result: dict) -> str:
    out = [f"<!-- vol. {page['volume']} p. {page['label']}, {result['meta'].get('model')} -->"]
    lrm = "‎"  # left-to-right mark: keeps a line that starts with Hebrew or Arabic LTR on GitHub
    for b in result["blocks"]:
        text = lrm + b["text"].replace("\n", f"  \n{lrm}")  # keep printed line breaks
        if b["type"] == "heading":
            out.append(f"### {text}")
        elif b["type"] == "footnote":
            out.append(f"> {lrm}{b.get('marker', '')} {text}".replace("  \n", "  \n> "))
        elif b["type"] == "furniture":
            out.append(f"{lrm}*{text}*")
        else:
            out.append(text)
    return "\n\n".join(out) + "\n"


def main():
    global ARGS
    p = argparse.ArgumentParser()
    p.add_argument("pages", nargs="*", help="page keys, e.g. v2-0409 (default: all in the manifest)")
    p.add_argument("--model", required=True, help="OpenRouter model id, e.g. anthropic/claude-opus-5.5")
    p.add_argument("--effort", default="low", choices=["low", "medium", "high", "xhigh", "max"])
    p.add_argument("--tag", default="", help="suffix for the output folder, e.g. a prompt version")
    p.add_argument("--force", action="store_true")
    p.add_argument("--start", type=int, default=0, help="parallel workers: first page index")
    p.add_argument("--stride", type=int, default=1, help="parallel workers: take every n-th page")
    ARGS = p.parse_args()
    name = f"or-{ARGS.model.split('/')[-1]}@{ARGS.effort}" + (f"+{ARGS.tag}" if ARGS.tag else "")

    pages = json.loads((DATA / "raw" / "manifest.json").read_text(encoding="utf-8"))["pages"]
    if ARGS.pages:
        pages = [pg for pg in pages if pg["key"] in ARGS.pages]
    pages = pages[ARGS.start::ARGS.stride]
    total, done = 0.0, 0
    for i, pg in enumerate(pages, 1):
        out = DATA / "ocr" / name / pg["key"]
        if out.with_suffix(".json").exists() and not ARGS.force:
            print(f"[{i}/{len(pages)}] {pg['key']}: done already", flush=True)
            continue
        try:
            res = run_openrouter(DATA / pg["file"])
        except Exception as e:  # report and go on with the next page
            print(f"[{i}/{len(pages)}] {pg['key']}: FAILED {type(e).__name__}: {e}", flush=True)
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.with_suffix(".json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        out.with_suffix(".md").write_text(to_md(pg, res), encoding="utf-8")
        total += res["meta"]["cost_usd"]
        done += 1
        print(f"[{i}/{len(pages)}] {pg['key']}: {len(res['blocks'])} blocks, "
              f"{res['meta']['seconds']} s, ${res['meta']['cost_usd']:.4f}", flush=True)
    print(f"{done} pages OCR'd this run, cost ${total:.4f}")


if __name__ == "__main__":
    main()
