"""Second reading, all scripts: flag every word where a second reader differs from the main OCR.

  uv run check.py 408 429                    # writes logs/check_v2-408-429.csv

Ported from lewysohn-zoologie's hebcheck.py, for every script, with two second readers:
Gemini 3.8 Flash and the MDZ hOCR. On the gold pages Opus's errors are "corrections" of the print
(نشز for نشر, caussa for causa, ὗραξ for ὕραξ, מבה״ח for מב״ח); the MDZ layer and Flash read more
literally, so a difference marks a word to check.

Words are compared on a key: NFC, <i> tags, margin marks and ^{} wrappers removed, punctuation
stripped; Hebrew without points, ״ and " the same; Arabic without vowel signs and tatweel (the
letters and dots are compared, the vowel signs are not); Greek with its accents. Against MDZ only:
f and s are the same (MDZ reads the long s as f); the hamza forms and ى are folded (أ إ آ -> ا,
ئ -> ي, ؤ -> و, ى -> ي: MDZ modernizes the Arabic, the print has no hamza); a comma or colon
glued to the next word is split off.
A difference where the same words come in another order is "order"; a span of more than 6 words
is "block" (text in another place: Flash's line order, note columns). Both are left to the page
join check, not to the judges.
A Greek flag where Flash agrees with the main OCR and MDZ differs only by an accent, by ε for the
ου ligature or by Φ for φ is "quirk": not judged (12-Nov-2026; see is_mdz_quirk). The same for a
Latin flag where MDZ differs only by in for m, tt/ft for ct/st, fl for ss, S for an initial s, or l/J
for I (13-Nov-2026; see is_latin_quirk).
Each flag has the line of the main OCR and, for the image judge, the box of the matching line in
the MDZ hOCR (found by fuzzy match).
"""

import argparse
import csv
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

from rapidfuzz import fuzz

import eval as ev

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
DATA = ROOT / "data"
HEB_POINTS = re.compile(r"[֑-ׇ]")
AR_MARKS = re.compile(r"[ً-ٰٟـ]")  # vowel signs, superscript alif, tatweel
PUNCT = re.compile(r"^[^\w֐-ۿ܀-ݏࠀ-࠿ሀ-᎟]+|[^\w֐-ۿ܀-ݏࠀ-࠿ሀ-᎟]+$")
LINE = re.compile(r'<span class="ocr_line" title="bbox (\d+) (\d+) (\d+) (\d+)"[^>]*>(.*?)</span>\s*(?=<span class="ocr_line"|</p>)', re.S)


MDZ_FOLD = str.maketrans({"f": "s", "أ": "ا", "إ": "ا", "آ": "ا", "ئ": "ي", "ؤ": "و", "ى": "ي"})


def key(word: str, mdz: bool = False) -> str:
    w = PUNCT.sub("", unicodedata.normalize("NFC", word)).replace("ſ", "s").replace('"', "״")
    w = AR_MARKS.sub("", HEB_POINTS.sub("", w))
    return w.translate(MDZ_FOLD) if mdz else w


