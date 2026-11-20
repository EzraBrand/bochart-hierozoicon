# Reading the Syriac: tests of 20-Nov-2026

Syriac is the weakest script of the edition (GitHub issue 4; the blog draft on right-to-left scripts). The voted
OCR of vols. 2-3 has only 331 Syriac words on 116 pages: most are single words or short quotations inside a Latin
line; a few are long blocks (vol. 3 p. 283: 14 and 10 lines; p. 345: 5 lines). These tests ask which method reads
the Serto type of the Leipzig edition best. Scripts: `syriac_lab.py` (short items), `syriac_block.py` (long blocks),
`peshcheck.py` (Peshitta check); results in `logs/syriac/` (not in git).

## Test set

50 printed lines with a known answer (`uv run syriac_lab.py items`):

- 21 Peshitta quotations that `peshcheck.py` places in the Peshitta with a fuzzy score of 85 or more (the answer is
  the ETCBC Peshitta text; Bochart's edition sometimes differs, so this answer is approximate);
- 28 Syriac corrections that the scan checks of tranches 1-10 wrote into `entry.FIXES` (the hard cases: the
  pipeline had them wrong);
- the 4 words of issue 4 (p. 207), read on the scan.

## Results on short items (character error rate on consonants; words right)

| method | all items | Peshitta items | hard items (FIXES) | cost of 50 lines |
|---|---|---|---|---|
| voted page OCR (the pipeline) | 22% (58/105) | 9% (41/57) | 34% (17/44) | — |
| Opus 5.5 low, line crop | 34% (47/105) | 34% | 31% (20/44) | $0.73 |
| Opus 5.5 low + a Serto letter guide | 36% | 32% | 39% | $0.80 |
| Gemini 4 Argon + guide | 41% | 40% | 43% (20/44) | $0.14 |
| Gemini 3.8 Flash + guide | 46% | 41% | 48% | $0.73 |
| GPT-6.1 Sol + guide | 53% | 51% | 55% | (not reported) |
| Sonnet 5.5 + guide | 66% | 69% | 63% | — |
| Tesseract 5.4, `syr` (tessdata_best) | 87% | 89% | 86% | free |

The Peshitta items favour the pipeline, because they were found by matching the pipeline's own text. The letter
guide did not help. Each reader gets different words right, so the readers were combined (`logs/syriac/combine.py`;
each reader's word is the one nearest to the OCR word being re-read, so the answer is not used):

| words of the hard items (48) | right |
|---|---|
| the pipeline | 17 |
| a majority of the pipeline and 5 line re-reads | **27** |
| the same, words in the Peshitta first | 27 |
| any reader has it (upper bound) | 28 |

On the 57 words of the Peshitta items the majority is not worse than the pipeline (42 against 41), so the vote does
not damage words that were right.

## Long blocks: vision models do not read them

Rosenmüller copied the left block of vol. 3 p. 283 from Barhebraeus, *Chronicon Syriacum*, ed. Bruns and Kirsch
(Leipzig 1789), vol. 2 (the Syriac text), p. 134. archive.org has that volume (item `ChroniconSyriacum`, file
"Chronicon_Syriacum 2", leaf 503 = p. 134; the pages are numbered backwards from the end). Its image is 3898 × 5040
px, about twice the resolution of the MDZ scan, and the type is a Serto very like Rosenmüller's. No Unicode text of
the chronicle was found (the archive.org OCR of Bedjan's edition is not Syriac letters).

Both prints were cut into lines (`syriac_block.py lines`) and each line was read by four models. If a model can read
Serto, its readings of the two prints of one text must agree, and the four models must agree with each other on the
1789 page. They do not: the four models agree on **3-6% of the words** of the 1789 page (21 lines), and each model's
reading of Rosenmüller's block agrees with its own reading of the 1789 page on 2-4% of the words. The models produce
fluent Syriac that is not the print. Cost: $2.34. The same result was found independently by the ETCBC in
October 2026 ("Digitising printed Syriac editions with AI"): vision LLMs at 65-71% character error on Serto and East
Syriac print.

The block stays "not transcribed". A reader of Syriac can now check it against the 1789 print (link above), which is
much clearer than the MDZ scan.

## What is now in the pipeline

- `peshcheck.py` (free): every run of two Syriac words or more is placed in the Peshitta (ETCBC plain text, Old
  Testament, in `data/peshitta/`, gitignored) and compared word by word; report only, as `biblecheck.py` for the Hebrew.
  On vols. 2-3 it placed 40 runs; 25 have a word that differs (many are Bochart's other editions, some are OCR errors).
- In tranche 11 the Peshitta was the guide for the 5 lines of Eccl 10:1 on p. 345 and for ܪ̈ܗܛܢܐ on p. 399.

## Next steps, in order of promise

1. **A dedicated Syriac OCR model.** Beth Mardutho's Qoruyo models for Kraken include one for printed Serto
   (recognition: doi 10.5281/zenodo.17406676; segmentation: 10.5281/zenodo.17406625). In the ETCBC test a general
   model (PP-OCRv6 medium, through eScriptorium) read a Serto print page at 7.7% character error, against 19% for
   Tesseract and 65-71% for vision LLMs. Kraken runs locally (a Python 3.12 environment); its install was not done
   on 20-Nov-2026 (it needs the owner's approval for new packages outside the project).
2. **The Syriac re-read vote as a pipeline step**: re-read each line with Syriac on it with 4-5 models and take the
   majority per word (above: 17 → 27 of 48 hard words). About $0.05 a line; about 30 lines a tranche.
3. **Two prints of one text.** For a long quotation, find the source edition (as for p. 283) and read both: an OCR
   model that agrees with itself on two prints is right with high probability. This is the check for step 1.
4. Not useful: Tesseract `syr`, the letter guide in the prompt, a Peshitta word list as a tie-breaker (no gain over
   the vote), Sonnet.
