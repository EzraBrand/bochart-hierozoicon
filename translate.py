"""Translate Bochart's Latin into English: the prompt, the model call, and the fixed steps after it.

Used by entry.py (chunks of whole paragraphs). Rules v1 (01-Nov-2026) = TRANSLATION_RULES.md,
accepted with its four recommendations. The model translates; code does the fixed steps (finish()):
page and column marks copied from the Latin, Bible references in SBL form, folio columns joined
("fol. 19. d." -> "fol. 19d"), Hebrew letters for Syriac, Rosenmüller's notes as R1, R2 ..., the
abbreviation expansions (abbrev.py) and the identifications of names (names.py) at the first use.
Ported from lewysohn-zoologie.
"""

import json
import os
import re
import time
from pathlib import Path

import requests

import abbrev
import names

DATA = Path(__file__).parent / "data"
KEY_FILE = Path(os.environ.get("OPENROUTER_KEY_FILE", Path.home() / "Desktop/Misc/key.txt"))
RULES_VERSION = "v1"  # change when the rules change; it is part of the chunk cache key

PROMPT = """\
Below is a passage of Samuel Bochart, "Hierozoicon" (1663), in the edition of E. F. C. Rosenmüller \
(Leipzig 1793-96): a Latin study of the animals of the Bible, here {about}. It is OCR'd text, as JSON blocks \
in reading order{notes}. Translate it into English for scholars of the Bible, rabbinics and the \
history of zoology.

Rules:
- Return exactly one output block for each input block, in the same order, with the same "type" \
and "marker". Translate only the "text".
- Translate all Latin into clear, accurate scholarly English: not archaic, not a paraphrase. You \
may split Bochart's long periods into shorter sentences. Keep his numbered arguments (1., 2., I., \
II.) numbered. Keep the author's hedges ("nisi fallor" -> "if I am not mistaken", "suspicor" -> \
"I suspect", "videtur" -> "seems", "fortasse" -> "perhaps"). Do not add explanations.
- Latin quotations (the Vulgate, Jerome, Pliny ...) are translated too; keep their italics and \
quotation marks. Bochart's Latin rendering of a Greek, Hebrew or Arabic quotation is translated \
like any Latin. Do not add a translation of a Greek, Hebrew, Arabic or Syriac quotation that the \
text does not translate.
- A Latin word discussed as a word (not used for its meaning) stays in Latin, in italics, with \
the English in square brackets: "et a Graeco ὕραξ deductum sorex" -> "and from the Greek ὕραξ \
[hyrax] comes <i>sorex</i> [shrew]".
- Keep exactly as printed: Bochart's romanized forms of foreign words with their <i> tags \
(<i>sephanim</i>, <i>aljarbuo</i>, <i>chagas</i>, <i>taphza</i>); Linnaean and other zoological \
names (<i>viverra aurita</i>, <i>mus jaculus</i>); titles of books (<i>Porta coeli</i>, \
<i>Masal Kadmoni</i>); note marks (^{{(13)}}, ^{{c)}}); page marks "[II, 410]" and column marks \
"[col. 1003]", each at the corresponding place in the English.
- Bible references: keep them exactly as printed, Roman numerals included ("Levit. XI, 5.", \
"Psal. CIV. 18."); a program converts them later. Other references: the numbers become Arabic \
numerals and the structure words are translated, but the numbers are not changed to a modern \
edition: "Plinius libri octavi capite quinquagesimo quinto" -> "Pliny, book 8, chapter 55"; \
"Hist. lib. 6. cap. 37." -> "<i>Hist.</i> book 6, ch. 37"; "Azoaram Alcorani LXXIII" -> \
"Azoara 73 of the Qur'an". "p. 1012" (a column of the 1663 edition, as Rosenmüller cites it) \
stays "p. 1012".
- Hebrew and Aramaic in Hebrew letters: keep exactly as given; do NOT transliterate.
- Syriac script: keep exactly as given; do NOT transliterate (a program adds Hebrew letters).
- Ethiopic and Samaritan script: keep exactly as given; nothing added.
- Arabic and Persian script: keep exactly as given, and add an IJMES transliteration in square \
brackets right after each word or phrase: "اليربوع [al-yarbūʿ] <i>aljarbuo</i>". Transliterate \
what is written, also where the spelling looks wrong ("الجرد" -> [al-jurd]); write no vowels \
that you cannot infer with confidence. Bochart's own romanization, if it follows, stays after the \
bracket.
- Greek: keep exactly as given and add an SBL transliteration in square brackets right after each \
word or phrase: "χοιρογρύλλιος [choirogryllios]". If the text has [?], keep [?].
- Names: use the English forms in the list below for the persons and works it names, in every \
case form ("Hieronymo" -> "Jerome", "Geuhario" -> "Giauhari"). Other names: the usual English \
form of a classical or church author, otherwise as printed in the nominative.
{names}
- Fixed terms: "Seniores" (the Greek translators of the Bible) -> "the Elders"; "LXX" -> "LXX"; \
"Vulgatus interpres" -> "the Vulgate translator"; "Chaldaeus", "Chaldaice" -> "the Chaldee", \
"in Chaldee"; "Arabs interpres" -> "the Arabic translator"; "cuniculus" -> "rabbit"; "lepus" -> \
"hare"; "lepusculus" -> "little hare"; "herinaceus", "hericius", "erinaceus", "echinus" -> \
"hedgehog"; "mus" -> "mouse"; "mus Alpinus" -> "Alpine mouse"; "mus iaculus" -> "jerboa (<i>mus \
iaculus</i>)"; "choerogryllius", "hyrax", "Daman Israel" stay as printed; "saphan" stays \
"saphan" (never "rock badger", "coney" or "hyrax": the identity of the animal is what the chapter \
argues about);{chapter_terms} "Cap." (a chapter of this book) -> "Chapter". "Palaestina" in Bochart's and \
Rosenmüller's own words -> "Eretz Yisrael"; in a translated quotation of an ancient author -> \
"Palestine".
- Abbreviations: do not expand them. "Keep as printed": leave exactly as printed, nothing added \
(a program adds the expansion). "Translate": use the English form given. Others: leave as they are.
{abbrevs}
- Keep <i> tags around italic words; you may move them to fit the English word order.
- Join the printed lines of a block into running text: remove line breaks and re-join words \
hyphenated at a line end. Keep ^{{..}} and _{{..}} markup.
- A block may start or end in the middle of a sentence; translate the fragment as a fragment.

Return JSON: {{"blocks": [{{"type": ..., "marker": ..., "text": ...}}]}}.

Input blocks:
{blocks}
"""

