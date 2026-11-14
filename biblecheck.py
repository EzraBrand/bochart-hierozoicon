"""Check the Hebrew Bible quotations against the Masoretic text, in code (14-Nov-2026; no model call).

  uv run biblecheck.py fetch           # once: the consonantal Tanakh from the public Sefaria export (gcloud)
  uv run biblecheck.py                 # all the published chapters -> data/concordance/bible_check.csv
  uv run biblecheck.py corvus-nomina   # only these chapters

Most Hebrew in Bochart is a Bible quotation. In this type ו/ז, ד/ר, ח/ת/ה, ב/כ and others look alike, and
all the OCR readers can agree on the wrong letter. The Bible text is a reader that does not look at the
print at all: every Hebrew string of two words or more is placed in the Tanakh by its look-alike classes
(so a misread letter does not hide the verse), and the words are then compared letter by letter.

  kind "alike"   the word differs from the verse only by look-alike letters: read it on the scan
  kind "other"   another difference (a different word, an abbreviation, a variant, a quotation from memory)
A difference of full and defective spelling (ו, י) is not listed.

Report only: Bochart sometimes quotes a variant, the Targum, or the Talmud's form of a verse, and the printer
made errors of his own. A row is a question for the scan (AGENTS.md).
"""

import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

import concordance as C

ROOT = Path(__file__).resolve().parent
TANAKH = ROOT / "data" / "tanakh"
OUT = ROOT / "data" / "concordance" / "bible_check.csv"
BUCKET = "gs://sefaria-export/json/Tanakh"
VERSION = "Tanach with Text Only.json"
FINALS = str.maketrans("ךםןףץ", "כמנפצ")


def fetch() -> None:
    """The bucket is public; no sign-in is used (as in talmud-zoology-factcheck/fetch_sefaria.py)."""
    env = dict(os.environ, CLOUDSDK_AUTH_DISABLE_CREDENTIALS="true")
    TANAKH.mkdir(parents=True, exist_ok=True)
    ls = subprocess.run(["gcloud", "storage", "ls", f"{BUCKET}/*/*/Hebrew/{VERSION}"], env=env, check=True,
                        capture_output=True, text=True, shell=os.name == "nt").stdout.split("\n")
    urls = [u.strip() for u in ls if u.strip()]
    for i, u in enumerate(urls, 1):
        book = u.split("/")[-3]
        dest = TANAKH / f"{book}.json"
        if not dest.exists():
            subprocess.run(["gcloud", "storage", "cp", u, str(dest), "-q"], env=env, check=True, shell=os.name == "nt")
        print(f"{i}/{len(urls)} {book}", flush=True)


def fold(w: str) -> str:
    return w.translate(FINALS).translate(C.ALIKE).translate(FINALS)


def load() -> list[tuple[str, int, int, str]]:
    words = []
    for f in sorted(TANAKH.glob("*.json")):
        for c, chapter in enumerate(json.loads(f.read_text(encoding="utf-8"))["text"], 1):
            for v, verse in enumerate(chapter, 1):
                text = re.sub(r"<[^>]+>|\([^)]*\)|\[[^\]]*\]|&[a-z]+;", " ", verse).replace("־", " ")
                for w in re.sub(r"[^א-ת ]", "", text).split():
                    words.append((f.stem, c, v, w))
    return words


def skeleton(w: str) -> str:
    """Without the letters of full spelling: עורב = ערב."""
    return re.sub(r"[וי]", "", w.translate(FINALS))


def check(row: dict, words, index) -> list[dict]:
    heb = row["key"].split()
    if len(heb) < 2:
        return []
    f = [fold(w) for w in heb]
    votes = Counter()
    n = 3 if len(heb) >= 3 else 2
    for i in range(len(f) - n + 1):
        for pos in index[n].get(tuple(f[i:i + n]), ()):
            votes[pos - i] += 1
    if not votes:
        return []
    best, out = None, []
    for off, _ in votes.most_common(8):
        pairs = [(w, words[off + i]) for i, w in enumerate(heb) if 0 <= off + i < len(words)]
        same = sum(fold(w) == fold(t[3]) or skeleton(w) == skeleton(t[3]) for w, t in pairs)
        exact = sum(w.translate(FINALS) == t[3].translate(FINALS) for w, t in pairs)
        if best is None or (same, exact) > best[0]:
            best = ((same, exact), pairs)
    (same, exact), pairs = best
    if same < max(2, 0.6 * len(heb)) or exact == len(pairs):
        return []
    for w, (book, c, v, t) in pairs:
        if w.translate(FINALS) == t.translate(FINALS) or skeleton(w) == skeleton(t):
            continue
        kind = "alike" if fold(w) == fold(t) else "other"
        out.append({"kind": kind, "word": w, "bible": t, "verse": f"{book} {c}:{v}", "hebrew": row["hebrew"],
                    "chapter": row["chapter"], "page": row["page"], "part": row["part"],
                    "romanization": row["romanization"], "before": row["before"], "after": row["after"],
                    "scan_url": row["scan_url"]})
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:] == ["fetch"]:
        return fetch()
    if not list(TANAKH.glob("*.json")):
        sys.exit("no Bible text: run `uv run biblecheck.py fetch` first")
    words = load()
    index = {2: defaultdict(list), 3: defaultdict(list)}
    fw = [fold(w[3]) for w in words]
    for i in range(len(fw) - 1):
        index[2][tuple(fw[i:i + 2])].append(i)
        index[3][tuple(fw[i:i + 3])].append(i)
    only = set(sys.argv[1:])
    rows = [r for r in C.rows(require_en=False) if r["words"] >= 2 and (not only or r["chapter"] in only)]
    found = [x for r in rows for x in check(r, words, index)]
    found.sort(key=lambda x: (x["kind"] != "alike", x["page"]))
    if found:
        C.write(OUT if not only else OUT.with_name("bible_check_part.csv"), found)
    n = sum(x["kind"] == "alike" for x in found)
    print(f"{len(rows)} strings of two words or more; {n} words differ from the verse only by a look-alike "
          f"letter, {len(found) - n} in another way")
    for x in found:
        print(f'{x["kind"]} p. {x["page"]} {x["chapter"]}: {x["word"]} / Bible {x["bible"]} ({x["verse"]}) | {x["hebrew"]}')


if __name__ == "__main__":
    main()