def quirk_fold(word: str) -> str:
    """The key against MDZ without the differences that are MDZ's habit in Greek: accents and
    breathings, the ου ligature (ȣ) read as ε, and the lower-case φ of this type read as Φ."""
    k = "".join(c for c in unicodedata.normalize("NFD", key(word, True)) if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", k).replace("ου", "ε").replace("ȣ", "ε").replace("Φ", "φ")


def latin_fold(word: str) -> str:
    """The key against MDZ without MDZ's habits in the Latin of this type (13-Nov-2026): m read as in/ın
    (cuin, quaın), ct and the long-s st read as tt/ft (fatta, noftis), ss read as fl (fuifle), a capital S
    for an initial long s, and l or J for a capital I (ludaei, Jerichuntem). Accents and the other
    capitals are not folded: MDZ found quò and Ie for Je that way."""
    k = key(word, True).replace("ı", "i")
    k = re.sub(r"^[lJS]", lambda m: "s" if m.group(0) == "S" else "I", k)
    return k.replace("m", "in").replace("ct", "tt").replace("st", "tt").replace("sl", "ss")


def is_latin_quirk(row: dict) -> bool:
    """Latin flag where Flash reads exactly as the main OCR and MDZ differs only by the habits of
    latin_fold. Measured on tranches 2-4: about 100-150 flags a tranche; the judge kept all but 5, and
    those 5 were the judge following MDZ (cuin, quain, Certuin, coluinbae, sinaragdis)."""
    if row["script"] != "Latin" or not row["flash"] or not row["mdz"]:
        return False
    m = row["main"].split()
    if any(re.match(r"[lJ]", w) for w in (key(x, True) for x in m)):  # main has l/J itself: no fold of the initial
        return False
    return ([key(w) for w in m] == [key(w) for w in row["flash"].split()]
            and [latin_fold(w) for w in m] == [latin_fold(w) for w in row["mdz"].split()])


def is_mdz_quirk(row: dict) -> bool:
    """Greek flag where Flash reads exactly as the main OCR and MDZ differs only by its habits
    (12-Nov-2026). In tranche 3 that was 187 of 1,467 flags; the judge kept 160 and changed 2, both
    an iota subscript. Such a flag gets the kind "quirk": listed in the CSV, not sent to the judge."""
    if is_latin_quirk(row):
        return True
    if row["script"] != "Greek" or not row["flash"] or not row["mdz"]:
        return False
    m = row["main"].split()
    return ([key(w) for w in m] == [key(w) for w in row["flash"].split()]
            and [quirk_fold(w) for w in m] == [quirk_fold(w) for w in row["mdz"].split()])


def tokens(engine: str, page: str) -> tuple[list[tuple[str, int]], list[str]]:
    """-> [(word, line index)], lines (furniture left out; loose normalization of eval.py)."""
    f = DATA / "ocr" / engine / f"{page}.json"
    if not f.exists():
        return [], []
    ev.LOOSE = True
    blocks = json.loads(f.read_text(encoding="utf-8"))["blocks"]
    text = "\n".join((b.get("marker", "") + " " if b.get("marker") else "") + b["text"]
                     for b in blocks if b["type"] != "furniture")
    if engine == "mdz":
        text = re.sub(r"([,;:])(?=\S)", r"\1 ", text)
    lines = [ev.norm(ln) for ln in text.split("\n")]
    toks = [(w, i) for i, ln in enumerate(lines) for w in ln.split() if PUNCT.sub("", w)]
    return toks, lines


def span(ops, i1: int, i2: int) -> tuple[int, int]:
    """The reader's token range aligned to main[i1:i2]."""
    js = []
    for tag, a1, a2, b1, b2 in ops:
        if a2 <= i1 and not (a1 == a2 == i1) or a1 >= i2 and not (a1 == a2 == i2 and i1 == i2):
            continue
        if tag == "equal":
            js += [b1 + max(i1, a1) - a1, b1 + min(i2, a2) - a1]
        else:
            js += [b1, b2]
    return (min(js), max(js)) if js else (0, 0)


def script_of(text: str) -> str:
    counts = {}
    for ch in text:
        s = ev.script(ch)
        if s != "common":
            counts[s] = counts.get(s, 0) + 1
    if re.search(r"[ሀ-᎟]", text):
        return "Ethiopic"
    if re.search(r"[ࠀ-࠿]", text):
        return "Samaritan"
    return max(counts, key=counts.get) if counts else "common"


def mdz_lines(page: str) -> list[tuple[tuple[int, int, int, int], str]]:
    f = DATA / "mdz_hocr" / f"{page}.hocr"
    if not f.exists():
        return []
    return [(tuple(map(int, m.groups()[:4])), re.sub(r"<[^>]+>", "", m.group(5)))
            for m in LINE.finditer(f.read_text(encoding="utf-8"))]


def find_box(line: str, boxes) -> tuple[str, float]:
    if not boxes:
        return "", 0
    k = key(line, True)
    best = max(boxes, key=lambda b: fuzz.ratio(k, key(b[1], True)))
    return " ".join(map(str, best[0])), round(fuzz.ratio(k, key(best[1], True)))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("first", type=int)
    p.add_argument("last", type=int)
    p.add_argument("--vol", type=int, default=2)
    p.add_argument("--main", default="or-claude-opus-5.5@low")
    p.add_argument("--flash", default="or-gemini-3.8-flash@low")
    p.add_argument("--run", default="", help="suffix of the check CSV, e.g. .argon (another main OCR)")
    p.add_argument("--no-quirk-rule", action="store_true", help="send the Greek MDZ-habit flags to the judge too (as before 12-Nov-2026)")
    a = p.parse_args()
    rows, n_words = [], 0
    for page in range(a.first, a.last + 1):
        pk = f"v{a.vol}-{page:04d}"
        m, lines = tokens(a.main, pk)
        if not m:
            print(f"{pk}: no main OCR, skipped")
            continue
        n_words += len(m)
        readers = {"flash": tokens(a.flash, pk)[0], "mdz": tokens("mdz", pk)[0]}
        for name in [n for n, r in readers.items() if not r]:  # an absent reader would flag the whole page as one block
            print(f"{pk}: no {name} OCR (run mdz_ocr.py / ocr.py); compared without it")
            del readers[name]
        if not readers:
            continue
        ops, spans = {}, []
        for name, r in readers.items():
            mdz = name == "mdz"
            sm = difflib.SequenceMatcher(None, [key(w, mdz) for w, _ in m], [key(w, mdz) for w, _ in r], autojunk=False)
            ops[name] = sm.get_opcodes()
            for tag, i1, i2, j1, j2 in ops[name]:
                if tag == "equal" or i1 == i2:  # an insertion in the reader: not a word of the main OCR
                    continue
                spans.append([i1, i2])
        spans.sort()
        merged = []
        for s in spans:  # union of overlapping spans of the two readers
            if merged and s[0] < merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], s[1])
            else:
                merged.append(s)
        boxes = mdz_lines(pk)
        for i1, i2 in merged:
            mw = " ".join(w for w, _ in m[i1:i2])
            row = {"page": pk, "script": script_of(mw), "main": mw}
            for name in ("flash", "mdz"):
                r = readers.get(name)
                j1, j2 = span(ops[name], i1, i2) if r else (0, 0)
                row[name] = " ".join(w for w, _ in r[j1:j2]) if r else ""
            mk = sorted(key(w, True) for w, _ in m[i1:i2])
            row["kind"] = ("order" if i2 - i1 > 1 and all(sorted(key(w, True) for w in row[n].split()) == mk
                                                          for n in readers if row[n])
                           else "block" if i2 - i1 > 6 else "replace")
            if row["kind"] == "replace" and not a.no_quirk_rule and is_mdz_quirk(row):
                row["kind"] = "quirk"
            li = m[i1][1]
            row["line"] = lines[li]
            row["line_no"] = li
            row["box"], row["box_match"] = find_box(lines[li], boxes)
            rows.append(row)
    out = ROOT / "logs" / f"check_v{a.vol}-{a.first}-{a.last}{a.run}.csv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["page", "script", "kind", "main", "flash", "mdz", "line", "line_no", "box", "box_match"])
        w.writeheader()
        w.writerows(rows)
    tally = {}
    for r in rows:
        tally[r["script"]] = tally.get(r["script"], 0) + 1
    weak = sum(1 for r in rows if r["box_match"] and float(r["box_match"]) < 70)
    print(f"{n_words} words in {a.main}; {len(rows)} flags {tally}; "
          f"{sum(r['kind'] == 'order' for r in rows)} order, {sum(r['kind'] == 'block' for r in rows)} block, {sum(r['kind'] == 'quirk' for r in rows)} quirk (not judged); {weak} with a weak line match; wrote {out}")


if __name__ == "__main__":
    main()
