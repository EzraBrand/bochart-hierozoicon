# bochart-hierozoicon

OCR and English translation of Samuel Bochart, *Hierozoicon, sive bipertitum opus de animalibus
Sacrae Scripturae* (London 1663), in the edition of E. F. C. Rosenmüller (Leipzig: Breitkopf,
1793–96, 3 vols.). **Pilot only:** Book III, ch. 33, on the shafan ("non esse Cuniculum").

Same family as [low-flora](https://github.com/EzraBrand/low-flora) and
[lewysohn-zoologie](https://github.com/EzraBrand/lewysohn-zoologie); the code is ported from
lewysohn-zoologie. Companion: [talmud-zoology-factcheck](https://github.com/EzraBrand/talmud-zoology-factcheck),
claim 7 (hyrax/shafan).

## Status (01-Nov-2026)

Step 1 of the pilot: scans, manifest, the MDZ OCR layer and a note on the layout. No model OCR yet.

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
```

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

**A question for the gold rules:** the print has its own dot errors in the Arabic (p. 422 line 23:
مقام is printed with the dot of غ). Lewysohn's rule was "as printed". For Arabic I propose the
same, with a list of printer's errors for the translation step.

## License

The code and everything added in this repository (transcriptions, gold pages, translations and
documentation) are under the [MIT License](LICENSE), © 2026 Ezra Brand.

Bochart's *Hierozoicon* and Rosenmüller's edition are in the public domain; the scans are by the
Bayerische Staatsbibliothek (MDZ), rights statement NoC-NC 1.0, and are not stored here.
