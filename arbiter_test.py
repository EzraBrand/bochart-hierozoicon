"""Test of an "arbiter": can a second model call, with more context than the judge has, give the verdict
of the scan check? (14-Nov-2026)

  uv run arbiter_test.py T5 T6 --effort medium          # groups whose names start with T5 or T6
  uv run arbiter_test.py T5 T6 --effort medium --report # the table again, without a model call

The answer key is the scan check itself: logs/review/{group}/decisions.tsv (1,228 verdicts in tranches
1-6). For each item the arbiter gets the same 2x line crop that the reader saw (logs/review/{group}/NNN.jpg),
the OCR text of the line, the readings of the four readers, and the lessons of AGENTS.md about this type.
It answers with what is printed. The test counts how often that is the reading the scan check chose
(judge / main / other), in total and for the answers it calls confident.

One Batch API call (half price); the crops are published with crophost.py. Answers are kept in
logs/arbiter_{tag}.jsonl, so a second run costs nothing. The crops of the groups A, B, C (tranche 4) were
written over on 14-Nov-2026 and cannot be used.
"""

import argparse
import csv
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent
REVIEW = ROOT / "logs" / "review"
PROMPT = """\
The image shows one printed line (with parts of the lines above and below) of Samuel Bochart, \
"Hierozoicon", Leipzig 1793-96: Latin (roman and italic, with the long s "ſ"), Greek in an old type with \
ligatures, unpointed square Hebrew, Arabic naskh, Syriac. Four OCR readers read the line; this is the text \
of the line as the first reader has it:

{line}

They disagree about one place. The readings:
- reader A: "{main}"
- reader B: "{flash}"
- reader C (a library OCR; it drops Syriac, and it has habits listed below): "{mdz}"
- reader D (looked at this crop): "{judge}"

Find that place in the image and write exactly what is PRINTED there, character by character, for the same \
stretch of text as reader A's reading covers. Do not correct the print: a misprint, an old spelling or an \
unusual form stays as printed. It may be that no reader is right.

What is known about this type and these readers:
- Latin: the long s is written "s"; "f" only with a full cross bar. "caussa" is often printed "causa": look.
- Greek: the ligature that looks like "8" or "ȣ" is ου (write ου with its accent); reader C writes ε or υ \
for it. The ligature "ϛ" is στ (write στ); a theta-like sign with a loop in front is σθ (write σθ). A \
lower-case φ can look like Φ. Reader C loses and misplaces accents; an accent difference counts only if you \
see the accent.
- Hebrew: ד/ר, ה/ח/ת, ו/ז/י/ן, ב/כ, ם/ס look alike in this type. Decide by the shape first; where the \
shape does not decide, use the Latin words and Bochart's romanization next to the word, and say that you \
are not confident.
- Arabic: a medial ف and a medial غ have the same shape; ذ is cup-shaped like ن; the lead-in stroke of ج/ح/خ \
is not an alif; dots are often faint. Do not add a dot that you do not see.
- A note mark is a small raised letter or number with ")" or in brackets; write it on the line.
- Keep the same convention for line-end hyphens and spaces as reader A.

Answer with a JSON object: "printed" (the text), "confident" (true only if the shapes in the image decide it).
"""
SCHEMA = {"type": "object", "properties": {"printed": {"type": "string"}, "confident": {"type": "boolean"}},
          "required": ["printed", "confident"], "additionalProperties": False}


def norm(s: str) -> str:
    return unicodedata.normalize("NFC", " ".join((s or "").split()))


def load(prefixes: list[str]) -> list[dict]:
    out = []
    for g in sorted(REVIEW.iterdir()):
        if not any(g.name.startswith(p) for p in prefixes) or not (g / "decisions.tsv").exists():
            continue
        items = {r["id"]: r for r in csv.DictReader((g / "items.tsv").open(encoding="utf-8"), delimiter="\t")}
        for d in csv.DictReader((g / "decisions.tsv").open(encoding="utf-8"), delimiter="\t"):
            r = items.get(d["id"])
            if r is None or r["page"] != d["page"] or not r["image"] or not (g / r["image"]).exists():
                continue
            v, t = d["verdict"].strip(), norm(d.get("text"))
            if v == "OK" or (v in ("APPLY", "OTHER") and t and t in (norm(r["judge"]), norm(r["new"]))):
                right, truth = "judge", norm(r["new"] or r["judge"])
            elif v in ("UNDO", "KEEP", "UNSURE"):
                right, truth = "main", norm(r["main"])
            elif v in ("APPLY", "OTHER") and t:
                right, truth = "other", t
            else:
                continue
            out.append({**r, "group": g.name, "cid": f"{g.name}_{int(r['id']):03d}", "right": right, "truth": truth,
                        "unsure": v == "UNSURE" or "?" in (d.get("note") or "")})
    return out


