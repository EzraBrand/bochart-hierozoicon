> **Archived 08-Nov-2026.** The full README of the pilot (ch. 33), with the OCR tests, the layout notes, the gold rules and the error tables. Replaced by a short [README](../README.md). Links in this file are relative to the repository root, so open them from there.

# bochart-hierozoicon

OCR and English translation of Samuel Bochart, *Hierozoicon, sive bipertitum opus de animalibus
Sacrae Scripturae* (London 1663), in the edition of E. F. C. Rosenmüller (Leipzig: Breitkopf,
1793–96, 3 vols.). **Pilot only:** Book III, ch. 33, on the shafan ("non esse Cuniculum").

Same family as [low-flora](https://github.com/EzraBrand/low-flora) and
[lewysohn-zoologie](https://github.com/EzraBrand/lewysohn-zoologie); the code is ported from
lewysohn-zoologie. Companion: [talmud-zoology-factcheck](https://github.com/EzraBrand/talmud-zoology-factcheck),
claim 7 (hyrax/shafan).

**Reading edition (web):** https://ezrabrand.github.io/bochart-hierozoicon/ — Latin and English side
by side, a scan link at each page mark, each column mark of 1663 linked to the Frankfurt 1675
scan, transliterations and identifications as tooltips, Rosenmüller's notes R1–R13 and Bochart's
a)–c). Built by `build_site.py` into `docs/` (GitHub Pages serves `main:/docs`).

## Status (08-Nov-2026)

| Step | Status |
|---|---|
| 1. Scans, manifest, MDZ OCR layer, layout note | done |
| 2. OCR test on pp. 409, 422, 428 (Opus, Sonnet, Gemini Flash, MDZ); gold pp. 422, 428 | done; gold pages checked by you (01-Nov-2026) |
| 3. Translation rules for Latin | [TRANSLATION_RULES.md](TRANSLATION_RULES.md), accepted 01-Nov-2026 |
| 4. OCR of the whole pilot, pp. 408–429 (Opus main, Flash second reader), QA; Hebrew gold p. 410 | done; gold p. 410 checked by you (01-Nov-2026) |
| 5. Second reading and vote, all scripts (`check.py`, `judge.py`, `vote.py`) | done; 40 changes; **review list for you** |
| 6. Page joins (`entry.py`), translation (`translate.py`, rules v1) | done: [Latin](data/entries/shafan/la.md), [English](data/entries/shafan/en.md) |
| 7. Reading edition (`build_site.py`, GitHub Pages) | done: https://ezrabrand.github.io/bochart-hierozoicon/ |
| 8. Cost test; ch. 35 (*choled*, pp. 435–453) with the Batch API pipeline | done 08-Nov-2026: [COST_TEST.md](COST_TEST.md), $2.56 for 21 pages (−57% a page); [Latin](data/entries/choled/la.md), [English](data/entries/choled/en.md); **review list for you** (`logs/vote_v2-434-454.csv`) |

Decisions (01-Nov-2026): Bochart's chapter synopsis, which Rosenmüller leaves out, will be added
from Frankfurt 1675 as a block of its own, marked as such, after the Rosenmüller OCR is settled.
Arabic is transcribed as printed (see Gold rules).

## Source

Munich, Bayerische Staatsbibliothek (MDZ), IIIF Presentation 2.0:

| Vol. | MDZ id | Canvases | Notes |
|---|---|---|---|
| 1 | bsb10353453 | — | not fetched yet |
| 2 | bsb10353454 | 892 | 1794; "X, 870 S."; scans about 2125×2830 px |
| 3 | bsb10353455 | — | not fetched yet |

- Manifest: `https://api.digitale-sammlungen.de/iiif/presentation/v2/{id}/manifest`; images:
  `https://api.digitale-sammlungen.de/iiif/image/v2/{id}_{canvas:05d}/full/full/0/default.jpg`.
- **Vol. 2: printed page = canvas − 16.** The MDZ labels ("415 (0431)") are correct for the pilot
  pages (checked on the scans of pp. 409, 422, 428, 429).
- **OCR layer:** each canvas has `seeAlso` → `https://api.digitale-sammlungen.de/ocr/{id}/{canvas}`,
  hOCR 1.2 (blocks, lines, words with bboxes; page `lang="la"`; no word confidences in the files).
- Licence in the manifest: `https://rightsstatements.org/vocab/NoC-NC/1.0/` (no copyright,
  non-commercial use of the scans). The text is public domain. Scans are not stored here.

**Other editions (checked 01-Nov-2026):**
- Frankfurt 1675, MDZ bsb11935761 (Pars I, "1094 Sp.", 688 canvases, 2624×4328 px) and
  bsb11935762 (Pars II, "888 Sp."). The column numbers are those of London 1663 (same count, 1094
  and 888). Ch. 33 starts in col. 1001 in both; cols. 1001–1018 = canvases 569–577 of bsb11935761.
  The scans are larger than Rosenmüller's, which may help with the Arabic.
- London 1663 (EEBO microfilm on archive.org): not checked yet.

## Pilot pages

Ch. 33 runs from p. 409 (after three lines of ch. 32) to the top of p. 429 (then ch. 34, *De
vulgari Mure*). So the pilot is **pp. 409–429 (21 pages, canvases 425–445)**; p. 408 is fetched
too. London/Frankfurt **cols. 1001–1017** (Rosenmüller's margin: p. 1001 on p. 409, p. 1012 on
p. 422, p. 1017 on p. 429).

```
py -3.13 fetch.py list --vol 2 --from 420 --to 450    # canvas, label, image id
py -3.13 fetch.py sample                              # pilot scans + hOCR + data/raw/manifest.json
uv run mdz_ocr.py                                     # hOCR -> data/ocr/mdz/{page}.json/.md

uv run ocr.py v2-0409 v2-0422 v2-0428 --model anthropic/claude-opus-5.5 --effort low
uv run ocr.py v2-0409 v2-0422 v2-0428 --model anthropic/claude-sonnet-5.5 --effort low
uv run ocr.py v2-0409 v2-0422 v2-0428 --model google/gemini-3.8-flash --effort low
uv run diffwords.py v2-0422 --main "or-claude-opus-5.5@low"   # words where the engines differ
uv run eval.py draft v2-0422 --from "or-claude-opus-5.5@low"  # start a gold page
uv run eval.py --loose                                        # CER table (--loose: see eval.py)
```

`ocr.py` sends a page as two images (top and bottom half) when one image would be over the API's
pixel limit, so the Arabic dots and vowel signs reach the model at full resolution. Parallel
workers: `--start N --stride M`.

Page keys: `v2-0409` (volume, printed page); `v2-scan0005` for an unnumbered page.

## Layout (Rosenmüller, vol. 2, pp. 408–429)

- **One column** of main text, about 35 lines a page. No line numbers.
- **Running head:** recto `Cap. XXXIII. Probatur, שפן esse majoris muris genus. 409`; verso
  `428 Probatur, שפן … L. III.` (the Hebrew is in the head). Foot: signature (`Fff`, `Hhh 3`, and
  on the first page of a gathering `BOCHARTI Hieroz. Tom. II.`) and a **catchword** (`Graecum`,
  `um`, `Saepe`). All furniture.
- **Chapter heading:** `CAP. XXXIII.` and a long italic argument (5 lines, with Hebrew, Greek and
  Arabic). Bochart's own chapter synopsis of 1663/1675 (col. 1001, "Octo rationes, quibus probari
  videtur …") is **not in Rosenmüller** (to confirm on the next pages of Frankfurt 1675).
- **Margin:** the old column numbers, printed `p. 1001`, `p. 1002` … (Rosenmüller calls them
  "p."; his own notes cite "supra p. 1012"). Keep them as page marks of their own.
- **Two layers of notes**, at the foot:
  - Bochart's notes, with **letters**: `c) Pag. 1003.` (short cross-references; full width).
  - Rosenmüller's notes, with **numbers in brackets**: `(1)`, `(13)`; the mark in the text is
    `(¹³)`, a raised number in brackets. Set in **two columns**, smaller type. A note can run on to
    the next page.
- **Type:** roman and italic Latin with long s (ſ) and ligatures (ſt, ct, æ). Italics carry the
  quotations, titles and the Latin glosses of foreign words; they matter for the translation.
- **Scripts:** Greek in an old type with many ligatures (ȣ for ου, a καί ligature);
  unpointed square Hebrew; **Arabic in naskh type, often whole lines**, unvocalized in the text and
  vocalized in some notes; **Syriac in Estrangela type** (p. 428: four words, *chagas*, *chagisa*, *chagira*). Bochart's
  transliterations follow the foreign word in italics (`שפנים ſephanim`, `اليربوع aljarbuo`).
  Arabic and Latin share a line, so the reading order of a mixed line matters.

Characters per script on each page, from the MDZ OCR (it drops Syriac, so "Syr" counts the word
*Syrus/Syri* in the Latin as a sign of Syriac; notes: lines that start with a note mark):

| Page | Latin | Greek | Hebrew | Arabic | "Syr" | (n) notes | a) notes |
|---|---|---|---|---|---|---|---|
| 409 | 1648 | 135 | 43 | 14 | 0 | 0 | 0 |
| 410 | 1993 | 39 | 234 | 3 | 0 | 0 | 0 |
| 411 | 2129 | 267 | 20 | 2 | 1 | 1 | 0 |
| 412 | 2176 | 7 | 138 | 0 | 3 | 0 | 0 |
| 413 | 1364 | 13 | 4 | 326 | 0 | 1 | 0 |
| 414 | 2501 | 20 | 12 | 18 | 6 | 1 | 0 |
| 415 | 2138 | 3 | 242 | 0 | 0 | 0 | 0 |
| 416 | 1434 | 0 | 11 | 345 | 0 | 0 | 0 |
| 417 | 1876 | 201 | 14 | 13 | 0 | 1 | 0 |
| 418 | 1859 | 270 | 16 | 16 | 1 | 0 | 0 |
| 419 | 1893 | 240 | 57 | 14 | 0 | 0 | 0 |
| 420 | 1764 | 467 | 3 | 11 | 0 | 2 | 0 |
| 421 | 1627 | 191 | 0 | 174 | 0 | 0 | 0 |
| 422 | 1255 | 0 | 0 | 517 | 0 | 2 | 0 |
| 423 | 1393 | 0 | 0 | 289 | 0 | 0 | 1 |
| 424 | 1713 | 33 | 3 | 239 | 1 | 1 | 0 |
| 425 | 1530 | 21 | 0 | 330 | 0 | 0 | 0 |
| 426 | 1612 | 18 | 10 | 322 | 0 | 0 | 0 |
| 427 | 2252 | 8 | 0 | 9 | 1 | 1 | 0 |
| 428 | 1751 | 283 | 15 | 54 | 2 | 1 | 0 |
| 429 | 1339 | 338 | 57 | 7 | 0 | 0 | 1 |

