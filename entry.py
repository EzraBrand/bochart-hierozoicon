"""Join the pages of one chapter into continuous text and translate it as a whole.

  uv run entry.py shafan --no-translate     # the joined Latin text: data/entries/shafan/la.json, la.md
  uv run entry.py shafan                    # and the English (translate.py), chunk by chunk, resumable
  uv run entry.py shafan --finish-only      # redo the fixed steps after translation (no model call)

Ported from lewysohn-zoologie. Per page the source is the gold text if it exists, else the voted
OCR (vote.py). Furniture (running heads, signatures, catchwords) is dropped. A paragraph that runs
over a page break is joined, and "[II, 410]" marks where p. 410 of vol. 2 begins. The margin
column numbers of 1663 (⟦p. 1001⟧) become "[col. 1001]". Notes (Bochart's a), b) ...; Rosenmüller's
(1), (2) ...) are kept when their mark is in the chapter's own text on that page; a note without a
mark at the top of a page continues the last note of the page before.
"""

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DATA = Path(__file__).parent / "data"
SOURCE = "or-claude-opus-5.5@low+vote"
CHUNK_CHARS = 5000

# start / end: regexes for the first block of the chapter and the first block after it.
# Page joins checked by eye on the scans (logs/qa_v2-408-429.csv), 01-Nov-2026.
ENTRIES = {
    "shafan": {"vol": 2, "pages": list(range(409, 430)),
               "title": "Book 3, chapter 33: Saphan is not the rabbit but a kind of larger mouse (vol. 2, pp. 409–429)",
               "start": r"^CAP\.\s*XXXIII\.", "end": r"^CAP\.\s*XXXIV\.",
               "first_col": 1001},  # the mark p. 1001 stands in the last lines of ch. 32
    # 08-Nov-2026, the first chapter run with the Batch API (COST_TEST.md); the mark p. 1021 stands in
    # the heading line; ch. 36 begins at the top of p. 454
    "choled": {"vol": 2, "pages": list(range(435, 455)),
               "title": "Book 3, chapter 35: Choled is not the weasel but the mole; other names of the mole (vol. 2, pp. 435–453)",
               "start": r"^CAP\.\s*XXXV\.", "end": r"^CAP\.\s*XXXVI\.",
               "about": "the chapter arguing that the Hebrew חלד (choled) is not the weasel but the mole, "
                        "with the other names of the mole",
               "terms": '"mustela" -> "weasel"; "talpa" -> "mole"; "choled" stays "choled" (never "weasel" '
                        'or "mole": the identity of the animal is what the chapter argues about);'},
}
SENTENCE_END = re.compile(r"[.!?:;)\]]\s*$")
# Corrections to the voted OCR of pages without gold text, each checked on the scan.
# Catchwords read into the body text (the next page begins with the same word); applied to the
# gold text too (p. 410).
FIXES = {
    410: [("מעלה\nגרה,", "מעלה")],
    # Ethiopic and Samaritan, read by Claude at 4-6x (02-Nov-2026; not by a reader of these scripts):
    # ለጊሔ፡ fits Bochart's "legiche"; the Samaritan, Bochart's "taphsa", read ט פ ס ה (the ה not sure)
    412: [("ሰጊሔ፡", "ለጊሔ፡"), ("<i>Samaritano</i> [?] <i>taphsa", "<i>Samaritano</i> ࠈࠐࠎࠄ <i>taphsa")],
    414: [("con-\nstanter", "con-")],
    # the catchword "rias" (printer's error for "riae", p. 419's first word)
    # ኮሮገሬሊወን፡ (choerogryllion): seven signs before the colon, Opus had six; 3rd and 4th not sure
    418: [("<i>Histo-\nriae</i> ⟦p. 1009⟧", "<i>Histo-</i> ⟦p. 1009⟧"), ("ኮርገሊሎን፡", "ኮሮገሬሊወን፡")],
    421: [("يناقده\nاليه", "يناقده")],
    # ch. 35 (08-Nov-2026): catchwords read into the body text
    439: [("caeci de-\ngunt</i>,", "caeci de-</i>")],
    440: [("meta-\nphoram-", "meta-")],
}
# the same foreign-script corrections, for an English translation made before them (translate.finish)
SCRIPT_SYNC = [("ሰጊሔ፡", "ለጊሔ፡"), ("ኮርገሊሎን፡", "ኮሮገሬሊወን፡"), ("[?] <i>taphsa", "ࠈࠐࠎࠄ <i>taphsa")]
NOTE_MARK = re.compile(r"\^\{(\(\d+\)|[a-z]\))\}")
MARGIN = re.compile(r"⟦p\. (\d+)⟧")
FOOTNOTE = re.compile(r"^(\(\d+\)|[a-z]\))\s")