NOTES = " (here: the notes at the foot of the pages; Rosenmüller's notes have a number in \
brackets, Bochart's a letter)"

SCHEMA = {
    "type": "object",
    "properties": {"blocks": {"type": "array", "items": {
        "type": "object",
        "properties": {"type": {"type": "string"}, "marker": {"type": "string"}, "text": {"type": "string"}},
        "required": ["type", "marker", "text"], "additionalProperties": False}}},
    "required": ["blocks"], "additionalProperties": False,
}


# What the chapter is about and its own fixed terms; entry.py sets these from ENTRIES (default: the pilot)
CHAPTER = {"about": "the chapter arguing that the Hebrew שפן (saphan) is not the rabbit but a kind of larger mouse",
           "terms": ""}


def request_body(blocks: list[dict], effort: str, notes: bool = False) -> dict:
    src = [{"type": b["type"], "marker": b.get("marker", ""), "text": b["text"]} for b in blocks]
    text = "\n".join(b["text"] for b in src)
    prompt = PROMPT.format(blocks=json.dumps({"blocks": src}, ensure_ascii=False, indent=1),
                           abbrevs=abbrev.prompt_rows(text), names=names.prompt_rows(text),
                           notes=NOTES if notes else "", about=CHAPTER["about"],
                           chapter_terms=(" " + CHAPTER["terms"]) if CHAPTER["terms"] else "")
    return {"max_tokens": 16000, "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_schema", "json_schema": {"name": "page", "strict": True, "schema": SCHEMA}},
            "reasoning": {"effort": effort}, "usage": {"include": True}}


