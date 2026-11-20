"""Check the Syriac quotations of the Bible against the Peshitta, in code (20-Nov-2026; no model call).
  uv run peshcheck.py                 # every voted page -> data/concordance/peshitta_check.csv
  uv run peshcheck.py 3:270-330       # a range of pages of one volume
The Peshitta text (Old Testament) is the ETCBC plain text (github.com/ETCBC/peshitta, plain/0.2), in
data/peshitta/ (gitignored; fetch with `gh api repos/ETCBC/peshitta/contents/plain/0.2/FILE -H "Accept:
application/vnd.github.raw"`). As biblecheck.py does for the Hebrew: every run of Syriac words in the voted OCR
(two words or more) is placed in the Peshitta by fuzzy match of the consonants, and the words are compared.
In Serto print, ܛ/ܦ/ܩ, ܪ/ܕ, ܢ/ܝ, ܥ/ܟ/ܓ and ܘ/ܩ are the readers' usual confusions; all readers can agree on
the wrong letter. Report only: Bochart quotes from memory and from other editions (the Paris and London
Polyglots), and the printer made errors of his own. A row is a question for the scan.
"""
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent
PESH = ROOT / "data" / "peshitta"
VOTED = ROOT / "data" / "ocr" / "or-claude-opus-5.5@low+vote"
OUT = ROOT / "data" / "concordance" / "peshitta_check.csv"
SYR = re.compile(r"[ܐ-ܯݍ-ݏ][܀-ݏ̣̰̈̃̄̇-̱]*")


def cons(w: str) -> str:
    """the consonants of a Syriac word: no vowel points, seyame or other marks"""
    w = unicodedata.normalize("NFD", w)
    return "".join(c for c in w if "ܐ" <= c <= "ܯ" or "ݍ" <= c <= "ݏ")


def load_peshitta() -> list[tuple[str, list[str]]]:
    """(reference, words) per verse; a verse that runs over two lines of the file is joined"""
    verses = []
    for f in sorted(PESH.glob("*.txt")):
        book, ch, ref, words = f.stem, "?", None, []
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            m = re.match(r"Chapter (\d+)", line)
            if m:
                ch = m.group(1)
                continue
            m = re.match(r"(\d+)\s+(.*)", line)
            if m:
                if ref:
                    verses.append((ref, words))
                ref, words = f"{book} {ch}:{m.group(1)}", [cons(w) for w in m.group(2).split() if cons(w)]
            elif ref:
                words += [cons(w) for w in line.split() if cons(w)]
        if ref:
            verses.append((ref, words))
    return verses


def page_text(path: Path) -> str:
    d = json.loads(path.read_text(encoding="utf-8"))
    return "\n".join(b.get("text", "") for b in d.get("blocks", []))


def runs(text: str, least: int = 2) -> list[list[str]]:
    """runs of Syriac words (only punctuation and spaces between them)"""
    out, cur, last = [], [], 0
    for m in SYR.finditer(text):
        gap = text[last:m.start()]
        if cur and re.search(r"[A-Za-z֐-ۿͰ-Ͽ\d]", gap):
            out.append(cur)
            cur = []
        cur.append(m.group())
        last = m.end()
    if cur:
        out.append(cur)
    return [r for r in out if len(r) >= least]


class Index:
    def __init__(self, verses):
        self.verses = verses
        self.by_word = defaultdict(set)
        for i, (_, ws) in enumerate(verses):
            for w in ws:
                self.by_word[w].add(i)

    def place(self, words: list[str]) -> tuple[float, str, list[str]]:
        """the verse (or two verses) whose window best matches the run"""
        ws = [cons(w) for w in words]
        cand = defaultdict(int)
        for w in set(ws):
            for i in self.by_word.get(w, ()):
                cand[i] += 1
        best = (0.0, "", [])
        q = " ".join(ws)
        for i, _ in sorted(cand.items(), key=lambda x: -x[1])[:200]:
            ref, vw = self.verses[i]
            if i + 1 < len(self.verses):
                vw = vw + self.verses[i + 1][1]
            n = len(ws)
            for s in range(0, max(1, len(vw) - n + 1)):
                win = vw[s:s + n]
                sc = fuzz.ratio(q, " ".join(win))
                if sc > best[0]:
                    best = (sc, ref, win)
        return best


def main():
    pages = sorted(VOTED.glob("v*.json"))
    if len(sys.argv) > 1:
        vol, _, rng = sys.argv[1].partition(":")
        a, _, b = rng.partition("-")
        pages = [p for p in pages if p.stem.startswith(f"v{vol}-") and int(a) <= int(p.stem[3:]) <= int(b or a)]
    idx = Index(load_peshitta())
    rows = []
    for p in pages:
        for r in runs(page_text(p)):
            sc, ref, win = idx.place(r)
            if sc < 70 or not ref:
                continue
            diffs = [(o, cons(o), v) for o, v in zip(r, win) if cons(o) != v]
            rows.append({"page": p.stem, "ref": ref, "score": round(sc), "words": len(r),
                         "ocr": " ".join(r), "peshitta": " ".join(win),
                         "diffs": " | ".join(f"{c}->{v}" for _, c, v in diffs if Levenshtein.distance(c, v) <= 2)})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["page"])
        w.writeheader()
        w.writerows(rows)
    exact = sum(1 for r in rows if not r["diffs"])
    print(f"{len(rows)} Syriac runs placed in the Peshitta ({exact} with no word difference of 1-2 letters); {OUT}")


if __name__ == "__main__":
    main()
