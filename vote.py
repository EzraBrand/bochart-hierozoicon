"""Vote on the flags of check.py and write the corrected main OCR as an engine of its own.

  uv run vote.py 408 429      # reads data/fix/v2-408-429.judge.jsonl; writes data/fix/v2-408-429.decisions.json,
                              # logs/vote_v2-408-429.csv and data/ocr/or-claude-opus-5.5@low+vote/

Ported from lewysohn-zoologie's hebvote.py. The voters are the two second readers (Flash, MDZ)
and the image judge. Rule: the main OCR is changed only where the image judge read the same as
Flash or as MDZ (2 of 3 against the main OCR, and the judge always one of the two). Flash and MDZ
alone never change it: on the gold pages both read Δίπες and "Patrae" where Opus was right.
A judge reading that matches no engine is "review" (listed, not applied). A change of a whole
different word (not a letter or two) is "review" too (an alignment error of check.py).
The new text is the reading of the engine the judge agreed with (Flash's text if both agree: MDZ's
has the long s as f). Writes the changed pages into data/ocr/{main}+vote/ (all pages, changed or
not), so eval.py and qa.py can score the voted text like any engine.
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

import eval as ev
from check import PUNCT, key

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
DATA = ROOT / "data"


def similar(old: str, new: str) -> bool:
    o, n = old.split(), new.split()
    if len(o) != len(n):
        return False
    return all(Levenshtein.distance(key(a), key(b)) <= max(2, len(key(a)) // 3) for a, b in zip(o, n))


# Changes of the vote that are wrong, each read on the scan (01-Nov-2026). Nearly all had only MDZ
# with the judge: an MDZ-only change needs a look (pilot: about 6 right, 9 wrong).
REJECT = {
    ("v2-0410", "טפז"): "print טפז (5x; Bochart: taphza)",
    ("v2-0412", "טווזא"): "print not clear (Bochart: tauza); judge read ז as ו before",
    ("v2-0414", "שפן"): "print שפן",
    ("v2-0414", "et-"): "print et- (a broken t)",
    ("v2-0415", "תרדמה"): "print תרדמה (Gen 2:21)",
    ("v2-0415", "האדם"): "print האדם",
    ("v2-0418", "riae"): "catchword 'rias' read into the body text: for the page join",
    ("v2-0421", "commune"): "print commune",
    ("v2-0425", "plerumque"): "print plerumque",
    ("v2-0429", "עכלבר"): "print עכלבר (achalbar); the line has both עכבר and עכלבר",
    ("v2-0411", "κένικλον."): "print κένικλον",
    ("v2-0411", "κένικλος,"): "print κένικλος (as κένικλον two lines before)",
}

# Differences that the scan cannot decide or that are conventions, not readings: never changed by the
# vote, listed for review. Each was seen in the pilot (01-Nov-2026).
SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


def ambiguous(old: str, new: str) -> str:
    o, n = key(old), key(new)
    if o.translate(SUPERSCRIPTS) == n.translate(SUPERSCRIPTS):
        return "note-mark format"
    if len(o) == len(n) and all(a == b or {a, b} == {"ف", "غ"} for a, b in zip(o, n)):
        return "ف/غ: the same shape in this type (medial)"
    if re.sub("ου", "ε", o) == n or re.sub("ού", "έ", o) == n or o.replace("ου", "υ") == n:
        return "ȣ ligature (ου) read as ε or υ"
    if o.replace("στ", "ς") == n:
        return "στ ligature written ς"
    if len(n) < len(o) and n in o and len(o) - len(n) >= 2:
        return "shorter reading (the judge read a part)"
    return ""


def by_word(it: dict) -> list[dict]:
    """A flag of several words is voted word by word when the judge read as many words as the main
    OCR; a reader with another word count has no vote on those words."""
    m, j = it["main"].split(), (it["printed"] or "").split()
    if len(m) < 2 or len(j) != len(m):
        return [it]
    out = []
    for i, w in enumerate(m):
        sub = {**it, "main": w, "printed": j[i]}
        for n in ("flash", "mdz"):
            r = it[n].split()
            sub[n] = r[i] if len(r) == len(m) else ""
        out.append(sub)
    return out


def apply(blocks: list[dict], line: str, old: str, new: str) -> bool:
    """Replace old by new in the block line most like `line` (an earlier change may have touched it)."""
    ev.LOOSE = True
    if not any(old in b["text"] for b in blocks):  # "<i>alphenec</i>,": try the word without its punctuation
        old, new = PUNCT.sub("", old), PUNCT.sub("", new)
    cands = [(fuzz.ratio(ev.norm(raw), line), bi, i) for bi, b in enumerate(blocks)
             for i, raw in enumerate(b["text"].split("\n")) if old in raw]
    if not cands or max(cands)[0] < 90:
        return False
    _, bi, i = max(cands)
    b = blocks[bi]
    lines = b["text"].split("\n")
    lines[i] = lines[i].replace(old, new, 1)
    b["text"] = "\n".join(lines)
    b["runs"] = [{"lang": b.get("lang", "other"), "text": b["text"]}]  # runs no longer split by language
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("first", type=int)
    p.add_argument("last", type=int)
    p.add_argument("--vol", type=int, default=2)
    p.add_argument("--main", default="or-claude-opus-5.5@low")
    p.add_argument("--judge", default="", help="judge tag: reads data/fix/{range}.judge.{tag}.jsonl (judge_page.py)")
    p.add_argument("--skip-mdz-only", action="store_true", help="ignore flags where only MDZ differs from the main OCR")
    a = p.parse_args()
    rng = f"v{a.vol}-{a.first}-{a.last}"
    sfx = (f".{a.judge}" if a.judge else "") + (".nomdz" if a.skip_mdz_only else "")
    recs = [json.loads(x) for x in (DATA / "fix" / f"{rng}.judge{'.' + a.judge if a.judge else ''}.jsonl")
            .read_text(encoding="utf-8").splitlines()]
    if a.skip_mdz_only:
        for rec in recs:
            rec["items"] = [it for it in rec["items"] if it["flash"] and it["flash"] != it["main"]]
    rows, decisions, tally = [], [], Counter()
    for rec in recs:
        for it in (w for item in rec["items"] for w in by_word(item)):
            pr = it["printed"] or ""
            k = key(pr)
            agree = [n for n in ("flash", "mdz") if it[n] and " ".join(key(w, n == "mdz") for w in it[n].split())
                     == " ".join(key(w, n == "mdz") for w in pr.split())]
            if " ".join(key(w) for w in pr.split()) == " ".join(key(w) for w in it["main"].split()):
                outcome, new = "keep", ""
            elif agree:
                new = it["flash"] if "flash" in agree else pr
                new = re.sub(r'(?<=[א-ת])"(?=[א-ת])', "״", new)  # Flash writes " for ״
                new = new.replace("ſ", "s")
                amb = ambiguous(it["main"], new)
                outcome = (f"rejected ({REJECT[rec['page'], it['main']]})" if (rec["page"], it["main"]) in REJECT
                           else f"review ({amb})" if amb else
                           "change" if similar(it["main"], new) else "review (not similar)")
            else:
                outcome, new = ("review (judge read another text)" if k else "no answer"), ""
            tally[outcome] += 1
            if outcome == "change":
                decisions.append({"page": rec["page"], "line": rec["line"], "old": it["main"], "new": new,
                                  "script": it["script"], "agree": agree})
            rows.append({"page": rec["page"], "script": it["script"], "main": it["main"], "flash": it["flash"],
                         "mdz": it["mdz"], "judge": pr, "confident": it["confident"], "outcome": outcome,
                         "new": new, "line": rec["line"]})
    (DATA / "fix" / f"{rng}.decisions{sfx}.json").write_text(json.dumps(
        {"rule": "change where the image judge reads the same as Flash or MDZ, against the main OCR",
         "items": decisions}, ensure_ascii=False, indent=1), encoding="utf-8")
    out = ROOT / "logs" / f"vote_{rng}{sfx}.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    # the voted OCR as an engine of its own
    src, dst = DATA / "ocr" / a.main, DATA / "ocr" / f"{a.main}+vote{sfx.replace('.', '-')}"
    dst.mkdir(parents=True, exist_ok=True)
    failed = 0
    by_page = {}
    for d in decisions:
        by_page.setdefault(d["page"], []).append(d)
    for f in sorted(src.glob(f"v{a.vol}-*.json")):
        res = json.loads(f.read_text(encoding="utf-8"))
        for d in by_page.get(f.stem, []):
            if not apply(res["blocks"], d["line"], d["old"], d["new"]):
                failed += 1
                print(f"  {f.stem}: not applied (tags inside the span?): {d['old']} -> {d['new']}")
        res["meta"] = {**res.get("meta", {}), "vote": f"{len(by_page.get(f.stem, []))} decisions from {rng}"}
        (dst / f.name).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(rows)} flags: {dict(tally)}; {len(decisions)} changes ({failed} not applied); "
          f"wrote {out} and {dst}")


if __name__ == "__main__":
    main()