About 2,500 characters a page, so the chapter is about 50,000 characters (about 8,000 words).

## The MDZ OCR layer (pp. 409, 422, 428; read against the scans)

| Script | Result | Errors seen (each checked on the scan) |
|---|---|---|
| Latin | good; no dropped lines in the main text | long s written as `f` or `ſ` at random (`feu`, `effe`, `ſic`); **italics lost**; `XXXIII` → `XXXII` (twice on p. 409); `Tſade` → `Tjade`; `Patrae` for `Petrae` |
| Greek | good, with modern polytonic accents | the **ου ligature ȣ is read as ε**: Δίπȣς → `Δίπες`, ἔχȣσι → `ἔχεσι`, βαδίζȣσιν → `βαδίζεσιν` (systematic) |
| Hebrew | mostly right | **plausible wrong words**: שפן → `שמן` (p. 428, twice, also in the running head); טפזא → `טפו` |
| Arabic, unvocalized | **better than expected**: most lines on p. 422 right | ن → ت (`باستانه` for باسنانه); م → ب (`البا` for الما); adds a hamza the print does not have (`الرئيس` for الرييس); keeps tatweel (`ذنـبـة`) |
| Arabic, vocalized (notes) | poor | vowel marks read as stray letters (`९६`, `If`) |
| Syriac | **dropped** | not in the text at all |
| Layout | weak | margin numbers garbled (`p.co.`, `p. 100%` for p. 1001, p. 1002); the two note columns split into fragments and out of order; in mixed Arabic–Latin lines the Latin is put at the wrong end (`… في نشر من Et paullo infra`) |

