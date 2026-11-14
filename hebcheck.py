"""Check the Hebrew words against Bochart's own romanization, in code (14-Nov-2026; no model call).

  uv run hebcheck.py                 # all the published chapters -> data/concordance/romanization_check.csv
  uv run hebcheck.py corvus struthio # only these chapters

In this type ו/ז, ד/ר, ח/ת/ה, ב/כ, י/ו/ן, ם/ס, ג/נ look alike, and all the OCR readers can agree on the wrong
letter, so the vote sees nothing (tranche 5: זנה read ונה next to "zana"). Bochart writes a romanization in
italics after most Hebrew words. This script builds, from the Hebrew letters, the pattern of the
romanizations that Bochart's system allows, and lists the words where

  swap   the romanization does not fit the word as transcribed, but fits it when ONE letter is changed
         for a look-alike: the first place to look on the scan
  nofit  the romanization has the same number of words and does not fit, with or without a swap
         (often a translation, not a romanization: a long list, for a quick look only)

Report only. A row is a question for the scan, not a correction: Bochart's romanization follows the
pointed word, and the printer made errors of his own (do not "correct" a letter against the romanization
without the scan; see AGENTS.md).
"""

import csv
import re
import sys
import unicodedata
from pathlib import Path

import concordance as C

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "concordance" / "romanization_check.csv"
V = "[aeiouyw]*"  # vowels between the consonants ("w" for the rare "aw")
# Hebrew letter -> what Bochart writes for it (he has g or nothing for ע, th for ת, ts for צ, ch for ח and כ)
LETTER = {
    "א": "", "ב": "bh|b|v", "ג": "gh|g", "ד": "dh|d", "ה": "h|", "ו": "v|u|w|", "ז": "z|s", "ח": "ch|hh|h",
    "ט": "t", "י": "j|i|", "כ": "ch|c|k", "ך": "ch|c|k", "ל": "l", "מ": "m", "ם": "m", "נ": "n", "ן": "n",
    "ס": "s", "ע": "gh|g|ng|h|", "פ": "ph|p|f", "ף": "ph|p|f", "צ": "ts|tz|z|s", "ץ": "ts|tz|z|s", "ק": "k|c|q",
    "ר": "rh|r", "ש": "sch|sh|s", "ת": "th|t",
}
ALIKE = [set("וזין"), set("דרך"), set("החת"), set("בכ"), set("םס"), set("גנ"), set("עצ"), set("טמ")]
PREFIX = "והבכלמש"


def pattern(word: str) -> re.Pattern:
    parts = []
    for ch in word:
        alt = LETTER[ch]
        if alt == "":
            continue
        opt = alt.endswith("|")
        alt = alt.rstrip("|")
        parts.append(f"(?:{alt}){{1,2}}" if not opt else f"(?:{alt}){{0,2}}")
    return re.compile(V + V.join(parts) + V)


def norm(rom: str) -> str:
    s = unicodedata.normalize("NFD", rom.lower())
    return re.sub(r"[^a-z]", "", s)


def fits(word: str, rom: str) -> bool:
    if pattern(word).fullmatch(rom):
        return True
    # the romanization often leaves out a prefix ("ut tsipparin" for כצפרין)
    return len(word) > 2 and word[0] in PREFIX and bool(pattern(word[1:]).fullmatch(rom))


def swaps(word: str):
    for i, ch in enumerate(word):
        for group in ALIKE:
            if ch in group:
                for other in sorted(group - {ch}):
                    final = other in "ךןם"
                    if final != (i == len(word) - 1) and other in "ךןם":
                        continue
                    yield word[:i] + other + word[i + 1:]


def check(row: dict) -> list[dict]:
    heb = [w for w in row["key"].split() if all(c in LETTER for c in w)]
    roms = [norm(w) for w in row["romanization"].split()]
    roms = [r for r in roms if r]
    if not heb or not roms:
        return []
    pairs = list(zip(heb, roms)) if len(heb) == len(roms) else (
        [(heb[0], r) for r in roms] if len(heb) == 1 and len(roms) <= 3 else [])
    if len(heb) == 1 and len(roms) > 1:  # "ut tsipparin", "tsab Mosis": one of the words is the romanization
        if any(fits(heb[0], r) for r in roms):
            return []
        pairs = [(heb[0], r) for r in roms]
    out = []
    for w, r in pairs:
        if fits(w, r):
            continue
        alt = [s for s in swaps(w) if fits(s, r)]
        out.append({"kind": "swap" if alt else "nofit", "word": w, "romanization": r,
                    "fits_as": " / ".join(dict.fromkeys(alt)), "hebrew": row["hebrew"],
                    "printed_romanization": row["romanization"], "chapter": row["chapter"], "page": row["page"],
                    "part": row["part"], "before": row["before"], "after": row["after"], "scan_url": row["scan_url"]})
    # for one Hebrew word against several words, keep the row only when no word fits; one row is enough
    if len(heb) == 1 and len(out) > 1:
        out = sorted(out, key=lambda x: x["kind"] != "swap")[:1]
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    only = set(sys.argv[1:])
    rows = [r for r in C.rows(require_en=False) if r["romanization"] and (not only or r["chapter"] in only)]
    found = [x for r in rows for x in check(r)]
    found.sort(key=lambda x: (x["kind"] != "swap", x["page"]))
    if found:
        C.write(OUT if not only else OUT.with_name("romanization_check_part.csv"), found)
    n = sum(x["kind"] == "swap" for x in found)
    print(f"{len(rows)} strings with a romanization; {n} words fit only with a look-alike letter, "
          f"{len(found) - n} do not fit (translations for the most part)")
    for x in found:
        if x["kind"] == "swap":
            print(f'p. {x["page"]} {x["chapter"]}: {x["word"]} "{x["romanization"]}" fits {x["fits_as"]} | '
                  f'{x["before"][-30:]} [{x["hebrew"]}] {x["after"][:40]}')


if __name__ == "__main__":
    main()
