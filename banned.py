"""Banned-words check of the English against the chapter's fixed terms (11-Nov-2026). No model call.

  uv run banned.py                 # every chapter with an en.json
  uv run banned.py deror agur      # these chapters

A chapter that argues about the identity of a bird keeps the Hebrew name (deror, sis, agur, kore) and
uses the English bird name only where the Latin has the Latin or Greek bird name. For each paragraph
the English word is counted against its sources in the Latin paragraph (same index in en.json and
la.json); a paragraph with more English words than sources is listed, for a look. "pigeon" alone
(not "wood pigeon") is never right. Report only: nothing is rewritten.
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ENTRIES = Path(__file__).resolve().parent / "data" / "entries"

# english regex -> regex of the Latin/Greek words that justify it ("" = never right)
PIGEON = (r"(?<!wood )(?<!wood-)\bpigeons?\b", "")
WOOD_PIGEON = (r"\bwood[ -]pigeons?\b", r"palumb|φάττ|φάσσ|φάψ|φαβ")
SWALLOW = (r"\bswallows?\b", r"hirund|χελιδ[όώοω]|χελιδ|סנונית|سنون|خطاف|progne|procne")
CRANE = (r"\bcranes?\b", r"\bgru[semi]|\bgrus\b|γεραν|γέραν|كركي|غرنوق|כורכי")
PARTRIDGE = (r"\bpartridges?\b", r"perdi[xc]|πέρδι|περδί|περδικ|حجل|قبج|כרא|cara\b")
SPARROW = (r"\bsparrows?\b", r"passer|στρουθ|عصفور|צפור")
RULES = {
    "shafan": [(r"\bcone(y|ys|ies)\b|\bhyrax(es)?\b|\brock badgers?\b", r"hyra[xc]|ὕραξ")],
    "choled": [(r"\bweasels?\b", r"mustel|γαλ[ῆέῇ]|γαλῆ|חולדה|belette")],
    "kippod": [(r"\bhedgehogs?\b", r"eric|erinac|heric|ἐχῖν|ἐχίν|echin|قنفذ|herisson")],
    "deror": [PIGEON, WOOD_PIGEON, SWALLOW, SPARROW],
    "turtur": [PIGEON, WOOD_PIGEON],
    "sis": [PIGEON, SWALLOW, CRANE],
    "agur": [PIGEON, CRANE, SWALLOW],
    "kore": [PIGEON, PARTRIDGE],
    "perdix-cavea": [PIGEON, (r"\bdecoys?\b", r"illic|illex|allect|παλευ")],
}
# tranche 4: barburim stays barburim (the English must not decide the bird)
RULES["barburim"] = [PIGEON, (r"\bswans?\b", r"cygn|olor|κύκν"), (r"\bgeese\b|\bgoose\b", r"anser|χ[ήη]ν")]
for e in ("selav", "selav-quaestiones", "gallinaceum", "galli-cantus", "gallina-pulli", "tukkiyim"):
    RULES[e] = [PIGEON, (r"\broosters?\b", "")]
for e in ("jonah", "columba-pennae", "columbaria", "columba-mores", "columba-sacrificia", "columba-noachi",
          "chiryonim"):
    RULES[e] = [PIGEON, WOOD_PIGEON]


def plain(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


def check(entry: str) -> int:
    d = ENTRIES / entry
    if not (d / "en.json").exists():
        print(f"{entry}: no en.json")
        return 0
    en, la = (json.loads((d / f"{x}.json").read_text(encoding="utf-8")) for x in ("en", "la"))
    found = 0
    for part in ("main", "notes"):
        if len(en[part]) != len(la[part]):
            print(f"{entry}: {part} has {len(en[part])} English and {len(la[part])} Latin blocks: not compared")
            continue
        for i, (be, bl) in enumerate(zip(en[part], la[part])):
            te, tl = plain(be["text"]), plain(bl["text"])
            for en_re, la_re in RULES.get(entry, []):
                hits = re.findall(en_re, te, re.I)
                n_la = len(re.findall(la_re, tl, re.I)) if la_re else 0
                if len(hits) > n_la:
                    found += 1
                    m = re.search(en_re, te, re.I)
                    ctx = te[max(m.start() - 70, 0):m.end() + 50].replace("\n", " ")
                    print(f"{entry} {part}[{i}] p. {be.get('page', '?')}: {len(hits)} x {m.group(0)!r}, "
                          f"{n_la} source word(s) in the Latin | …{ctx}…")
    return found


def main():
    entries = sys.argv[1:] or sorted(p.name for p in ENTRIES.iterdir() if p.name in RULES)
    total = sum(check(e) for e in entries)
    print(f"{total} paragraph(s) to look at in {len(entries)} chapter(s)")


if __name__ == "__main__":
    main()