So the MDZ text is a fair first reading of the Latin, Greek and plain Arabic, and a possible
second reader for the Arabic (as Gemini Flash was for the Hebrew in Lewysohn). It cannot be the
main OCR: no italics, no Syriac, no note structure.

(Correction, 01-Nov-2026: step 1 said that مقام on p. 422 is printed with the dot of غ. At 2× it
has the two dots of ق; this type sets the dots of medial ق close together. Not a printer's error.)

## Gold rules

The same as the OCR prompt in `ocr.py`. In short: as printed, never corrected; long s → s; type
ligatures as plain letters (Greek ȣ → ου); italics as `<i>`; one line per printed line; margin
column numbers as `⟦p. 1001⟧` at the end of their line; note marks `^{(13)}` (Rosenmüller) and
`^{c)}` (Bochart); notes after the text, the left note column before the right one.

**Arabic as printed:** the letters and dots of the print, vowel signs only where printed, no
added hamza, no tatweel. Where the print differs from the expected Arabic, the gold keeps the print
and the difference goes into a list of printer's errors for the translation step (none found so
far for certain; see p. 428 below). One limit: in this type the **isolated forms of د/ذ are a cup,
like ن** (ذ = cup with a dot, the same as ن). There the gold follows the word (وذو, ذنبه), and
only the presence or absence of a dot is "as printed" (الجرد, no dot).