def parse(d: dict, n_src: int, model: str, effort: str, seconds: float) -> dict:
    if "error" in d or "choices" not in d:
        raise RuntimeError(f"{d.get('error', d)}")
    ch, u = d["choices"][0], d.get("usage", {})
    if ch.get("finish_reason") not in ("stop", "end_turn"):
        raise RuntimeError(f"finish_reason={ch.get('finish_reason')}, cost ${u.get('cost', 0):.4f}")
    out = ch["message"]["content"].strip()
    if out.startswith("```"):
        out = out.split("\n", 1)[1].rsplit("```", 1)[0]
    res = json.loads(out)["blocks"]
    if len(res) != n_src:
        raise RuntimeError(f"{len(res)} blocks back for {n_src} sent")
    return {"blocks": res, "meta": {"model": d.get("model", model), "effort": effort,
                                    "input_tokens": u.get("prompt_tokens"), "output_tokens": u.get("completion_tokens"),
                                    "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                                    "cost_usd": round(u.get("cost", 0), 4), "seconds": round(seconds, 1)}}


def translate(blocks: list[dict], model: str, effort: str, notes: bool = False) -> dict:
    t = time.monotonic()
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": "Bearer " + KEY_FILE.read_text(encoding="utf-8").strip()},
        json={"model": model, **request_body(blocks, effort, notes)}, timeout=900)
    d = r.json()
    if not r.ok and "error" not in d:
        d = {"error": f"HTTP {r.status_code}: {d}"}
    return parse(d, len(blocks), model, effort, time.monotonic() - t)


# ---------- fixed steps after translation ----------

SYRIAC_TO_HEBREW = dict(zip("ܐܒܓܕܗܘܙܚܛܝܟܠܡܢܣܥܦܨܩܪܫܬ", "אבגדהוזחטיכלמנסעפצקרשת"))
FINALS = dict(zip("כמנפצ", "ךםןףץ"))
SYRIAC_RUN = re.compile(r"[ܐ-ݏ][܀-ݏ̀-ͯ]*(?:[  ]+[ܐ-ݏ][܀-ݏ̀-ͯ]*)*")


def syriac_to_hebrew(run: str) -> str:
    words = []
    for w in run.split():
        h = "".join(SYRIAC_TO_HEBREW.get(c, "") for c in w)
        if len(h) > 1 and h[-1] in FINALS:
            h = h[:-1] + FINALS[h[-1]]
        words.append(h)
    return " ".join(words)


SAMARITAN_TO_HEBREW = dict(zip("ࠀࠁࠂࠃࠄࠅࠆࠇࠈࠉࠊࠋࠌࠍࠎࠏࠐࠑࠒࠓࠔࠕ", "אבגדהוזחטיכלמנסעפצקרשת"))
SAMARITAN_RUN = re.compile(r"[ࠀ-ࠕ][ࠀ-࠿]*")


def add_hebrew_letters(text: str) -> str:
    text = SYRIAC_RUN.sub(lambda m: f"{m.group(0)} [{syriac_to_hebrew(m.group(0))}]", text)
    return SAMARITAN_RUN.sub(lambda m: f"{m.group(0)} [{samaritan_to_hebrew(m.group(0))}]", text)


def samaritan_to_hebrew(word: str) -> str:
    h = "".join(SAMARITAN_TO_HEBREW.get(c, "") for c in word)
    return h[:-1] + FINALS[h[-1]] if len(h) > 1 and h[-1] in FINALS else h


ROMAN = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}


def roman(s: str) -> int:
    n = 0
    for a, b in zip(s, s[1:] + " "):
        n += -ROMAN[a] if ROMAN.get(b, 0) > ROMAN[a] else ROMAN[a]
    return n


# Bochart's book abbreviations -> SBL (TRANSLATION_RULES.md §2); only "Book Roman, verse" forms
BOOKS = {"Gen": "Gen", "Exod": "Exod", "Levit": "Lev", "Lev": "Lev", "Deut": "Deut", "Psal": "Ps",
         "Pfal": "Ps", "Ps": "Ps", "Pf": "Ps", "Prov": "Prov", "Prou": "Prov", "Es": "Isa", "Esa": "Isa",
         "Ioel": "Joel", "Sam": "Sam",
         # tranche 1 (09-Nov-2026); "Reg." (Vulgate 1-4 Kings = 1-2 Sam, 1-2 Kgs) is left as printed
         "Psalm": "Ps", "Num": "Num", "Ios": "Josh", "Iob": "Job", "Eccles": "Eccl", "Ies": "Isa",
         "Ierem": "Jer", "Os": "Hos", "Sophon": "Zeph", "Zephan": "Zeph", "Zeph": "Zeph",
         "Iudith": "Jdt", "Tob": "Tob", "Macchab": "Macc", "Cor": "Cor"}
# the dot after the verse number ("Levit. XI, 5.") is the number's, not a sentence end: dropped
BIBLE = re.compile(r"\b(" + "|".join(sorted(BOOKS, key=len, reverse=True)) + r")[.,]?\s+([IVXLC]+)[.,]?\s*(\d+)\b\.?")


SENTENCE_NEXT = re.compile(r"(?:</i>)?(?:\s+[A-Z֐-׿]|\s*$)")  # after "28." a new sentence begins