def run(items: list[dict], model: str, effort: str, out: Path) -> None:
    import crophost
    import orbatch
    done = {json.loads(l)["cid"] for l in out.read_text(encoding="utf-8").splitlines()} if out.exists() else set()
    todo = [it for it in items if it["cid"] not in done]
    if not todo:
        return
    crops = {f"arbiter/{out.stem}/{it['cid']}.jpg": (REVIEW / it["group"] / it["image"]).read_bytes() for it in todo}
    if not (ROOT / "logs" / f"batch_{out.stem}.json").exists():
        crophost.publish(crops)
    bodies = {}
    for it in todo:
        text = PROMPT.format(line=it["line"], main=it["main"], flash=it["flash"], mdz=it["mdz"], judge=it["judge"])
        bodies[it["cid"]] = {"max_tokens": 1200, "messages": [{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": crophost.RAW + f"arbiter/{out.stem}/{it['cid']}.jpg"}},
            {"type": "text", "text": text}]}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "answer", "strict": True, "schema": SCHEMA}},
            "reasoning": {"effort": effort}, "usage": {"include": True}}
    res = orbatch.run_batch(model, bodies, log_name=out.stem)
    with out.open("a", encoding="utf-8") as fh:
        for it in todo:
            d = res.get(it["cid"], {})
            try:
                text = d["choices"][0]["message"]["content"].strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1].rsplit("```", 1)[0]
                ans = json.loads(text)
            except Exception as e:
                print(f"{it['cid']}: FAILED {type(e).__name__}: {str(d)[:200]}", flush=True)
                continue
            fh.write(json.dumps({"cid": it["cid"], **ans}, ensure_ascii=False) + "\n")


def letters(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if c.isalnum())


def report(items: list[dict], out: Path) -> None:
    ans = {a["cid"]: a for a in map(json.loads, out.read_text(encoding="utf-8").splitlines())}
    rows = []
    for it in items:
        a = ans.get(it["cid"])
        if not a:
            continue
        p = norm(a["printed"])
        choice = "judge" if p == norm(it["new"] or it["judge"]) else "main" if p == norm(it["main"]) else "other"
        agree = p == it["truth"] or (choice == it["right"] and choice != "other")
        support = ("F" if norm(it["judge"]) == norm(it["flash"]) else "") + ("M" if norm(it["judge"]) == norm(it["mdz"]) else "")
        rows.append({**{k: it[k] for k in ("cid", "page", "kind", "main", "flash", "mdz", "judge", "right", "truth", "unsure")},
                     "support": support or "none", "arbiter": p, "confident": a["confident"], "choice": choice,
                     "agree": agree, "agree_letters": agree or letters(p) == letters(it["truth"])})
    with (ROOT / "logs" / f"{out.stem}.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    def line(name, rs):
        if not rs:
            return
        n, c = len(rs), [r for r in rs if r["confident"]]
        print(f"  {name:28} n={n:4}  agrees {100 * sum(r['agree'] for r in rs) / n:3.0f}%  (letters {100 * sum(r['agree_letters'] for r in rs) / n:3.0f}%)"
              f" | confident: {len(c):4} = {100 * len(c) / n:3.0f}%, of these agrees {100 * sum(r['agree'] for r in c) / max(len(c), 1):3.0f}%"
              f" (letters {100 * sum(r['agree_letters'] for r in c) / max(len(c), 1):3.0f}%)")
    print(f"{len(rows)} items with an answer; 'agrees' = the arbiter wrote the reading that the scan check chose\n")
    line("all", rows)
    line("without the UNSURE items", [r for r in rows if not r["unsure"]])
    for key in ("kind", "support", "right"):
        print(key)
        by = defaultdict(list)
        for r in rows:
            by[r[key]].append(r)
        for k, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
            line(k, rs)
    print("baseline: the vote as it is (change applied, review item not applied)")
    base = sum((r["kind"] == "change") == (r["right"] == "judge") for r in rows)
    print(f"  right in {100 * base / len(rows):.0f}% of the items")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("groups", nargs="+")
    p.add_argument("--model", default="anthropic/claude-opus-5.5")
    p.add_argument("--effort", default="medium")
    p.add_argument("--report", action="store_true")
    a = p.parse_args()
    items = load(a.groups)
    out = ROOT / "logs" / f"arbiter_{'-'.join(a.groups)}_{a.model.split('/')[-1].replace('.', '-')}_{a.effort}.jsonl"
    print(f"{len(items)} items in {sorted({it['group'] for it in items})}", flush=True)
    if not a.report:
        run(items, a.model, a.effort, out)
    report(items, out)


if __name__ == "__main__":
    main()
