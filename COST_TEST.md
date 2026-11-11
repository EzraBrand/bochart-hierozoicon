# Cost test, 08-Nov-2026

Goal: cut the cost of the pipeline a lot, with about the same quality. Test passage: the pilot
chapter (pp. 408–429), because the three gold pages (410, 422, 428) and the reviewed vote give a
measure of quality. Spent on the test: $7.51 (key `bochart-hierozoicon`).

## Result: ch. 35 (*choled*) with the new pipeline (08-Nov-2026)

Plan B below, run on Book 3, ch. 35 (pp. 434–454, 21 pages; the chapter is pp. 435–453). The
crops go to the public repo [bochart-hierozoicon-crops](https://github.com/EzraBrand/bochart-hierozoicon-crops)
(`crophost.py`; emptied with `uv run crophost.py clean` after the run). Billed costs:

| Step | Model | Cost |
|---|---|---|
| OCR, compact output | Opus 5.5 @low, batch | $0.759 |
| Second reader | Gemini 3.8 Flash @low, batch | $0.077 |
| Image judge, 366 lines | Opus 5.5 @low, batch | $1.272 |
| Translation, 13 chunks | Opus 5.5 @low, batch | $0.452 |
| **Total** | | **$2.56** ($0.122 a page; pilot $0.283 a page: **−57%**) |

Each batch took 5–15 minutes. No failed request.

Quality (no gold page in this chapter yet):
- `qa.py`: lengths, margin column marks 1021–1036 (each once, no gap), note marks and notes: no
  problem. Two catchwords read into the body text (pp. 439, 440): removed in `entry.FIXES`.
- Vote: 27 changes; 83 listed for review (`logs/vote_v2-434-454.csv`).
- **The vote rule is changed:** a change that only MDZ supports is no longer applied but listed
  ("review (MDZ only)") unless it is in `vote.ACCEPT` (read on the scan). Of 22 such changes in
  ch. 35, about 20 were wrong. Most of them are ד read as ר (חולד → חולר, 8 times): on the scan the
  two letters hardly differ in this type, and MDZ and the judge both read ר. So ד/ר and ذ/ن (the
  cup-shaped ذ) are now type-ambiguous, like ف/غ: never changed, only listed. The 9 pilot changes of
  these kinds that were read on the scan are in `ACCEPT`, so the pilot text is unchanged.
- I read the doubtful changes on the scan: 1 accepted (*nestae*), 7 rejected (כפל is printed, a
  printer's error for נפל in Ps 58:9; *scribit*, *metalla*, the στ ligature, smeared line ends).
- Translation (Opus @low): accurate in the passages I read against the Latin; all 36 page and
  column marks, all 31 Arabic words transliterated; 3 long Greek quotations without
  transliteration; one page mark inside a quotation dropped by the model (put back by hand in the
  cached chunk). Names new in this chapter are not in `names.json` yet, so they have no
  identifications; "1 Cor. XV, 8." is not converted (the Bible-book list has no Cor).

## Tranche 1 (09-Nov-2026): Book 3, chs. 34 and 36, and Book 4 (74 new pages, 10 chapters)

| Step | Model | Cost |
|---|---|---|
| OCR, compact, `max_tokens` 10000 (was 32000) | Opus 5.5 @low + Flash 3.8 @low, batch | $2.91 |
| Re-OCR of 3 pages cut by the crop (sync) | Opus + Flash | $0.23 |
| Image judge, about 1,320 lines | Opus 5.5 @low, batch (+ 33 lines sync) | $4.67 |
| Translation, 10 chapters | Opus 5.5 @low, batch | about $1.90 |
| **Total** | | **$9.71** ($0.131 a page) |

The 10 translation batches ran in parallel; the whole tranche took about 1.5 hours (the earlier estimate was 2–3). The scan check
of the 283 doubtful readings and changes was done by 4 Opus subagents (one per page group,
`review_pack.py`); where an agent and the image judge read differently, Claude read the crop.
Result: 30 proposals accepted, 14 changes undone (mostly the ου ligature and the φ of this type read
as ε and Φ), 18 corrections from the print. Catchwords read into the body text: 12 pages.

## Tranche 2 (10-Nov-2026): Part 2, Book 1, chs. 1-7, the dove (66 new pages, p. 524 redone)

| Step | Model | Lines / pages | Cost |
|---|---|---|---|
| OCR, compact (67 pages; p. 524 again, its tranche-1 crop had cut the line ends) | Opus 5.5 @low + Flash 3.8 @low, batch | 67 + 67 | about $3.7 |
| Image judge | Opus 5.5 @low, batch, two batches (354 + 790 lines) | 1,144 lines | about $2.9 |
| Translation, 7 chapters in parallel | Opus 5.5 @low, batch | 7 batches | about $1.7 |
| **Total** (key usage of the day) | | | **$8.23** ($0.125 a page) |

Wall-clock about 3 h, of which: the Flash OCR batch took 26 min (Opus 7 min); the judge was run
twice because `mdz_ocr.py` had not been run for pp. 545-590 and `check.py` then flagged each of those
pages as one block (fixed: an absent reader is skipped and reported). The scan check of 219 items
(76 + 63 + 80) was done by 3 subagents (Claude Fable 5.1) in parallel, one per page group, with
`logs/review_prompt_t2.md`; `apply_review.py` turned their decisions into the lists. Result: 52
changes confirmed, 17 undone (again the ȣ ligature and the lower-case φ of this type, and three
times قلي → قلى), 40 proposals accepted, 26 corrections from the print (misprints kept: *aleis*,
*vent*, *filins*, *effissum*, *eum*; a Hebrew line read in visual order on p. 560; the Greek article
τοῦ read as Hebrew דא on p. 589; a Syriac word on pp. 568 and 578; the Ethiopic መዐንቅ፡ on p. 590).

New in the code: catchwords dropped automatically (`entry.drop_catchwords`; 6 on these pages),
`(^{6})` and `^{(ᵇ)}` note-mark forms normalized or listed instead of applied, `names_candidates.py`
and 43 new rows in `names.json` (Kimchi, Ibn Ezra, Maimonides, Avicenna, the Fathers...; the 12
earlier chapters re-finished with them at no cost), 40 more Bible-book abbreviations. The page QA
found three misread margin column numbers (pp. 535, 557, 567), read on the scan and fixed;
col. 34 is not printed on pp. 567-568.

## Where the money goes now (one chapter, 22 pages)

| Step | Model | Cost | Share |
|---|---|---|---|
| OCR | Opus 5.5 @low, sync | $1.90 | 31% |
| Second reader | Gemini 3.8 Flash @low, sync | $0.29 | 5% |
| Image judge, one request per line (352 lines) | Opus 5.5 @low, sync | $2.47 | 40% |
| Translation | Opus 5.5 @medium, sync | $1.56 | 25% |
| **Total** | | **$6.22** | |

## What works

1. **OpenRouter Batch API** (`:batch` models, 50% price, median wait about 7 minutes; new
   `orbatch.py`). Same model, so the same quality. For text it works now (translation). For images
   it needs **public image URLs**: OpenRouter rejects base64 images in a batch, on
   `/v1/chat/completions` and on `/v1/messages`. The MDZ IIIF crop URLs work in principle, but MDZ
   takes 4–23 s per crop, and the providers time out (OpenAI always; Anthropic and Google on many
   requests). So the image steps need a fast host (see the question below).
2. **Compact OCR output** (`ocr.py --compact`): blocks without language runs (the runs are not used
   after `vote.py`). Opus output tokens −23%; gold pages: 16 word errors against 19, the same kinds.
3. **Translation at lower cost** (4 chunks of the pilot, compared with the pilot chunks):

   | Model | Cost (batch) | vs. pilot | Rule check | Reading |
   |---|---|---|---|---|
   | Opus 5.5 @medium (pilot, sync) | $0.656 | — | all kept | — |
   | Opus 5.5 @medium | $0.426 | −35% | all kept | = pilot |
   | **Opus 5.5 @low** | $0.193 | **−71%** | all kept | = pilot; drops some `<i>` (*Arabs*, *Hebrew*) and one τοῦ |
   | **GPT-6.1 Sol @medium** | $0.075 | **−89%** | all kept | accurate; more literal with abbreviations (*Supplemm. ad T. 3*), "p. 159–60" |
   | Gemini 4 Argon @medium | $0.067 | −90% | all kept | accurate, but Arabic transliterations with full case endings (*wa-smu l-munāfiqi*), ʿalā for علي |
   | Sonnet 5.5 @medium | $0.097 | −85% | **fails**: 19 of 76 Arabic runs without transliteration, "Palestine" in a note | — |

   Arabic transliterations equal to the pilot (chunk text-10, 53 runs): Opus @medium again 36,
   Opus @low 36, GPT-6.1 Sol 35, Argon 21. So two Opus runs differ as much as Opus and GPT-6.1 Sol.

## What does not work (tested)

- **Gemini 4 Argon as the main OCR.** On the gold pages as good as Opus (0.2% CER, 12 word errors
  against 19) at $0.019 a page sync ($0.0095 batch). But on the whole chapter, after the full
  second reading and vote, 77 words still differ from the reviewed text (Opus before the vote: 39):
  punctuation, Greek iota subscripts and accents, Hebrew words (מהם for מב״ח), Arabic (جحره for
  حجره, tatweel). It also drops 3 of 17 margin column marks. The judge costs the same ($2.40), so
  the saving is only on the OCR.
- **One judge request per page** (all lines of a page in one request): half the cost, but Opus
  then follows the MDZ reading more often (ולדות→ולרות, *majus*→*majur*, οὐδὲ→ἐδὲ: all wrong).
- **Cheaper judges** (one request per line, 125 hard lines): GPT-6.1 Sol, Gemini 3.8 Flash, Gemini 4
  Argon and Sonnet 5.5 all miss known printer's errors (וחחול, *Seholia-*, *alphenet*, نشر) or
  follow MDZ. Flash is also the second reader, so it cannot be the judge.
- **Leaving out MDZ-only flags** (half of the judge lines): these find the printer's errors that
  every model "corrects" (וחחול, *Seholia-*, *alphenet*, -θαι). Keep them.
- Flags that the vote never changes (ου/ε, ف/غ, note-mark format): only 15 of 352 lines.

## Projected cost of one chapter

| Plan | OCR | 2nd reader | Judge | Translation | Total | Saving |
|---|---|---|---|---|---|---|
| Now | 1.90 | 0.29 | 2.47 | 1.56 | **6.22** | — |
| A. No image host: compact OCR, translation Opus @low batch | 1.52 | 0.29 | 2.47 | 0.46 | **4.74** | −24% |
| B. With image host: all steps in batch, translation Opus @low | 0.77 | 0.14 | 1.23 | 0.46 | **2.60** | −58% |
| C. As B, translation GPT-6.1 Sol @medium | 0.77 | 0.14 | 1.23 | 0.18 | **2.32** | −63% |

Not tested yet: a shorter judge prompt with only the rules for the scripts of the line (the text
part of the prompt is larger than the image part; maybe −15% on the judge).

## Code changed (not committed)

- `orbatch.py` (new): submit, poll and read an OpenRouter batch; resumes from `logs/batch_*.json`.
- `ocr.py`: `--batch`, `--compact`, `--image-url` (IIIF crops of the same boxes), `--batch-log`.
- `judge.py`: `--tag`, `--subset`, `--run`, `--batch` (Messages format; blocked by the base64 rule).
- `judge_page.py` (new, test only): one judge request per page.
- `check.py`: `--run` (suffix of the check CSV, for another main OCR).
- `vote.py`: `--judge`, `--skip-mdz-only`.
- `translate.py`: `request_body()` and `parse()` split out of `translate()`, for batches.
- Test scripts and the translation outputs in `costtest/`; test outputs in `data/ocr/*+batchc`, `*+syncc`, `data/fix/*.judge.*.jsonl`.

## Tranche 3 (11-Nov-2026): Part 2, Book 1, chs. 8-13 (58 new pages, pp. 591-648; p. 648 for the join)

| Step | Model | Lines / pages | Cost | Minutes |
|---|---|---|---|---|
| Fetch (scans and MDZ hOCR) | none | 58 | $0 | 4 |
| OCR, compact | Opus 5.5 @low batch + Flash 3.8 @low sync, 4 workers | 58 + 58 | $0.42 for Flash; Opus is in the next line | 6 |
| Image judge (and the Opus OCR batch) | Opus 5.5 @low, batch | 967 lines | about $5.5 together | 10 |
| Translation, 6 chapters in parallel | Opus 5.5 @low, batch | 6 batches | $1.50 | 10 |
| **Total** (key spend, $28.19 to $35.59) | | | **$7.40** ($0.128 a page) | 30 |

First run of `tranche.py` (one command for fetch to review crops, one for translation and site).
Flash sync with 4 workers was done before the Opus batch: the OCR stage took 6 minutes against 35.
The check flagged 1,480 words, 613 of them Greek (Aristotle, Aelian, Pollux), which is why the judge
did not get cheaper. The scan check of 238 items (66 + 90 + 82) was done by subagents for groups A
and B; group C stopped at 25 items (spend limit of the Claude account) and was finished in the main
session. Result: 69 changes confirmed, 13 undone (the ȣ ligature again, an alif seen in the lead-in
stroke of ج and خ, three times قارية), 34 proposals accepted, 22 corrections from the print
(misprints kept: *Peientibus*, ὑπερητεῖν, ἀναιθησίᾳ, ἐλολυγὼν). A smear over the left margin of
pp. 595, 597 and 613 in the scan hides the line starts: 35 words were restored from the letters that
show and the sense (`entry.FIXES`, marked). 18 items stay unsure
(`logs/review/*/decisions.tsv`).

New in the code: `tranche.py` (with the cost per paid step from the key's spend), `banned.py`
(English against the fixed terms, no model call), the φ/Φ rule in `vote.py` and the judge prompt,
Chronicles, Sirach and Baruch in the Bible abbreviations ("Eccles. XI, 31" is Sirach when the verse
does not exist in Qohelet), 7 new rows in `names.json`.