## Results of the OCR test (pp. 409, 422, 428; 01-Nov-2026)

Gold pages: [v2-0422](data/gold/v2-0422.txt) (Arabic) and [v2-0428](data/gold/v2-0428.txt)
(Greek, Syriac, vowelled Arabic, two-column notes), drafted from the Opus output and corrected
where any engine disagreed, each case read on the scan at 2–4×; checked by you on 01-Nov-2026. p. 409
has no gold page; its differences were read on the scan too.

CER (`eval.py --loose`, both gold pages; Latin script includes the transliterations):

| Engine | $/page | s/page | all | Latin | Greek | Hebrew | Arabic | Syriac | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Opus 5.5 @low | 0.086 | 30 | **0.3%** | 0.1% | 1.1% | 0% | 1.1% | 0% | right reading order, notes and margin numbers on all 3 pages |
| Sonnet 5.5 @low | 0.041 | 16 | 4.4% | 2.1% | 0.7% | 0% | 8.1% | 6.2% | p. 422: the two note columns mixed, margin number dropped; dropped the vowel signs in note (13) |
| Gemini 3.8 Flash @low | 0.011 | 18 | 10.3% | 7.9% | 0.4% | 0% | 2.5% | 0% | p. 422: the mixed Arabic–Latin lines in the wrong order; notes mixed; margin number lost |
| MDZ hOCR | free | — | 9.1% | 6.8% | 3.5% | 58% | 27% | 100% | see above |
| (gold characters) | | | 4,875 | 3,009 | 285 | 19 | 557 | 16 | |

The high Latin CER of Sonnet and Flash is mostly text in the wrong place (note columns, line
order), not misread letters. Hebrew: see p. 410 below.

**Opus's errors** (all 13 cases on the three pages; every one checked on the scan):