def page_key(vol: int, page: int) -> str:
    return f"v{vol}-{page:04d}"


def gold_blocks(path: Path, ocr: dict) -> list[dict]:
    """Gold text -> blocks; block types from the OCR page (the gold pages keep its block count)."""
    texts = [t.strip("\n") for t in path.read_text(encoding="utf-8").split("\n\n") if t.strip()]
    if len(texts) != len(ocr["blocks"]):
        sys.exit(f"{path.name}: {len(texts)} gold blocks, {len(ocr['blocks'])} OCR blocks")
    out = []
    for t, b in zip(texts, ocr["blocks"]):
        m = FOOTNOTE.match(t) if b["type"] == "footnote" else None
        out.append({"type": b["type"], "marker": m.group(1) if m else "", "text": t[m.end():] if m else t})
    return out


def page_blocks(vol: int, page: int) -> list[dict]:
    key = page_key(vol, page)
    ocr = json.loads((DATA / "ocr" / SOURCE / f"{key}.json").read_text(encoding="utf-8"))
    gold = DATA / "gold" / f"{key}.txt"
    blocks = gold_blocks(gold, ocr) if gold.exists() else ocr["blocks"]
    for old, new in FIXES.get(page, []):
        hits = [b for b in blocks if old in b["text"]]
        if len(hits) != 1:
            sys.exit(f"p. {page}: correction {old!r} found {len(hits)} times, not once")
        hits[0]["text"] = hits[0]["text"].replace(old, new)
    for b in blocks:
        b["text"] = re.sub(r"\^\{([a-z])\}\)", r"^{\1)}", b["text"])  # p. 419: ^{a}) for ^{a)}
        b["text"] = MARGIN.sub(r"[col. \1]", b["text"])
    return blocks


