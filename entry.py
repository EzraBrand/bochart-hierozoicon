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
import os
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DATA = Path(__file__).parent / "data"
SOURCE = os.environ.get("ENTRY_SOURCE", "or-claude-opus-5.5@low+vote")  # ENTRY_SOURCE: a dry run on another OCR
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
    # Tranche 1, 09-Nov-2026: ch. 34, ch. 36 and Book 4 (chs. 1-8). Chapter heads from the MDZ hOCR
    # (logs/find_caps.py); first_col = the last margin column before the chapter head.
    "achbar": {"vol": 2, "pages": list(range(429, 436)),
               "title": "Book 3, chapter 34: The common mouse (vol. 2, pp. 429–435)",
               "start": r"^CAP\.\s*XXXIV\.", "end": r"^CAP\.\s*XXXV\.", "first_col": 1017,
               "about": "the chapter on the common mouse, Hebrew עכבר (achbar)",
               "terms": '"mus" -> "mouse"; "achbar" stays "achbar";'},
    "kippod": {"vol": 2, "pages": list(range(454, 464)),
               "title": "Book 3, chapter 36: Kippod is the hedgehog and the porcupine (vol. 2, pp. 454–462)",
               "start": r"^CAP\.\s*XXXVI\.", "end": r"LIBER QUARTUS", "first_col": 1035,
               "about": "the chapter arguing that the Hebrew קפוד (kippod) is the hedgehog and the porcupine, "
                        "against those who take it for a bird",
               "terms": '"ericius"/"hericius"/"erinaceus" -> "hedgehog"; "hystrix" -> "porcupine"; '
                        '"kippod" stays "kippod" (never "hedgehog": the identity is what the chapter argues);'},
    "tsab": {"vol": 2, "pages": list(range(463, 488)),
             "title": "Book 4, chapter 1: Tsab (Lev 11:29) is the land crocodile (vol. 2, pp. 463–487)",
             "start": r"LIBER QUARTUS", "end": r"^CAP\.\s*II\.",
             "about": "the first chapter of the book on the oviparous quadrupeds, arguing that the Hebrew צב "
                      "(tsab) of Lev 11:29 is the land crocodile, with Arabic sources",
             "terms": '"crocodilus terrestris" -> "land crocodile"; "lacerta" -> "lizard"; "stellio" -> '
                      '"stellio" (the Latin name is kept); "scincus" -> "skink"; "tsab" stays "tsab" '
                      '(never "tortoise" or "crocodile": the identity is what the chapter argues);'},
    "anaqah": {"vol": 2, "pages": list(range(487, 494)),
               "title": "Book 4, chapter 2: Anaka is a kind of stellio, named from its harsh cry (vol. 2, pp. 487–493)",
               "start": r"^CAP\.\s*II\.", "end": r"^CAP\.\s*III\.", "first_col": 1063,
               "about": "the chapter arguing that the Hebrew אנקה (anaka) of Lev 11:30 is a kind of stellio, "
                        "named from its harsh cry",
               "terms": '"stellio" -> "stellio" (the Latin name is kept); "lacerta" -> "lizard"; '
                        '"anaka" stays "anaka";'},
    "koach": {"vol": 2, "pages": list(range(493, 498)),
              "title": "Book 4, chapter 3: Coach is the waral, the largest lizard of Arabia (vol. 2, pp. 493–497)",
              "start": r"^CAP\.\s*III\.", "end": r"^CAP\.\s*IV\.",
              "about": "the chapter arguing that the Hebrew כח (coach) of Lev 11:30 is the Arabic ورل (waral), "
                       "the largest and strongest lizard of Arabia",
              "terms": '"lacerta" -> "lizard"; "coach" stays "coach"; ورل is transliterated "waral";'},
    "letaah": {"vol": 2, "pages": list(range(497, 501)),
               "title": "Book 4, chapter 4: Leta is a venomous lizard like the stellio (vol. 2, pp. 497–500)",
               "start": r"^CAP\.\s*IV\.", "end": r"^CAP\.\s*V\.",
               "about": "the chapter arguing that the Hebrew לטאה (leta) of Lev 11:30 is a lizard like the "
                        "stellio, very venomous",
               "terms": '"lacerta" -> "lizard"; "stellio" -> "stellio" (the Latin name is kept); '
                        '"leta" stays "leta";'},
    "chomet": {"vol": 2, "pages": list(range(500, 504)),
               "title": "Book 4, chapter 5: Chomet is a lizard that lives in the sand (vol. 2, pp. 500–503)",
               "start": r"^CAP\.\s*V\.", "end": r"^CAP\.\s*VI\.", "first_col": 1075,
               "about": "the chapter arguing that the Hebrew חומט (chomet) of Lev 11:30 is a lizard that lives "
                        "in the sand",
               "terms": '"lacerta" -> "lizard"; "chomet" stays "chomet";'},
    "tinshemet": {"vol": 2, "pages": list(range(503, 511)),
                  "title": "Book 4, chapter 6: Tinshemeth (Lev 11:30) is the chameleon (vol. 2, pp. 503–510)",
                  "start": r"^CAP\.\s*VI\.", "end": r"^CAP\.\s*VII\.", "first_col": 1078,
                  "about": "the chapter arguing that the Hebrew תנשמת (tinshemeth) of Lev 11:30 is the chameleon",
                  "terms": '"chamaeleon" -> "chameleon"; "lacerta" -> "lizard"; "tinshemeth" stays "tinshemeth";'},
    "semamit": {"vol": 2, "pages": list(range(510, 521)),
                "title": "Book 4, chapter 7: Semamith (Prov 30:28) is not the ape nor the spider but the stellio "
                         "(vol. 2, pp. 510–520)",
                "start": r"^CAP\.\s*VII\.", "end": r"^CAP\.\s*VIII\.", "first_col": 1083,
                "about": "the chapter arguing that the Hebrew שממית (semamith) of Prov 30:28 is not the ape nor "
                         "the spider but the stellio",
                "terms": '"stellio" -> "stellio" (the Latin name is kept); "simia" -> "ape"; "aranea" -> '
                         '"spider"; "semamith" stays "semamith";'},
    "chelonai": {"vol": 2, "pages": list(range(520, 525)),
                 "title": "Book 4, chapter 8: Why the altars of the idols are said to be ὡς χελῶναι, like "
                          "tortoises, in the Greek version of Hosea (vol. 2, pp. 520–523)",
                 "start": r"^CAP\.\s*VIII\.", "end": r"PARS SECUNDA", "first_col": 1090,
                 "about": "the chapter on why the Greek version (the Septuagint) of Hosea says that the altars "
                          "of the idols are ὡς χελῶναι, like tortoises",
                 "terms": '"testudo" -> "tortoise" (or "tortoise shell" where the shell is meant);'},
    # Tranche 2, 10-Nov-2026: Pars II (the birds), Book 1 (the clean birds), chs. 1-7: the dove. Chapter
    # heads from the MDZ hOCR (logs/find_chapters_t2.log). The margin columns of 1663 start again at 1.
    "jonah": {"vol": 2, "pages": list(range(524, 534)),
              "title": "Part 2, Book 1, chapter 1: The Hebrew name of the dove (vol. 2, pp. 524–532)",
              "start": r"PARS SECUNDA", "end": r"^CAP\.\s*II\.",
              "about": "the first chapter of Part 2 (the birds), Book 1 (the clean birds): the Hebrew name of "
                       "the dove, יונה (jonah), and its etymology",
              "terms": '"columba" -> "dove" (never "pigeon"); "turtur" -> "turtledove"; "palumbes" -> "wood '
                       'pigeon"; "jonah"/"jona" (Bochart\'s romanized Hebrew) stays as printed;'},
    "columba-pennae": {"vol": 2, "pages": list(range(533, 546)),
                       "title": "Part 2, Book 1, chapter 2: The dove's feathers, neck, eyes, moaning and flight "
                                "(vol. 2, pp. 533–544)",
                       "start": r"^CAP\.\s*II\.", "end": r"^CAP\.\s*III\.",
                       "about": "the chapter on the dove's feathers, neck, eyes, moaning and flight in the Bible",
                       "terms": '"columba" -> "dove" (never "pigeon"); "turtur" -> "turtledove"; "gemitus" -> '
                                '"moaning"; "pennae" -> "feathers" (or "wings" where the flight is meant);'},
    "columbaria": {"vol": 2, "pages": list(range(545, 550)),
                   "title": "Part 2, Book 1, chapter 3: The dwellings of doves (vol. 2, pp. 545–548)",
                   "start": r"^CAP\.\s*III\.", "end": r"^CAP\.\s*IV\.",
                   "about": "the chapter on where doves dwell: dovecotes, rocks and clefts",
                   "terms": '"columba" -> "dove" (never "pigeon"); "columbarium" -> "dovecote";'},
    "columba-mores": {"vol": 2, "pages": list(range(549, 558)),
                      "title": "Part 2, Book 1, chapter 4: The dove's simplicity, gentleness, chastity and "
                               "timidity (vol. 2, pp. 549–556)",
                      "start": r"^CAP\.\s*IV\.", "end": r"^CAP\.\s*V\.",
                      "about": "the chapter on the dove's simplicity, gentleness, chastity and timidity",
                      "terms": '"columba" -> "dove" (never "pigeon"); "simplicitas" -> "simplicity"; '
                               '"mansuetudo" -> "gentleness"; "castitas" -> "chastity";'},
    "columba-sacrificia": {"vol": 2, "pages": list(range(557, 561)),
                           "title": "Part 2, Book 1, chapter 5: The sacrifices of doves and turtledoves "
                                    "(vol. 2, pp. 557–559)",
                           "start": r"^CAP\.\s*V\.", "end": r"^CAP\.\s*VI\.",
                           "about": "the chapter on the sacrifices of doves and turtledoves in the Law",
                           "terms": '"columba" -> "dove" (never "pigeon"); "turtur" -> "turtledove"; '
                                    '"pullus columbae" -> "young dove";'},
    "columba-noachi": {"vol": 2, "pages": list(range(560, 573)),
                       "title": "Part 2, Book 1, chapter 6: Noah's dove, and the form of a dove at the baptism "
                                "of Christ (vol. 2, pp. 560–571)",
                       "start": r"^CAP\.\s*VI\.", "end": r"^CAP\.\s*VII\.",
                       "about": "the chapter on Noah's dove (Gen 8) and on the form of a dove in which the Spirit "
                                "appeared at the baptism of Christ",
                       "terms": '"columba" -> "dove" (never "pigeon"); "ramus olivae" -> "olive branch";'},
    "chiryonim": {"vol": 2, "pages": list(range(572, 591)),
                  "title": "Part 2, Book 1, chapter 7: Chiryonim or dibyonim (2 Kgs 6:25) is a kind of chickpea, "
                           "not dove's dung (vol. 2, pp. 572–589)",
                  "start": r"^CAP\.\s*VII\.", "end": r"^CAP\.\s*VIII\.",
                  "about": "the chapter arguing that חריונים (chiryonim) or דביונים (dibyonim) of 2 Kgs 6:25, "
                           "sold at a high price in the siege of Samaria, is a kind of chickpea, not dove's dung",
                  "terms": '"columba" -> "dove" (never "pigeon"); "cicer" -> "chickpea"; "stercus columbarum"/'
                           '"fimus columbinus" -> "dove\'s dung"; Bochart\'s romanized Hebrew names stay as printed;'},
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
    # tranche 1 (09-Nov-2026): superscript letters as note marks; the margin mark of p. 495 is printed
    # 1071 (read on the scan; Opus and MDZ read 1971)
    479: [("^{ᵉ)}", "^{e)}"), ('qui non', 'qui nou')],
    495: [("⟦p. 1971⟧", "⟦p. 1071⟧"), ('τȣ̃', 'τοῦ')],
    510: [("^{ᵃ)}", "^{a)}")],
    # tranche 1: catchwords read into the body text (the next page begins with the same word)
    456: [("الافاع\nولا", "الافاع")],
    464: [("وان كان\nيشبهه", "وان كان"), ('פרויט.', 'פויוט.')],
    466: [("يخرج من\nحاجره", "يخرج من")],
    471: [("aluntur.</i>\nوكذلك", "aluntur.</i>")],
    473: [("ut de\neo", "ut de")],
    480: [("فلا\nياكلونها", "فلا")],
    482: [("οἱ\nχερσαῖοι,", "οἱ"), ('talibus crocodilis accipiendum,', 'talibus crccodilis accipiendum,')],
    492: [("<i>Gal-\nlica.</i>", "<i>Gal-</i>")],
    497: [("quod id\nipsum", "quod id")],
    502: [("العظاة\nعند", "العظاة")],
    503: [("aspi-\nratio,", "aspi-")],
    514: [("sam-\nmabras,", "sam-")],
    # tranche 1, scan check (09-Nov-2026): the print differs from the vote's proposal
    455: [('Poniarius</i> ריצ"ו', 'Poniarius</i> ריצ"יו'), ('Selomo</i> הריצון', 'Selomo</i> הריצ"ון')],
    461: [('ὄπω', 'οὔπω')],
    474: [('צוק', 'צרק')],
    475: [('ܚܪܕܘܢܐ', 'ܚܕܪܘܢܐ')],
    484: [('ἁρμόζει', 'ἁρμώζει')],
    486: [('ΧΑΡΟΥΚΙ,', 'ΧΑΡΟΥΚῚ,')],
    490: [('à', 'á')],
    498: [('عشّة', 'عشه')],
    501: [('Damir, اللحكا دويبة', 'Damir, لحلكا دويبة'), ('بالعظاة', 'بالعغناة')],
    511: [('Εἱλίσσετε', 'Εἰλίσσετε')],
    512: [('στάχυς (lege', 'στάχους (lege')],
    517: [('ἐκδύνηται·', 'ἐκδύηται·')],
    # tranche 2 (10-Nov-2026): margin column numbers read on the scan (qa.py found the gaps in the
    # sequence); col. 34 is not printed on pp. 567-568
    535: [("⟦p. 19⟧", "⟦p. 10⟧"), ('והחורים', 'והתורים')],  # the Hebrew: group A scan check
    557: [("⟦p. 24⟧", "⟦p. 26⟧")],
    567: [("⟦p. 39⟧", "⟦p. 33⟧")],
    # tranche 2, group A, scan check (10-Nov-2026): the print differs from the vote's text (misprints kept)
    525: [('περιστερὰν δε,', 'περιστεράν δε,')],
    528: [('albis', 'aleis')],
    529: [('παλαιοῦ', 'παλαίου')],
    531: [('cum حمام', 'eum حمام')],
    537: [('فراف <i>riphraph</i>', 'رفراف <i>riphraph</i>')],
    542: [('ὀυκ', 'οὐκ')],
    # tranche 2, group B, scan check (10-Nov-2026): the print differs from the vote's text (misprints kept);
    # p. 560: the Hebrew words of Ezek 22:24 were read in visual order and without the ו of גושמה
    546: [('Ἅ ῥά θ᾽ ὑφ᾽', 'Ἥ ῥάθ᾽ ὑφ᾽')],
    548: [('ἀγροὺς,', 'ἄγρους,')],
    551: [('مثل', 'مشل'), ('ἀπλούστατοι', 'ἁπλούστατοι')],
    559: [('למקדשין', 'למקדשי')],
    560: [('ועם ביום גשמה ולא היא,', 'היא ולא גושמה ביום זעם,')],
    562: [('Ἄλλα', 'Ἀλλὰ')],
    563: [('σεγαστὰς', 'στεγαστὰς')],
    565: [('ὑῶν', 'ὑὼν'), ('مملولة', 'مبلولة')],
    # tranche 2, group C, scan check (10-Nov-2026): the print differs from the vote's text (misprints kept);
    # p. 568 Syriac as in the Peshitta of Luke 3:22; p. 589 the Greek article was read as Hebrew דא
    568: [('ܦܓܪܐ ܕܝܘܢܐ,', 'ܓܘܫܡܐ ܕܝܘܢܐ,')],
    576: [('מחראות^{d)}', 'טחוראות^{d)}')],
    578: [('ܢܩܒܐ', 'ܚܪܘܪܐ')],
    579: [('מדת של', 'מרת של'), ('חטים,', 'חטום,'), ('Φοινικηίου', 'Φοινικηΐου')],
    589: [('חרי דא,', 'τοῦ חרי,')],
    590: [('ሞሆኒቅ፡', 'መዐንቅ፡')],
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
        b["text"] = re.sub(r"\(\^\{(\d+)\}\)", r"^{(\1)}", b["text"])  # p. 541: (^{6}) for ^{(6)}
        b["text"] = MARGIN.sub(r"[col. \1]", b["text"])
    return blocks


