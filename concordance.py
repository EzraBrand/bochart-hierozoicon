"""Concordance of the Hebrew-letter strings in the published chapters, for a reader's QA (13-Nov-2026).

  uv run concordance.py        # writes data/concordance/hebrew.csv and hebrew_words.csv

A string is a run of consecutive words in Hebrew letters (Hebrew and Aramaic; the Hebrew letters that
a program adds after Syriac are not in the Latin text and so not here). It is taken from the Latin side
(la.json: the transcription after the vote and the scan check), with the words before and after it and
Bochart's romanization where one follows in italics.

hebrew.csv        one row per occurrence, in the order of the book
hebrew_words.csv  one row per distinct word: count, pages, and "looks_like" = other words of the
                  concordance that differ only by letters that look alike in this type (ד/ר, ה/ח/ת,
                  ו/ז/י/ן, ב/כ, ם/ס, ג/נ, ע/צ). A rare word next to a frequent look-alike is where an OCR
                  error is most likely.
build_site.py makes docs/hebrew.html from the same rows.
"""

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = DATA / "concordance"
MDZ_VIEW = "https://www.digitale-sammlungen.de/en/view"
SITE = "https://ezrabrand.github.io/bochart-hierozoicon"
HEB = r"[א-ת][֑-ׇא-תװ-״\"'’]*"
RUN = re.compile(rf"{HEB}(?:[  ־\-]+{HEB})*")
PAGE_MARK = re.compile(r"\[(I{1,3}), (\d+)\]")
TAGS = re.compile(r"</?i>|\^\{[^}]*\}|⟦[^⟧]*⟧|\[col\. \d+\]|\[I{1,3}, \d+\]")
ROMAN = re.compile(r"\s*[,(]?\s*(?:\(\s*)?<i>([^<]{1,60})</i>")
POINTS = re.compile(r"[֑-ׇ]")
# letters that look alike in the Hebrew type of this edition -> one class
ALIKE = str.maketrans({"ר": "ד", "ח": "ה", "ת": "ה", "ז": "ו", "י": "ו", "ן": "ו", "כ": "ב", "ס": "ם",
                       "נ": "ג", "צ": "ע", "ך": "ד"})


def key(s: str) -> str:
    """Unpointed, without punctuation: the form that is counted."""
    return re.sub(r"[^א-ת ]", "", POINTS.sub("", s.replace("־", " ").replace("-", " "))).strip()


def clean(s: str) -> str:
    return " ".join(TAGS.sub("", s).split())


def rows(require_en: bool = True) -> list[dict]:
    import build_site as B
    ids = B.scan_ids()
    out = []
    for d in B.DOCS:
        f = DATA / "entries" / d["entry"] / "la.json"
        if d["kind"] != "entry" or not f.exists() or (require_en and not (f.parent / "en.json").exists()):
            continue
        la = json.loads(f.read_text(encoding="utf-8"))
        for part in ("main", "notes"):
            for b in la[part]:
                text = b["text"].replace("-\n", "").replace("\n", " ")
                marks = [(m.start(), int(m.group(2))) for m in PAGE_MARK.finditer(text)]
                for m in RUN.finditer(text):
                    if not key(m.group(0)):
                        continue
                    page = max([(pos, p) for pos, p in marks if pos < m.start()], default=(0, b["page"]))[1]
                    after = text[m.end():m.end() + 160]
                    rom = ROMAN.match(after)
                    canvas = ids.get(B.page_key(d["vol"], page))
                    out.append({
                        "hebrew": m.group(0), "key": key(m.group(0)), "words": len(key(m.group(0)).split()),
                        "romanization": rom.group(1).strip(" ,.;:") if rom else "",
                        "chapter": d["slug"], "page": page, "part": "text" if part == "main" else "note",
                        "before": clean(text[max(0, m.start() - 90):m.start()])[-70:],
                        "after": clean(after)[:90],
                        "scan_url": f"{MDZ_VIEW}/{B.VOL_IDS[d['vol']]}?page={canvas}" if canvas else "",
                        "site_url": f"{SITE}/{d['slug']}.html"})
    return out


def words(occ: list[dict]) -> list[dict]:
    by = defaultdict(list)
    for r in occ:
        for w in r["key"].split():
            by[w].append(r)
    classes = defaultdict(set)
    for w in by:
        classes[w.translate(ALIKE)].add(w)
    out = []
    for w, rs in by.items():
        pages = sorted({r["page"] for r in rs})
        like = sorted(classes[w.translate(ALIKE)] - {w}, key=lambda x: -len(by[x]))
        out.append({"word": w, "count": len(rs), "pages": " ".join(map(str, pages)),
                    "looks_like": "; ".join(f"{x} ({len(by[x])})" for x in like),
                    "first_context": f'{rs[0]["before"]} {rs[0]["hebrew"]} {rs[0]["after"]}'})
    return sorted(out, key=lambda r: r["word"])


def write(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    occ = rows()
    ws = words(occ)
    write(OUT / "hebrew.csv", occ)
    write(OUT / "hebrew_words.csv", ws)
    print(f"{len(occ)} Hebrew strings ({len({r['key'] for r in occ})} distinct) in "
          f"{len({r['chapter'] for r in occ})} chapters; {len(ws)} distinct words, "
          f"{sum(1 for w in ws if w['looks_like'])} with a look-alike; wrote {OUT}")


if __name__ == "__main__":
    main()
