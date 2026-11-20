"""Syriac reading test (20-Nov-2026, GitHub issue 4). Which method reads Bochart's Serto type best?
  uv run syriac_lab.py items                 # build logs/syriac/items.json and the line crops
  uv run syriac_lab.py run METHOD [...]      # read every item with a method -> logs/syriac/res_METHOD.json
  uv run syriac_lab.py score                 # table of character errors per method
Items with a known answer: (1) Peshitta quotations that peshcheck.py places with a score of 85 or more (the
answer is the Peshitta's consonants; Bochart's edition can differ, so a "wrong" letter is looked at on the scan);
(2) Syriac words that the scan checks of tranches 1-10 corrected in entry.FIXES; (3) the words of issue 4.
Methods: the voted OCR (baseline), models on the line crop (plain or with a Serto glyph guide), Tesseract syr.
"""
import base64
import csv
import io
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from PIL import Image
from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

import entry
from peshcheck import SYR, cons, page_text

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "logs" / "syriac"
VOTED = ROOT / "data" / "ocr" / "or-claude-opus-5.5@low+vote"
KEY_FILE = Path(os.environ.get("OPENROUTER_KEY_FILE", ROOT.parent / "bochart-hierozoicon.txt"))
TESS = Path.home() / "AppData/Local/Programs/Tesseract-OCR/tesseract.exe"
TESSDATA = ROOT.parent / "low-flora" / "tessdata"

# issue 4 (vol. 3 p. 207, first line): read on the scan by Claude with Bochart's argument (Koph and Ajin change
# places: Aramaic ארקא/ארעא, קטר/עטר, ...). The fourth word is not certain; it is left out of the score.
ISSUE4 = {"key": "v3-0207", "phrase": "et frigus, et. Et Ionathani", "truth": ["ܐܪܩܐ", "ܩܛܪ", "ܥܛܪ", "ܩܘܪܐ"],
          "src": "issue4", "ocr": ["ܐܬܢܢ", "ܩܘܦܣ", "ܟܦܣ", "ܩܘܦܣܐ"]}

GUIDE = """The Syriac is in the West Syriac (Serto) printing type of 1793. Shapes that readers confuse in this type:
- ܩ qof: a round loop with a short tail, open at the top; ܘ waw: a small closed round loop on the line, no tail.
- ܛ teth: a loop like a figure 8 or a 'ɗ', taller than the line; ܦ pe: a small loop with a stroke, not taller.
- ܪ rish has ONE dot ABOVE, ܕ dalath has ONE dot BELOW; both are the same small hook otherwise.
- ܥ ʿe: a shallow open curve like a 'د' or 'ب' with a hook; ܟ kaph: a bowl with a horizontal stroke; ܓ gamal: a
  slanting stroke.
- ܐ alaph: initial/isolated a tall vertical stroke ('|'); final alaph after a joining letter is a horizontal tail
  with a hook ('ʅ').
- ܢ nun final is a long descender; ܝ yod is a small tooth with a dot-like stroke under it.
- Two dots above (seyame ̈) mark a plural; ignore vowel signs.
Read letter by letter from right to left. Do not guess a word from what the Latin context suggests."""

PROMPT = """This is one printed line from Bochart's Hierozoicon (Leipzig, 1793-96). It mixes Latin with words in
other scripts. Transcribe ONLY the words in Syriac script, in the order they appear in the line (reading the line
left to right, each Syriac word right to left), in Unicode Syriac letters, consonants only (no vowel points).
{guide}
Answer with JSON only: {{"syriac": ["word1", "word2", ...]}}"""


def mdz_lines(key: str) -> list[tuple[tuple[int, int, int, int], str]]:
    t = (ROOT / "data" / "mdz_hocr" / f"{key}.hocr").read_text(encoding="utf-8")
    return [(tuple(map(int, m.groups()[:4])), re.sub(r"<[^>]+>", "", m.group(5)).replace("ſ", "s"))
            for m in re.finditer(r'class="ocr_line" title="bbox (\d+) (\d+) (\d+) (\d+)"[^>]*>(.*?)</span>\s*'
                                 r'(?=<span class="ocr_line"|</p>)', t, re.S)]


def latin_of(line: str) -> str:
    s = re.sub(r"<[^>]+>|\^\{[^}]*\}|⟦[^⟧]*⟧", " ", line)
    return " ".join(re.findall(r"[A-Za-z]{2,}", s))


