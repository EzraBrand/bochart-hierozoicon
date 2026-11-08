# Cost test, 08-Nov-2026

Goal: cut the cost of the pipeline a lot, with about the same quality. Test passage: the pilot
chapter (pp. 408–429), because the three gold pages (410, 422, 428) and the reviewed vote give a
measure of quality. Spent on the test: $7.51 (key `bochart-hierozoicon`).

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
