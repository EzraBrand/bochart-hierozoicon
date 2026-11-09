# bochart-hierozoicon

Machine transcription and English translation of Samuel Bochart, *Hierozoicon* (London 1663), a
Latin study of the animals of the Bible, in the edition of E. F. C. Rosenmüller (Leipzig 1793–96).
The text quotes Hebrew, Aramaic, Greek, Arabic, Syriac and a little Ethiopic and Samaritan.

**Read it:** https://ezrabrand.github.io/bochart-hierozoicon/ (Latin and English side by side,
with links to the scans).

Part of a series with [low-flora](https://github.com/EzraBrand/low-flora),
[lewysohn-zoologie](https://github.com/EzraBrand/lewysohn-zoologie) and
[talmud-zoology-factcheck](https://github.com/EzraBrand/talmud-zoology-factcheck).

## Chapters done

| Chapter | Pages (vol. 2) | Text | Cost |
|---|---|---|---|
| Book 3, ch. 33: the *shafan* is not the rabbit but a kind of larger mouse | 409–429 | [Latin](data/entries/shafan/la.md) · [English](data/entries/shafan/en.md) | $6.31 (pilot, with tests) |
| Book 3, ch. 35: the *choled* is not the weasel but the mole | 435–453 | [Latin](data/entries/choled/la.md) · [English](data/entries/choled/en.md) | $2.56 |
| Book 3, ch. 34: the common mouse (*achbar*) | 429–435 | [Latin](data/entries/achbar/la.md) · [English](data/entries/achbar/en.md) | $9.71 for the 10 chapters (74 new pages; tranche 1, 09-Nov-2026) |
| Book 3, ch. 36: the *kippod* is the hedgehog and the porcupine | 454–462 | [Latin](data/entries/kippod/la.md) · [English](data/entries/kippod/en.md) | 〃 |
| Book 4, ch. 1: the *tsab* is the land crocodile | 463–487 | [Latin](data/entries/tsab/la.md) · [English](data/entries/tsab/en.md) | 〃 |
| Book 4, ch. 2: the *anaka*, a kind of stellio | 487–493 | [Latin](data/entries/anaqah/la.md) · [English](data/entries/anaqah/en.md) | 〃 |
| Book 4, ch. 3: the *coach* is the waral | 493–497 | [Latin](data/entries/koach/la.md) · [English](data/entries/koach/en.md) | 〃 |
| Book 4, ch. 4: the *leta*, a venomous lizard | 497–500 | [Latin](data/entries/letaah/la.md) · [English](data/entries/letaah/en.md) | 〃 |
| Book 4, ch. 5: the *chomet*, a sand lizard | 500–503 | [Latin](data/entries/chomet/la.md) · [English](data/entries/chomet/en.md) | 〃 |
| Book 4, ch. 6: the *tinshemeth* is the chameleon | 503–510 | [Latin](data/entries/tinshemet/la.md) · [English](data/entries/tinshemet/en.md) | 〃 |
| Book 4, ch. 7: the *semamith* is the stellio | 510–520 | [Latin](data/entries/semamit/la.md) · [English](data/entries/semamit/en.md) | 〃 |
| Book 4, ch. 8: altars "like tortoises" (Hos 12:12) | 520–523 | [Latin](data/entries/chelonai/la.md) · [English](data/entries/chelonai/en.md) | 〃 |

Open review lists (readings the pipeline did not decide): `logs/vote_v2-408-429.csv`,
`logs/vote_v2-434-454.csv`, `logs/vote_v2-430-433.csv` and `logs/vote_v2-455-524.csv` (column `outcome`),
and for tranche 1 the scan-check answers in `logs/review/*/decisions.tsv` (verdict `UNSURE`); `logs/` is
not in git.

## How it works

1. **Scans:** Munich, Bayerische Staatsbibliothek (MDZ), vol. 2 = `bsb10353454`; printed page =
   canvas − 16. MDZ's own OCR layer (hOCR) is used as a second reader.
2. **OCR:** Claude Opus 5.5 reads each page (as two image halves, at full resolution).
3. **Second reading:** Gemini 3.8 Flash and the MDZ OCR read the page too; every word where they
   differ from Opus is flagged.
4. **Image judge:** Opus looks at a crop of each flagged line and writes what is printed.
5. **Vote:** a word is changed only where the judge agrees with Flash or MDZ. Changes that only
   MDZ supports, and letters that look alike in this type (ד/ר, ف/غ, ذ/ن), are listed for review,
   not changed.
6. **Translation:** Opus translates by chapter, following [TRANSLATION_RULES.md](TRANSLATION_RULES.md);
   code then adds Bible references in SBL form, Hebrew letters for Syriac, the
   [abbreviations](ABBREVIATIONS.md) and identifications of names.
7. **Website:** `build_site.py` writes `docs/` (GitHub Pages).

All model calls go through the OpenRouter Batch API (half price, results in minutes). The batch
takes images only as public URLs, so the crops of a run are put in
[bochart-hierozoicon-crops](https://github.com/EzraBrand/bochart-hierozoicon-crops) and removed
after it. Why these models and not cheaper ones: [COST_TEST.md](COST_TEST.md).

**Known limits:** the models tend to "correct" the print toward the expected word (*caussa* →
*causa*, a printer's error → the right word), which is why the second reading and the vote exist.
Readings were checked on the scan by Claude, not by a specialist in each script; the
identifications of names need a review.

## Running a new chapter

Example: ch. 35, pp. 434–454 (one page before and after, for the joins). Needs
[uv](https://docs.astral.sh/uv/), an OpenRouter key in a text file, and `gh` logged in (for the
crops repo).

```bash
export OPENROUTER_KEY_FILE="path/to/key.txt"
```

0. Find the chapter heads in the MDZ OCR (`uv run find_chapters.py 470 560`). A tranche of
   60–100 pages that ends at a chapter end costs about $10 (09-Nov-2026: $0.13 a page).

1. Add the canvases to `SAMPLE` in `fetch.py`, then fetch the scans and the MDZ OCR:

   ```bash
   uv run fetch.py sample
   uv run mdz_ocr.py
   ```

2. OCR with Opus and Flash (batch):

   ```bash
   uv run ocr.py v2-0434 v2-0435 ... v2-0454 --model anthropic/claude-opus-5.5 --compact --batch
   uv run ocr.py v2-0434 v2-0435 ... v2-0454 --model google/gemini-3.8-flash --compact --batch
   ```

3. Flag, judge, vote, check:

   ```bash
   uv run check.py 434 454
   uv run judge.py 434 454 --batch
   uv run vote.py 434 454
   uv run qa.py 434 454 --main "or-claude-opus-5.5@low+vote"
   ```

   Read the doubtful changes on the scan; add them to `ACCEPT` or `REJECT` in `vote.py`, and run
   `vote.py` again. For a large range, `uv run review_pack.py 455 524 --group B:463-487 ...` writes a
   2x crop and a row per review item and per applied change, for one reader (a subagent) per group.

   Check that the OCR crop did not cut the text: `ocr.safe_box` widens the crop to every MDZ text line
   since 09-Nov-2026 (before, pp. 506, 510, 520 and 524 lost their line ends, and Flash got the same
   cut crops, so only MDZ showed it).

4. Add the chapter to `ENTRIES` in `entry.py` (pages, start and end patterns, subject, fixed
   terms), join the pages and check the joins, then translate:

   ```bash
   uv run entry.py choled --no-translate
   uv run entry.py choled --batch --effort low
   ```

5. Add the chapter to `DOCS` in `build_site.py`, then build the site and empty the crops repo:

   ```bash
   uv run build_site.py
   uv run crophost.py clean
   ```

## Files

| Path | What |
|---|---|
| `data/raw/manifest.json` | the pages used (scans are not in git) |
| `data/ocr/{engine}/` | OCR per page; `or-claude-opus-5.5@low+vote` is the final text |
| `data/gold/` | 3 pages corrected by hand (410, 422, 428), for measuring OCR error |
| `data/fix/` | judge answers and vote decisions |
| `data/entries/{chapter}/` | joined Latin, English, and the cached translation chunks |
| `docs/` | the website |
| `costtest/` | scripts and outputs of the cost test |
| `archive/` | the old, long README of the pilot (OCR tests, layout, gold rules, error tables) |

## License

Code, transcriptions and translations: [MIT](LICENSE), © 2026 Ezra Brand. Bochart's text and
Rosenmüller's edition are in the public domain. The scans are by the Bayerische Staatsbibliothek
München (MDZ), rights statement [NoC-NC 1.0](https://rightsstatements.org/vocab/NoC-NC/1.0/), and
are not stored here.