def find_line(key: str, phrase: str) -> tuple[int, int, int, int] | None:
    L = mdz_lines(key)
    if not L or not phrase:
        return None
    i = max(range(len(L)), key=lambda k: fuzz.partial_ratio(phrase, L[k][1]))
    return L[i][0] if fuzz.partial_ratio(phrase, L[i][1]) >= 60 else None


def crop(key: str, box) -> Image.Image:
    im = Image.open(ROOT / "data" / "raw" / f"{key}.jpg").convert("L")
    x0, y0, x1, y1 = box
    h = y1 - y0
    return im.crop((max(x0 - 40, 0), max(y0 - int(0.45 * h), 0), min(x1 + 40, im.width), min(y1 + int(0.45 * h), im.height)))


def build_items():
    OUT.mkdir(parents=True, exist_ok=True)
    items = []
    # (1) Peshitta quotations
    for r in csv.DictReader(open(ROOT / "data" / "concordance" / "peshitta_check.csv", encoding="utf-8-sig")):
        if int(r["score"]) < 85:
            continue
        key, words = r["page"], r["ocr"].split()
        text = page_text(VOTED / f"{key}.json")
        line = next((ln for ln in text.split("\n") if words[0] in ln), "")
        items.append({"key": key, "phrase": latin_of(line), "truth": r["peshitta"].split(), "ocr": words,
                      "src": "peshitta " + r["ref"]})
    # (2) scan-checked Syriac words in entry.FIXES
    for k, pairs in entry.FIXES.items():
        vol, pg = k if isinstance(k, tuple) else (2, k)
        key = f"v{vol}-{pg:04d}"
        if not (VOTED / f"{key}.json").exists():
            continue
        text = page_text(VOTED / f"{key}.json")
        for old, new in pairs:
            tw, ow = SYR.findall(new), SYR.findall(old)
            if not tw or "[" in old or len(new) > 200:
                continue
            ref = ow[0] if ow else None
            line = next((ln for ln in text.split("\n") if ref and ref in ln), "")
            if not line:
                continue
            items.append({"key": key, "phrase": latin_of(line), "truth": tw, "ocr": ow, "src": "fixes"})
    items.append(ISSUE4)
    keep = []
    for n, it in enumerate(items):
        box = find_line(it["key"], it["phrase"])
        if not box:
            print("no line:", it["key"], it["src"], it["truth"])
            continue
        it["id"] = len(keep)
        it["box"] = box
        crop(it["key"], box).save(OUT / f"item_{it['id']:03d}.jpg", quality=92)
        keep.append(it)
    (OUT / "items.json").write_text(json.dumps(keep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(keep), "items;", sum(1 for i in keep if i["src"].startswith("peshitta")), "Peshitta,",
          sum(1 for i in keep if i["src"] == "fixes"), "FIXES")


def ask(model: str, effort: str | None, img: Image.Image, prompt: str, scale: float = 1.0) -> tuple[list[str], float]:
    if scale != 1.0:
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    content = [{"type": "image_url", "image_url": {
        "url": "data:image/jpeg;base64," + base64.standard_b64encode(buf.getvalue()).decode()}},
        {"type": "text", "text": prompt}]
    body = {"model": model, "max_tokens": 8000, "messages": [{"role": "user", "content": content}],
            "usage": {"include": True}}
    if effort:
        body["reasoning"] = {"effort": effort}
    for attempt in range(3):
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                          headers={"Authorization": "Bearer " + KEY_FILE.read_text(encoding="utf-8").strip()},
                          json=body, timeout=300)
        d = r.json()
        if r.ok and "error" not in d:
            break
        time.sleep(5)
    else:
        raise RuntimeError(f"HTTP {r.status_code}: {str(d.get('error', d))[:200]}")
    text = (d["choices"][0]["message"]["content"] or "").strip()
    m = re.search(r"\{.*\}", text, re.S)
    try:
        words = json.loads(m.group())["syriac"] if m else []
    except Exception:
        words = SYR.findall(text)
    return [w for w in words if isinstance(w, str)], d.get("usage", {}).get("cost", 0) or 0