| Page | Print | Opus | Others |
|---|---|---|---|
| 409 | `CAP. XXXIII.` (twice) | `XXXIIII` | Sonnet, Flash right |
| 409 | اليربوع | الجربوع | Sonnet, Flash, MDZ right |
| 422 | وذو (cup-shaped ذ) | ذو (و dropped) | Flash, MDZ right |
| 422 | ويسمى | ويسمي | all wrong (MDZ too) |
| 422 | ادركهم | اسركهم | Flash, MDZ right |
| 422 | الجرد (no dot) | الجرذ | MDZ right |
| 422 | نشر | نشز | Sonnet, Flash, MDZ right |
| 428 | `ficet` (signi-ficet, note from p. 427) | `licet` | Sonnet, MDZ right |
| 428 | ὕραξ (twice) | ὗραξ | all others right |
| 428 | μῦες | μύες | Sonnet, Flash right |
| 428 | `causa` (long s) | `caussa` | Sonnet, MDZ right |
| 428 | أَلشَّعْنُ (no dot on ع) | أَلشَّغْنُ | Sonnet, MDZ: right letters, no vowel signs (Flash: ف) |
| 428 | `Bochartus,` | `Bochartus.` | MDZ right |
| 410 | מב״ח (abbreviation) | מבה״ח | Flash right |
| 410 | ב״ח | בה״ח | Flash right |
| 410 | سفن (ف) | سغن | Flash, MDZ right |

Most of them **"correct" the print toward an expected form**: the better Arabic word (نشز
"raised ground", الجرذ "rat"), the classical spelling (caussa), the dictionary accent (ὗραξ). This
is the same kind of error as Opus's plausible Hebrew words in Lewysohn, so the second-reading step
is needed here for **every script, Latin included**. Opus got right what the others missed: the
ου ligature (Δίπους; all others Δίπες), ἁλτικὸν, οἳ, "Petrae" (MDZ and Flash: "Patrae"), the
Syriac ܚܓܝܣܐ (Sonnet: ܚܓܝܫܐ), the vowelled Arabic in the notes.

**A literal second reader:** the MDZ layer does not "correct": on p. 422 it reads 4 of Opus's 5
Arabic errors right (Flash: 3 of 5). As a second reader it is free, but it also has many errors of
its own (long s, ȣ → ε, Syriac dropped), so it can only flag, and a judge decides (as in Lewysohn).

## OCR of the whole pilot (01-Nov-2026)

All 22 pages (pp. 408–429) with Opus 5.5 @low (main) and Gemini 3.8 Flash @low (second reader),
4 parallel workers per model. Cost: Opus $1.65, Flash $0.22 (pp. 409, 422, 428
were done in step 2).

**Gold p. 410** (240 Hebrew characters; Flash and MDZ compared, Sonnet not run on this page; each
difference read on the scan): Opus 0.1% CER, **Hebrew 0.8%: 2 errors**, both a ה added inside an
abbreviation (מב״ח → מבה״ח, ב״ח → בה״ח: Opus "expands" toward מבעלי החיים), and سفن → سغن. Not
decided: the Italian word in Hebrew letters, Opus קוני״לו; I may see קונ״לו (no י) at 3×. All
three gold pages: Opus 0.2%, Flash 6.6% (mostly order), MDZ 8.6%.

**`qa.py 408 429`** (`logs/qa_v2-408-429.csv`):
- Length against MDZ and Flash: 0.96–1.05 on every page, so no column or note is lost.
- Margin column marks: cols. 1001–1017, each once, no gap.
- Rosenmüller's notes: (1)–(13) in the chapter, each mark with its note; ch. 34 starts again at (1).
  Bochart's lettered notes: a) p. 419, b) p. 423, c) p. 429.
- One form slip: p. 419 `^{a})` for `^{a)}` (a fixed step in the entry code will normalize it).
- Page joins: 20 "continue", 2 "break" (pp. 417→418, 427→428); to check by eye at the join step.

**New scripts and problems found:**
- **Ethiopic** (not in the plan), corrected in `entry.FIXES` (02-Nov-2026, read by Claude at 4–6×,
  not by a reader of Ethiopic): p. 412 ለጊሔ፡ *legiche* (Opus: ሰጊሔ፡); p. 418 ኮሮገሬሊወን፡
  *choerogryllion*, seven signs (Opus had six: ኮርገሊሎን፡; the 3rd and 4th signs not sure).