def build(cfg: dict) -> tuple[list[dict], list[dict]]:
    """-> (main blocks, note blocks); each block has a "page"."""
    vol = cfg["vol"]
    main, notes, started, ended = [], [], False, False
    page_text, other_text = {}, {}
    for page in cfg["pages"]:
        first_on_page = True
        for b in page_blocks(vol, page):
            text = b["text"].strip()
            if b["type"] == "furniture":
                continue
            if b["type"] == "footnote":
                notes.append({"type": "footnote", "marker": b.get("marker", ""), "text": text, "page": page})
                continue
            if not started:
                if not re.search(cfg["start"], text):
                    other_text[page] = other_text.get(page, "") + "\n" + text
                    continue
                started = True
            elif re.search(cfg["end"], text):
                ended = True
            if ended:
                other_text[page] = other_text.get(page, "") + "\n" + text
                continue
            page_text[page] = page_text.get(page, "") + "\n" + text
            prev = main[-1] if main else None
            prev_end = re.sub(r"(?:\s*\[col\. \d+\])+$", "", prev["text"]) if prev else ""
            continues = (page in cfg.get("continue", []) or not SENTENCE_END.search(prev_end)) \
                and page not in cfg.get("break", [])
            mark = f"[{'I' * vol}, {page}]"
            if first_on_page and prev and prev["type"] == "body" and b["type"] == "body" and continues:
                # a word broken over the page ("Histo-</i> [col. 1009]" | "<i>riae"): the marks after the word
                hy = re.search(r"-((?:</i>)?)((?:\s*\[col\. \d+\])*)$", prev["text"])
                if hy:
                    word, _, rest = text.partition(" ")
                    prev["text"] = f"{prev['text'][:hy.start()]}{hy.group(1)}{word}{hy.group(2)} {mark} {rest}"
                else:
                    prev["text"] += f" {mark} {text}"
            else:
                lead = f"{mark} " if first_on_page and main else ""
                if not main:  # the chapter's first block: its page and the column it starts in
                    lead = f"{mark} " + (f"[col. {cfg['first_col']}] " if cfg.get("first_col") else "")
                main.append({"type": b["type"], "marker": "", "text": lead + text, "page": page})
            first_on_page = False
        if ended:
            break
    if not started:
        sys.exit(f"start pattern {cfg['start']!r} not found")
    kept, seen = [], {}
    for n in notes:
        mark = f"^{{{n['marker']}}}" if n["marker"] else ""
        if mark and mark in page_text.get(n["page"], ""):
            seen[n["page"]] = True
            kept.append(n)
        elif mark and mark in other_text.get(n["page"], ""):
            continue  # a note of the chapter before or after, on a shared page
        elif not n["marker"] and kept and not seen.get(n["page"]) and kept[-1]["page"] != n["page"]:
            prev = kept[-1]  # a note continued from the page before ("signi-|ficet")
            mark = f"[{'I' * vol}, {n['page']}]"
            if prev["text"].endswith("-"):
                word, _, rest = n["text"].partition(" ")
                prev["text"] = f"{prev['text'][:-1]}{word} {mark} {rest}"
            else:
                prev["text"] += f" {mark} {n['text']}"
            print(f"note on p. {n['page']} (no mark) joined to {prev['marker']} of p. {prev['page']}")
        else:
            print(f"note on p. {n['page']} {n['marker'] or '(no mark)'} left out: mark not in the chapter's text")
    return main, kept


def chunks(blocks: list[dict]) -> list[list[dict]]:
    out, cur = [], []
    for b in blocks:
        if cur and sum(len(x["text"]) for x in cur) + len(b["text"]) > CHUNK_CHARS:
            out.append(cur)
            cur = []
        cur.append(b)
    return out + [cur] if cur else out


LRM = "‎"  # keeps a paragraph that starts with Hebrew or Arabic left-to-right on GitHub


def md_inline(text: str) -> str:
    return re.sub(r"_\{(.+?)\}", r"<sub>\1</sub>", re.sub(r"\^\{(.+?)\}", r"<sup>\1</sup>", text))