CATCHWORD_KEY = re.compile(r"</?i>|[^\w\s֐-ۿ܀-ݏͰ-Ͽἀ-῿-]")


def drop_catchwords(vol: int, pages: list[int], blocks: dict[int, list[dict]]) -> None:
    """The catchword at the foot of a page is often read into the body text, as the last line of the
    page's last body block (tranche 1: 12 of 74 pages). It is dropped where that last line (1-3 words)
    is the same as the first words of the next page's first body block. In place; prints each drop.
    A closing </i> in the dropped line is kept ("caeci de-\\ngunt</i>," -> "caeci de-</i>")."""
    for page in pages:
        nxt = blocks.get(page + 1) or page_blocks_or_none(vol, page + 1)
        if nxt is None:
            continue
        body = [b for b in blocks[page] if b["type"] == "body"]
        first = next((b for b in nxt if b["type"] == "body"), None)
        if not body or first is None or "\n" not in body[-1]["text"]:
            continue
        head, last = body[-1]["text"].rsplit("\n", 1)
        words = CATCHWORD_KEY.sub("", last).split()
        if not words or len(last.split()) > 3:
            continue
        first_words = CATCHWORD_KEY.sub("", first["text"].split("\n", 1)[0]).split()[:len(words)]
        if words == first_words:
            body[-1]["text"] = head + ("</i>" if "</i>" in last and last.count("</i>") > last.count("<i>") else "")
            print(f"catchword on p. {page} dropped: {last!r}")


def page_blocks_or_none(vol: int, page: int) -> list[dict] | None:
    return page_blocks(vol, page) if (DATA / "ocr" / SOURCE / f"{page_key(vol, page)}.json").exists() else None


def build(cfg: dict) -> tuple[list[dict], list[dict]]:
    """-> (main blocks, note blocks); each block has a "page"."""
    vol = cfg["vol"]
    main, notes, started, ended = [], [], False, False
    page_text, other_text = {}, {}
    blocks = {page: page_blocks(vol, page) for page in cfg["pages"]}
    drop_catchwords(vol, cfg["pages"], blocks)
    for page in cfg["pages"]:
        first_on_page = True
        for b in blocks[page]:
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