def tesseract(img: Image.Image) -> list[str]:
    p = OUT / "_tess.png"
    img.resize((img.width * 2, img.height * 2), Image.LANCZOS).save(p)
    r = subprocess.run([str(TESS), str(p), "-", "--tessdata-dir", str(TESSDATA), "-l", "syr", "--psm", "7"],
                       capture_output=True, text=True, encoding="utf-8")
    return SYR.findall(r.stdout)


METHODS = {
    "opus-low": ("anthropic/claude-opus-5.5", "low", False, 1.0),
    "opus-low-guide": ("anthropic/claude-opus-5.5", "low", True, 1.0),
    "opus-high-guide": ("anthropic/claude-opus-5.5", "high", True, 1.0),
    "opus-low-guide-2x": ("anthropic/claude-opus-5.5", "low", True, 2.0),
    "flash": ("google/gemini-3.8-flash", "low", False, 1.0),
    "flash-guide": ("google/gemini-3.8-flash", "low", True, 1.0),
    "argon-guide": ("google/gemini-4-argon", "low", True, 1.0),
    "gpt-guide": ("openai/gpt-6.1-sol", "low", True, 1.0),
    "sonnet-guide": ("anthropic/claude-sonnet-5.5", "low", True, 1.0),
}


def run(method: str):
    items = json.loads((OUT / "items.json").read_text(encoding="utf-8"))
    out = OUT / f"res_{method}.json"
    res = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    todo = [it for it in items if str(it["id"]) not in res]

    def one(it):
        img = Image.open(OUT / f"item_{it['id']:03d}.jpg")
        if method == "tesseract":
            return it["id"], tesseract(img), 0.0
        model, effort, guide, scale = METHODS[method]
        try:
            w, c = ask(model, effort, img, PROMPT.format(guide=GUIDE if guide else ""), scale)
        except Exception as e:
            print(it["id"], "FAILED", e, flush=True)
            return it["id"], None, 0.0
        return it["id"], w, c

    cost = 0.0
    with ThreadPoolExecutor(1 if method == "tesseract" else 8) as ex:
        for i, w, c in ex.map(one, todo):
            if w is not None:
                res[str(i)] = w
            cost += c
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{method}: {len(res)}/{len(items)} items, ${cost:.3f}", flush=True)


def errors(truth: list[str], read: list[str]) -> tuple[int, int]:
    """character errors of the best alignment of the read words to the truth words (consonants only).
    Words read in the line that are not in the item are ignored: each truth word takes its closest read word."""
    rc = [cons(w) for w in read]
    e = 0
    for t in truth:
        tc = cons(t)
        e += min([Levenshtein.distance(tc, r) for r in rc] or [len(tc)])
    return e, sum(len(cons(t)) for t in truth)


def score():
    items = json.loads((OUT / "items.json").read_text(encoding="utf-8"))
    rows = []
    methods = ["baseline"] + sorted(p.stem[4:] for p in OUT.glob("res_*.json"))
    for m in methods:
        res = None if m == "baseline" else json.loads((OUT / f"res_{m}.json").read_text(encoding="utf-8"))
        tot = {"all": [0, 0, 0, 0], "peshitta": [0, 0, 0, 0], "fixes": [0, 0, 0, 0], "issue4": [0, 0, 0, 0]}
        for it in items:
            read = it["ocr"] if m == "baseline" else res.get(str(it["id"]))
            if read is None:
                continue
            e, n = errors(it["truth"], read)
            ok = sum(1 for t in it["truth"] if cons(t) in {cons(r) for r in read})
            for g in ("all", it["src"].split()[0]):
                tot[g][0] += e
                tot[g][1] += n
                tot[g][2] += ok
                tot[g][3] += len(it["truth"])
        rows.append((m, tot))
    print(f"{'method':22} " + "  ".join(f"{g:>22}" for g in ("all", "peshitta", "fixes", "issue4")))
    print(f"{'':22} " + "  ".join(f"{'CER   words right':>22}" for _ in range(4)))
    for m, tot in rows:
        cells = []
        for g in ("all", "peshitta", "fixes", "issue4"):
            e, n, ok, nw = tot[g]
            cells.append(f"{(e / n if n else 0):6.1%} {ok:4d}/{nw:<4d}      ")
        print(f"{m:22} " + "  ".join(f"{c:>22}" for c in cells))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "items":
        build_items()
    elif cmd == "run":
        for m in sys.argv[2:]:
            run(m)
    elif cmd == "score":
        score()