def render(title: str, main: list[dict], notes: list[dict]) -> str:
    out = [f"# {title}", ""]
    for b in main:
        text = LRM + md_inline(b["text"]).replace("\n", " ")
        out += [f"### {text}" if b["type"] == "heading" else text, ""]
    if notes:
        out += ["---", "", "**Notes**", ""]
        for n in notes:
            label = n.get("label") or n["marker"]
            out += [f"{LRM}{label} *(p. {n['page']})* {md_inline(n['text']).replace(chr(10), ' ')}", ""]
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("entry", choices=ENTRIES)
    p.add_argument("--model", default="anthropic/claude-opus-5.5")
    p.add_argument("--effort", default="medium")
    p.add_argument("--no-translate", action="store_true")
    p.add_argument("--batch", action="store_true", help="translate through the OpenRouter Batch API (half price)")
    p.add_argument("--finish-only", action="store_true", help="redo the fixed steps from en.raw.json")
    a = p.parse_args()
    cfg = ENTRIES[a.entry]
    out = DATA / "entries" / a.entry
    out.mkdir(parents=True, exist_ok=True)
    if a.finish_only:
        import translate as T
        T.finish(cfg, out)
        return
    main_blocks, notes = build(cfg)
    (out / "la.json").write_text(json.dumps({"main": main_blocks, "notes": notes}, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
    (out / "la.md").write_text(render(cfg["title"], main_blocks, notes), encoding="utf-8")
    print(f"{len(main_blocks)} paragraphs, {len(notes)} notes, "
          f"{sum(len(b['text']) for b in main_blocks)} characters of main text")
    if a.no_translate:
        return
    import translate as T  # here, so that --no-translate needs no model code
    if cfg.get("about"):
        T.CHAPTER = {"about": cfg["about"], "terms": cfg.get("terms", "")}
    en_main, en_notes, cost = [], [], 0.0
    if a.batch:  # all chunks not cached yet in one OpenRouter batch (half price); then the loop reads the cache
        import orbatch
        bodies, todo = {}, {}
        for kind, blocks in (("text", main_blocks), ("notes", notes)):
            for i, ch in enumerate(chunks(blocks), 1):
                src_key = hashlib.sha1(json.dumps([T.RULES_VERSION, a.model, a.effort, ch], ensure_ascii=False)
                                       .encode("utf-8")).hexdigest()[:16]
                cache = out / "chunks" / f"{kind}-{i:03d}-{src_key}.json"
                if not cache.exists():
                    bodies[f"{kind}-{i:03d}"] = T.request_body(ch, a.effort, notes=kind == "notes")
                    todo[f"{kind}-{i:03d}"] = (ch, cache)
        if bodies:
            t = time.monotonic()
            res = orbatch.run_batch(a.model, bodies, log_name=f"translate_{a.entry}_{a.effort}_{len(bodies)}")
            for cid, (ch, cache) in todo.items():
                try:
                    r = T.parse(res.get(cid, {"error": "no result"}), len(ch), a.model, a.effort, time.monotonic() - t)
                except Exception as e:
                    print(f"{cid}: FAILED {type(e).__name__}: {e} (the sync loop below retries it)", flush=True)
                    continue
                cache.parent.mkdir(exist_ok=True)
                cache.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
    for kind, blocks, target in (("text", main_blocks, en_main), ("notes", notes, en_notes)):
        for i, ch in enumerate(chunks(blocks), 1):
            # each chunk is saved when done, keyed by its source and the rules: a stopped run resumes
            src_key = hashlib.sha1(json.dumps([T.RULES_VERSION, a.model, a.effort, ch], ensure_ascii=False)
                                   .encode("utf-8")).hexdigest()[:16]
            cache = out / "chunks" / f"{kind}-{i:03d}-{src_key}.json"
            if cache.exists():
                res = json.loads(cache.read_text(encoding="utf-8"))
                print(f"{kind} chunk {i}: done already", flush=True)
            else:
                for attempt in range(3):
                    try:
                        res = T.translate(ch, a.model, a.effort, notes=kind == "notes")
                        break
                    except Exception as e:
                        print(f"{kind} chunk {i}: attempt {attempt + 1} FAILED {type(e).__name__}: {e}", flush=True)
                        if attempt == 2 or "credit" in str(e).lower() or "402" in str(e):
                            sys.exit(f"stopped at {kind} chunk {i}; the chunks done so far are saved")
                        time.sleep(20 * (attempt + 1))
                cache.parent.mkdir(exist_ok=True)
                cache.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
                cost += res["meta"]["cost_usd"]
                print(f"{kind} chunk {i}: {len(ch)} blocks, {res['meta']['seconds']} s, "
                      f"${res['meta']['cost_usd']:.4f}", flush=True)
            for src, b in zip(ch, res["blocks"]):
                target.append({**b, "page": src["page"]})
    meta = {"model": a.model, "effort": a.effort, "rules": T.RULES_VERSION, "cost_usd": round(cost, 4)}
    (out / "en.raw.json").write_text(json.dumps({"main": en_main, "notes": en_notes, "meta": meta},
                                                ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"translation cost ${cost:.4f}")
    T.finish(cfg, out)


if __name__ == "__main__":
    main()
