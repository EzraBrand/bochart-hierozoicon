"""The long Syriac blocks (vol. 3 p. 283; README "not transcribed"), 20-Nov-2026.
Rosenmüller copied the left block of p. 283 from Barhebraeus, Chronicon Syriacum, ed. Bruns and Kirsch (Leipzig
1789), vol. 2 (the Syriac text), p. 134 (archive.org item ChroniconSyriacum, "Chronicon_Syriacum 2", leaf 503,
3898 x 5040 px: about twice the resolution of the MDZ scan; saved through the browser to logs/syriac/v2_0503.jpg).
Two prints of one text in a similar type: if the readings of both agree, the text is right with high probability.
  uv run syriac_block.py lines IMAGE X0 Y0 X1 Y1 NAME      # cut a region into line crops -> logs/syriac/NAME/
  uv run syriac_block.py read NAME METHOD                   # read each line -> logs/syriac/NAME/METHOD.json
  uv run syriac_block.py compare A.json B.json              # align two readings (consonants), print agreement
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image
from rapidfuzz.distance import Levenshtein

from peshcheck import SYR, cons
from syriac_lab import ask

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "logs" / "syriac"

LINE_PROMPT = """This is one printed line of Syriac (West Syriac / Serto type, Leipzig, about 1790), from a chronicle.
Transcribe exactly the letters that are printed, in Unicode Syriac, right to left as usual, consonants only (leave out
vowel signs; keep the seyame dots as U+0308 only if printed). Do not correct toward a text you know or expect; if a letter
is unclear, give the letter that its shape shows. Keep the word spaces and the punctuation dots as printed.
Answer with JSON only: {"syriac": ["word1", "word2", ...]} (the words in reading order)."""

METHODS = {
    "opus-low": ("anthropic/claude-opus-5.5", "low"),
    "opus-high": ("anthropic/claude-opus-5.5", "high"),
    "flash": ("google/gemini-3.8-flash", "low"),
    "argon": ("google/gemini-4-argon", "low"),
    "gpt": ("openai/gpt-6.1-sol", "low"),
}


def lines(path: str, x0: int, y0: int, x1: int, y1: int, name: str) -> None:
    d = OUT / name
    d.mkdir(parents=True, exist_ok=True)
    im = Image.open(path).convert("L").crop((x0, y0, x1, y1))
    a = np.asarray(im) < 128
    prof = np.convolve(a.sum(axis=1), np.ones(5) / 5, mode="same")
    # Syriac lines are set close: dots and descenders fill the gaps, so the cut is at a low valley, not at zero
    thr = max(3, prof.max() * float(__import__("os").environ.get("SYR_THR", "0.03")))
    on = prof > thr
    spans, start = [], None
    for y, v in enumerate(on):
        if v and start is None:
            start = y
        if not v and start is not None:
            if y - start > 6:
                spans.append([start, y])
            start = None
    if start is not None:
        spans.append([start, len(on)])
    # join a span of dots (above or below) with its line: a span thinner than 40% of the median goes to the nearest
    med = np.median([b - t for t, b in spans])
    merged = []
    for s in spans:
        if merged and (s[1] - s[0] < 0.4 * med or merged[-1][1] - merged[-1][0] < 0.4 * med) and s[0] - merged[-1][1] < 0.5 * med:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    meta = []
    for i, (t, b) in enumerate(merged):
        pad = int(0.25 * med)
        c = im.crop((0, max(t - pad, 0), im.width, min(b + pad, im.height)))
        c.save(d / f"line_{i:02d}.jpg", quality=92)
        meta.append({"i": i, "box": [x0, y0 + t, x1, y0 + b]})
    (d / "lines.json").write_text(json.dumps(meta), encoding="utf-8")
    sheet = Image.new("L", (im.width + 120, sum(Image.open(d / f"line_{m['i']:02d}.jpg").height + 6 for m in meta)), 255)
    from PIL import ImageDraw
    dr, y = ImageDraw.Draw(sheet), 0
    for m in meta:
        c = Image.open(d / f"line_{m['i']:02d}.jpg")
        sheet.paste(c, (120, y))
        dr.text((10, y + c.height // 3), str(m["i"]), fill=0, font_size=max(20, c.height // 2))
        y += c.height + 6
    sheet.save(d / "sheet.jpg", quality=85)
    print(name, len(meta), "lines; median height", med)


def read(name: str, method: str) -> None:
    d = OUT / name
    meta = json.loads((d / "lines.json").read_text(encoding="utf-8"))
    out = d / f"{method}.json"
    res = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    model, effort = METHODS[method]

    def one(m):
        if str(m["i"]) in res:
            return m["i"], res[str(m["i"])], 0.0
        img = Image.open(d / f"line_{m['i']:02d}.jpg")
        try:
            w, c = ask(model, effort, img, LINE_PROMPT)
        except Exception as e:
            print(m["i"], "FAILED", e, flush=True)
            return m["i"], None, 0.0
        return m["i"], w, c

    cost = 0.0
    with ThreadPoolExecutor(8) as ex:
        for i, w, c in ex.map(one, meta):
            if w is not None:
                res[str(i)] = w
            cost += c
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{name} {method}: {len(res)}/{len(meta)} lines, ${cost:.3f}")


def text_of(path: Path, keep=None) -> list[str]:
    res = json.loads(path.read_text(encoding="utf-8"))
    ws = []
    for k in sorted(res, key=int):
        if keep and int(k) not in keep:
            continue
        ws += [cons(w) for w in res[k] if cons(w)]
    return ws


def align(a: list[str], b: list[str]):
    """word alignment (edit distance over words, substitution cost = normalized letter distance)"""
    n, m = len(a), len(b)
    D = np.zeros((n + 1, m + 1))
    D[:, 0] = np.arange(n + 1)
    D[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            s = Levenshtein.normalized_distance(a[i - 1], b[j - 1])
            D[i, j] = min(D[i - 1, j] + 1, D[i, j - 1] + 1, D[i - 1, j - 1] + s)
    i, j, pairs = n, m, []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and D[i, j] == D[i - 1, j - 1] + Levenshtein.normalized_distance(a[i - 1], b[j - 1]):
            pairs.append((a[i - 1], b[j - 1])); i -= 1; j -= 1
        elif i > 0 and D[i, j] == D[i - 1, j] + 1:
            pairs.append((a[i - 1], "")); i -= 1
        else:
            pairs.append(("", b[j - 1])); j -= 1
    return pairs[::-1]


def compare(pa: str, pb: str) -> None:
    a, b = text_of(Path(pa)), text_of(Path(pb))
    pairs = align(a, b)
    same = sum(1 for x, y in pairs if x and x == y)
    print(f"{Path(pa).parent.name}/{Path(pa).stem} {len(a)} words, {Path(pb).parent.name}/{Path(pb).stem} {len(b)} words: "
          f"{same} words agree ({same / max(len(a), len(b)):.0%})")
    return pairs


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "lines":
        lines(sys.argv[2], *map(int, sys.argv[3:7]), sys.argv[7])
    elif cmd == "read":
        for m in sys.argv[3:]:
            read(sys.argv[2], m)
    elif cmd == "compare":
        compare(sys.argv[2], sys.argv[3])