def _bible(m: re.Match) -> str:
    out = f"{BOOKS[m.group(1)]} {roman(m.group(2))}:{m.group(3)}"
    # the dot after the verse is dropped, unless it also ends the sentence ("Prov. XXX, 28. Sed")
    if m.group(0).endswith(".") and SENTENCE_NEXT.match(m.string, m.end()):
        out += "."
    return out


def modern_citations(text: str) -> str:
    text = BIBLE.sub(_bible, text)
    # "Levit. XI, 29. 30." -> "Lev 11:29 30." -> "Lev 11:29–30." (two verses in a row)
    text = re.sub(r"(\b[A-Z][a-z]+ \d+:(\d+)) (\d+)\b",
                  lambda m: f"{m.group(1)}–{m.group(3)}" if int(m.group(3)) == int(m.group(2)) + 1 else m.group(0), text)
    return re.sub(r"\bfol\. (\d+)\.? ([a-d])\b\.?", r"fol. \1\2", text)  # "fol. 19. d." / "fol. 19 d" -> "fol. 19d"


def unnest_italics(text: str) -> str:
    """"<i>the jerboa (<i>mus iaculus</i>)</i>" -> one level of <i>: inner tags dropped."""
    out, depth = [], 0
    for part in re.split(r"(</?i>)", text):
        if part == "<i>":
            depth += 1
            if depth > 1:
                continue
        elif part == "</i>":
            depth = max(depth - 1, 0)
            if depth > 0:
                continue
        out.append(part)
    return "".join(out)


MARKS = re.compile(r"\[(?:I{1,3}, \d+|col\. \d+)\]")


def restore_marks(src: list[dict], en: list[dict]) -> int:
    """Copy the page and column marks from the Latin into the English, block by block, in order."""
    fixed = 0
    for s, e in zip(src, en):
        marks = MARKS.findall(s["text"])
        if len(MARKS.findall(e["text"])) != len(marks):
            print(f"MARKS: {len(marks)} in the Latin, {len(MARKS.findall(e['text']))} in the English: {e['text'][:60]!r}")
            continue
        it = iter(marks)
        new = MARKS.sub(lambda m: next(it), e["text"])
        fixed += new != e["text"]
        e["text"] = new
    return fixed


def label_notes(main: list[dict], notes: list[dict]) -> None:
    """Rosenmüller's notes "(13)" -> "R13", in the notes and at their marks in the text."""
    for n in notes:
        m = re.fullmatch(r"\((\d+)\)", n["marker"])
        n["label"] = f"R{m.group(1)}" if m else n["marker"]
    for b in main + notes:
        b["text"] = re.sub(r"\^\{\((\d+)\)\}", r"^{R\1}", b["text"])


def finish(cfg: dict, out: Path) -> None:
    """en.raw.json -> fixed steps -> en.json and en.md."""
    import entry  # the render function
    raw = json.loads((out / "en.raw.json").read_text(encoding="utf-8"))
    la = json.loads((out / "la.json").read_text(encoding="utf-8"))
    en_main, en_notes = raw["main"], raw["notes"]
    n = restore_marks(la["main"], en_main) + restore_marks(la["notes"], en_notes)
    # corrections of foreign-script words made after the translation (entry.FIXES): copied into the
    # English, where the word stands untranslated (a Latin word around it is matched by the next step)
    for old, new in entry.SCRIPT_SYNC:
        for b in en_main + en_notes:
            b["text"] = b["text"].replace(old, new)
    for b in en_main + en_notes:
        b["text"] = unnest_italics(add_hebrew_letters(modern_citations(b["text"])))
    label_notes(en_main, en_notes)
    problems = abbrev.check("\n".join(b["text"] for b in la["main"] + la["notes"]),
                            "\n".join(b["text"] for b in en_main + en_notes))
    for p in problems:
        print(f"ABBREVIATION CHECK: {p}")
    uses = abbrev.expand([en_main, en_notes])
    ids = names.identify([en_main, en_notes])
    raw["meta"].update({"abbreviations_expanded": sorted(uses), "names_identified": ids})
    (out / "en.json").write_text(json.dumps({"main": en_main, "notes": en_notes, "meta": raw["meta"]},
                                            ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "en.md").write_text(entry.render(cfg["title"], en_main, en_notes), encoding="utf-8")
    print(f"{n} block(s) with marks restored; {len(uses)} abbreviations expanded, {len(ids)} names identified, "
          f"{len(problems)} check problem(s); wrote {out / 'en.md'}")
