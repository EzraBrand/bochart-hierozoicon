"""Translation spot-check: a second model reads the English against the Latin and lists what does not
match (13-Nov-2026; from the ideas backlog of AGENTS.md). Report only: nothing is rewritten.

  uv run spotcheck.py tsippor aquila --tag t5          # writes logs/spotcheck_t5.tsv
  uv run spotcheck.py tsippor --model openai/gpt-6.1-sol

Why: in tranche 4 three wrong words showed only in the English (a Hebrew ח read for ת, a Syriac word,
"Hist. Nat." expanded as Buffon). The reader is another model family than the translator (Gemini Flash
by default, synchronous, 4 workers; a chapter costs a few cents). The answers are cached per chunk in
data/entries/{chapter}/spotcheck/, so a second run is free. Each row is a thing to look at, not a
verdict: the checker is wrong often (it "corrects" the print as the other models do).
"""

import argparse
import csv
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CHARS = 6000
VERSION = "v1"

PROMPT = """\
Below are numbered pairs from Samuel Bochart, Hierozoicon (1663; Latin, with quotations in Greek, \
Hebrew, Aramaic, Syriac and Arabic): the transcribed source ("la") and its English translation ("en"). \
The transcription is OCR and can have a wrong letter in a quoted word.

List only clear, checkable problems:
1. omission: a clause, a negation, a hedge (fere, forte, ut videtur), a number or a reference of the \
source is missing in the English, or the English has one that the source does not have;
2. meaning: a word or phrase is translated with a clearly wrong sense, or a name or an abbreviated \
author/title is expanded to the wrong person or work;
3. quote: a quoted Greek/Hebrew/Aramaic/Syriac/Arabic word does not fit Bochart's own Latin rendering \
or romanization next to it (a sign of an OCR error in the quoted word), or the English renders it \
differently from Bochart's Latin.

Do not list: style, word order, modern Bible reference forms (Gen 1:2 for Gen. I, 2), bracketed \
additions in the English that identify a person or expand an abbreviation (unless wrong), kept Latin \
or romanized Hebrew terms, old spellings in the source. If a pair is fine, list nothing for it. Most \
pairs are fine.

Return JSON: {{"issues": [{{"n": pair number, "kind": "omission" | "meaning" | "quote", \
"la": "the source words (short)", "en": "the English words (short)", "problem": "one sentence"}}]}}

{pairs}"""

SCHEMA = {"type": "object", "properties": {"issues": {"type": "array", "items": {
    "type": "object",
    "properties": {"n": {"type": "integer"}, "kind": {"type": "string"}, "la": {"type": "string"},
                   "en": {"type": "string"}, "problem": {"type": "string"}},
    "required": ["n", "kind", "la", "en", "problem"], "additionalProperties": False}}},
    "required": ["issues"], "additionalProperties": False}


def key() -> str:
    import orbatch
    return orbatch.KEY_FILE.read_text(encoding="utf-8").strip()


def pairs_of(entry: str) -> list[dict]:
    d = DATA / "entries" / entry
    la, en = (json.loads((d / f"{x}.json").read_text(encoding="utf-8")) for x in ("la", "en"))
    out = []
    for part in ("main", "notes"):
        if len(la[part]) != len(en[part]):
            print(f"{entry}: {part} has {len(la[part])} Latin and {len(en[part])} English blocks: skipped", flush=True)
            continue
        out += [{"part": part, "i": i, "page": a.get("page", ""), "la": a["text"], "en": b["text"]}
                for i, (a, b) in enumerate(zip(la[part], en[part]))]
    return out


def chunks(pairs: list[dict]) -> list[list[dict]]:
    out, cur, n = [], [], 0
    for p in pairs:
        if cur and n + len(p["la"]) > CHARS:
            out.append(cur)
            cur, n = [], 0
        cur.append(p)
        n += len(p["la"])
    return out + ([cur] if cur else [])


def ask(model: str, chunk: list[dict]) -> dict:
    body = json.dumps([{"n": k, "la": p["la"], "en": p["en"]} for k, p in enumerate(chunk, 1)],
                      ensure_ascii=False, indent=1)
    for attempt in range(3):
        r = requests.post("https://openrouter.ai/api/v1/chat/completions",
                          headers={"Authorization": "Bearer " + key()}, timeout=600,
                          json={"model": model, "max_tokens": 6000, "reasoning": {"effort": "low"},
                                "messages": [{"role": "user", "content": PROMPT.format(pairs=body)}],
                                "response_format": {"type": "json_schema", "json_schema": {
                                    "name": "issues", "strict": True, "schema": SCHEMA}},
                                "usage": {"include": True}})
        try:
            d = r.json()
            out = d["choices"][0]["message"]["content"].strip()
            if out.startswith("```"):
                out = out.split("\n", 1)[1].rsplit("```", 1)[0]
            return {"issues": json.loads(out)["issues"], "cost": (d.get("usage") or {}).get("cost", 0)}
        except Exception as e:  # a cut or empty answer: once more
            err = f"{type(e).__name__}: {str(e)[:120]}"
            time.sleep(5 * (attempt + 1))
    return {"issues": [], "cost": 0, "error": err}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("entries", nargs="+")
    p.add_argument("--tag", default="")
    p.add_argument("--model", default="google/gemini-3.8-flash")
    p.add_argument("--workers", type=int, default=4)
    a = p.parse_args()
    jobs = []
    for e in a.entries:
        for n, ch in enumerate(chunks(pairs_of(e)), 1):
            h = hashlib.sha1(json.dumps([VERSION, a.model, [(x["la"], x["en"]) for x in ch]],
                                        ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
            jobs.append((e, n, ch, DATA / "entries" / e / "spotcheck" / f"{n:03d}-{h}.json"))
    todo = [j for j in jobs if not j[3].exists()]
    print(f"{len(jobs)} chunks, {len(todo)} to ask ({a.model})", flush=True)
    cost, done = 0.0, 0

    def work(job):
        e, n, ch, cache = job
        res = ask(a.model, ch)
        if "error" not in res:
            cache.parent.mkdir(exist_ok=True)
            cache.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
        return job, res

    with ThreadPoolExecutor(a.workers) as ex:
        for (e, n, ch, cache), res in ex.map(work, todo):
            done += 1
            cost += res.get("cost") or 0
            print(f"{done}/{len(todo)} {e} chunk {n}: {len(res['issues'])} issues"
                  + (f" FAILED {res['error']}" if "error" in res else ""), flush=True)
    rows = []
    for e, n, ch, cache in jobs:
        if not cache.exists():
            continue
        for it in json.loads(cache.read_text(encoding="utf-8"))["issues"]:
            if not 1 <= it["n"] <= len(ch):
                continue
            src = ch[it["n"] - 1]
            rows.append({"entry": e, "page": src["page"], "part": src["part"], "block": src["i"],
                         "kind": it["kind"], "la": it["la"], "en": it["en"], "problem": it["problem"]})
    out = ROOT / "logs" / f"spotcheck{'_' + a.tag if a.tag else ''}.tsv"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["entry", "page", "part", "block", "kind", "la", "en", "problem"], delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    missing = sum(1 for j in jobs if not j[3].exists())
    print(f"{len(rows)} issues in {len(jobs) - missing} of {len(jobs)} chunks; cost ${cost:.2f}; wrote {out}"
          + (f"; {missing} chunk(s) FAILED: run again" if missing else ""), flush=True)


if __name__ == "__main__":
    main()
