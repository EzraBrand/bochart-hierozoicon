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

The vision models cannot transcribe the block; Kraken can (next section). A reader of Syriac can check the result
against the 1789 print (link above), which is much clearer than the MDZ scan.

## Kraken with the Qoruyo Serto model: it reads the blocks

Installed by the owner on 20-Nov-2026 in `C:\Users\ezrab\Ezra Brandt\Claude\syriac-ocr\` (Python 3.12 venv, kraken 7.1.1;
on Windows `coremltools` builds from source and works). `kraken get` does not know the Qoruyo DOIs ("No metadata
found"); the two model files were downloaded from Zenodo directly (CC-BY-4.0): `serto_print_best_02.mlmodel`
(recognition, record 17406677) and `syr_print_seg03_91.mlmodel` (segmentation, record 17406626). On the line crops of
`syriac_block.py`, with no segmentation (free, about 4 s a line on the CPU):

    .venv/Scripts/kraken.exe -i LINE.jpg OUT.txt ocr -m serto_print_best_02.mlmodel --no-segmentation

The output is in visual order (left to right): reverse the string for logical order.

The two prints of the p. 283 block, each read by one method, aligned on the best-matching stretch of the 1789 page:

| reader | words of the block | the same in both prints | within one letter |
|---|---|---|---|
| Kraken + Qoruyo Serto | 57 | 18 (32%) | 39 (**68%**) |
| GPT-6.1 Sol | 54 | 6 (11%) | 7 (13%) |
| Opus 5.5 | 54 | 4 (7%) | 6 (11%) |
| Gemini 4 Argon | 36 | 2 (6%) | 2 (6%) |
| Gemini 3.8 Flash | 37 | 2 (5%) | 3 (8%) |

Kraken's two readings follow each other word for word (ܒܫܢܬ ܐܨܗ ܕܝ̈ܘܢܝܐ ܐܬܐ ܩܡܨܐ ܦܪܚܐ …, "in the year 1095 of the Greeks
came the flying locust …"), and where one print has a wrong letter the other has the right one (ܩܡܨܐ / ܩܡܬܐ, ܙܪܥܐ /
ܙܢܥܐ). So the block can be transcribed: Kraken on both prints, a word-by-word reconciliation, and a look at the scan
where the two disagree. Done the same day: the left block of p. 283 is now in the text (entry.FIXES (3, 283)); not certain:
no word (ܘܡܣܒܟ and ܘܠܓ̈ܐ were corrected from Bedjan's vocalised edition, p. 128). The right block (the continuator, 10 lines) is still "not transcribed". The block begins at the end of line 0 of the 1789 page (logs/syriac/bk134/kraken.json).

On a mixed line (Latin with a Syriac word in it) Kraken returns almost nothing: the model knows only Syriac. For the
short words it needs a crop of the Syriac word alone (the MDZ hOCR word boxes, or the gaps between words); not tested yet.

## What is now in the pipeline

- `peshcheck.py` (free): every run of two Syriac words or more is placed in the Peshitta (ETCBC plain text, Old
  Testament, in `data/peshitta/`, gitignored) and compared word by word; report only, as `biblecheck.py` for the Hebrew.
  On vols. 2-3 it placed 40 runs; 25 have a word that differs (many are Bochart's other editions, some are OCR errors).
- In tranche 11 the Peshitta was the guide for the 5 lines of Eccl 10:1 on p. 345 and for ܪ̈ܗܛܢܐ on p. 399.

## Next steps, in order of promise

1. **Kraken + Qoruyo for every block of pure Syriac** (above). Next: the right-hand block of p. 283, the continuator, is in Paulus, *Neues Repertorium*, vol. 1, p. 67: find a scan), and
   test Kraken on word crops for the short words. The ETCBC also had good results with a general model (PP-OCRv6
   medium, through eScriptorium: 7.7% character error on a Serto page).
2. **The Syriac re-read vote as a pipeline step**: re-read each line with Syriac on it with 4-5 models and take the
   majority per word (above: 17 → 27 of 48 hard words). About $0.05 a line; about 30 lines a tranche.
3. **Two prints of one text.** For a long quotation, find the source edition (as for p. 283) and read both: an OCR
   model that agrees with itself on two prints is right with high probability. This is the check for step 1.
4. Not useful: Tesseract `syr`, the letter guide in the prompt, a Peshitta word list as a tie-breaker (no gain over
   the vote), Sonnet.