- **Samaritan:** p. 412, Bochart's *taphsa*, Opus `[?]`: read ࠈࠐࠎࠄ (ט פ ס ה; the last letter not
  sure). The English gets Hebrew letters in brackets by code, as for Syriac ([טפסה]).
- Both corrections are copied into the English without a model call (`entry.SCRIPT_SYNC`).
- **p. 416, damaged scan:** the right edge of the last 8 lines is smeared in the MDZ scan. Opus
  filled the line ends from context ("Aben-", "regione", "occidentalem", "colligi"), against the
  prompt's "[?]" rule; Flash and MDZ read other things (the last word: Opus `po[?]`, Flash
  `possis`, MDZ `potiss`). R: read these 8 line ends in Frankfurt 1675 (Bochart's text, not
  Rosenmüller's) or in another copy of Rosenmüller.
- Opus marked one Arabic book title غهيد (p. 416); Flash has التمهيد (*al-Tamhīd* of Ibn ʿAbd
  al-Barr, which Bochart translates *Explanatio*). In the damaged part of the page.

## Second reading and vote, all scripts (01-Nov-2026)

Ported from Lewysohn's `hebcheck` / `hebjudge` / `hebvote`, changed in three ways:

1. **Two second readers, all scripts** (`check.py`): Gemini Flash and the MDZ hOCR. Every word
   where one of them differs from Opus is flagged (with folds for known noise: MDZ's f for long s,
   its added hamzas and ى, Flash's `"` for ״). 8,666 words → 587 word flags on 352 lines.
2. **No text judge.** Opus's errors here are corrections toward the expected word (نشز, caussa,
   ὗραξ, מבה״ח); a judge that decides from the sense makes the same errors.
3. **One image judge** (`judge.py`, Opus 5.5 @low): one call per printed line, with a crop of
   exactly that line (its box from the MDZ hOCR) and the readings without engine names. $2.47 for
   352 lines ($0.007 a line).

**Rule** (`vote.py`): Opus is changed only where the judge read the same as Flash or MDZ. Flash and
MDZ together never change it alone (both read Δίπες and "Patrae" where Opus was right). Multi-word
flags are voted word by word.

**Gold pages** (pp. 410, 422, 428; `eval.py --loose`):

| | all | Latin | Greek | Hebrew | Arabic |
|---|---|---|---|---|---|
| Opus | 0.2% | 0.1% | 1.2% | 1.2% | 1.2% |
| Opus + vote | **0.1%** | **0.0%** | **0.3%** | **0.0%** | 0.7% |

**Three errors in my gold pages**, found by the vote and read again on the scan (corrected; you had
approved these pages): p. 410 וחחול (a printer's error for וחתול; the same line has כחתול
correctly), p. 428 τῶ (not τῷ) and *Seholia-* (a printer's error for *Scholia-*). When I made the
gold, I checked only the words where Flash or Sonnet differed from Opus, not the MDZ-only ones.

**Outside the gold pages the judge is weaker.** I read the doubtful changes on the scan: 12 were
wrong and are kept out by a reviewed list (`REJECT` in `vote.py`). Almost all had only MDZ with
the judge: the judge tends to follow the MDZ reading (שכן for שפן, הארם for האדם, עכבר for עכלבר,
"cominune", "pleruinque", ו for ז). In the pilot an MDZ-only change was right about 6 times and
wrong about 9 times. **Rule for a larger run: every change that only MDZ supports needs a look.**

Never changed by the vote, listed for review (`ambiguous()` in `vote.py`):
- **ف/غ:** in this type the medial ف and the medial غ have the same shape (checked on الغزال
  against الفنك, الفار). The judge and MDZ read غ in الفنك, الفار, الفارة (Bochart: *alphenec*). As
  with the cup-shaped د/ذ, the gold follows the word here. This also blocks one right change (سغن →
  سفن on p. 410), so the Arabic stays at 0.7%.
- The ου ligature read as ε (καλού- → καλέ-), the στ ligature written ς, the note-mark format
  (`(³)`).

**Result:** 40 changes (Arabic 15, Latin script 14, Greek 6, Hebrew 5), e.g. causa for caussa (4 times),
Proindè, Giggeio for Viggeio, الصقلاب, اسرايل without hamza, والاسراييلي, لاذت, اذا, يناقده, قداد
(*kedad*), והגמל, י״, the printer's errors *alphenet* and λείπε-|θαι. The voted text is the
engine `or-claude-opus-5.5@low+vote`; `qa.py` on it: no change in lengths, marks or notes.

**For your review** (`logs/vote_v2-408-429.csv`, column `outcome`): 29 "judge read another text",
9 ف/غ, 7 "not similar", 12 rejected by me, 5 other (ligatures, note mark, a partial reading, one without an answer). Not voted at all: the Ethiopic (2), the
Samaritan word, the damaged line ends of p. 416.

## The chapter in English (01-Nov-2026)

**[English](data/entries/shafan/en.md)** and **[Latin](data/entries/shafan/la.md)** of Book 3,
ch. 33 (pp. 409–429): 31 paragraphs and 16 notes (13 by Rosenmüller, 3 by Bochart), 8,170 words of
Latin, 11,898 of English (with transliterations and identifications).

```
uv run entry.py shafan --no-translate   # join the pages: data/entries/shafan/la.json, la.md
uv run entry.py shafan                  # translate (Opus 5.5 @medium, chunks cached), then the fixed steps
uv run entry.py shafan --finish-only    # redo only the fixed steps from en.raw.json (no model call)
uv run abbrev.py                        # check the abbreviations, render ABBREVIATIONS.md
```

**Joining** (`entry.py`): the source is the gold text where it exists (pp. 410, 422, 428), else
the voted OCR. All 20 page joins checked by eye. Four catchwords that Opus had read into the body
text are removed by `FIXES` (pp. 410 גרה, 414 *stanter*, 418 *rias*, a printer's error for *riae*,
421 اليه); a word broken over a page joins also when a margin mark ends the line (*Histo-|riae*).
The chapter begins in col. 1001, whose mark stands in the last lines of ch. 32. Rosenmüller's note
(12) runs over to p. 428 (*signi-|ficet*) and is joined.

**Translation** (`translate.py`, rules v1 = [TRANSLATION_RULES.md](TRANSLATION_RULES.md)): Opus 5.5
@medium, 12 text and 2 note chunks, **$1.56**. Fixed steps after the model: page and column marks
(all kept by the model), Bible references in SBL form (*Levit. XI, 5.* → Lev 11:5), folio columns
(fol. 19d), Hebrew letters for Syriac (ܚܓܝܣܐ [חגיסא]), Rosenmüller's notes as R1–R13, 4
abbreviations expanded ([ABBREVIATIONS.md](ABBREVIATIONS.md), all kept by the model), 30 names
identified at their first use (`names.json`), nested italics removed.

Read against the Latin (p. 428 in full, other passages by search): accurate; Bochart's hedges,
romanizations, numbered arguments and the rules on fixed terms kept ("saphan" never rendered
"coney" or "rock badger"; *sorex* [shrew] as a word discussed; "Pliny, book 10, chapter 73";
"Azoara 73 of the Qur'an"; "Palestine" only inside a quotation of Jerome). Seen so far:
- One added gloss: "ἁλτικὸν [haltikon], a leaper" (the Latin has no "a leaper").
- Roman numerals kept in a few references in the notes ("Oedmann IV, p. 53").
- The identifications in `names.json` are from general knowledge where the basis says so; they
  need a review (TRANSLATION_RULES.md §4).

**Costs of the pilot so far:** OCR test $0.41, OCR of 22 pages $1.87, image judge $2.47,
translation $1.56: **$6.31**. $6.82 left on the key (01-Nov-2026).

## License

The code and everything added in this repository (transcriptions, gold pages, translations and
documentation) are under the [MIT License](LICENSE), © 2026 Ezra Brand.

Bochart's *Hierozoicon* and Rosenmüller's edition are in the public domain; the scans are by the
Bayerische Staatsbibliothek (MDZ), rights statement NoC-NC 1.0, and are not stored here.
