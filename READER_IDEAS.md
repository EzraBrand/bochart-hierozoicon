# Reader ideas from Scriptorai (15-Nov-2026)

Notes from a look at the reader of the [Scriptorai Open Esoteric Library](https://scriptorai.org/)
(sample: CCAG vol. II, https://scriptorai.org/works/ccag-2/pages/0027; also its Method page and General
index), compared with the reading edition in `docs/`. The owner's view: their default view is too crowded,
but some features are worth offering as options.

## What Scriptorai does

- **Three panels, each with an on/off switch:** Scan, Text, Line panel.
- **Line-by-line text:** each printed line has its transcription and its English below it.
- **Word meanings** (a switch, off by default): a short dictionary sense below each word.
- **Dictionary card:** a tap on a word shows the headword, the sense, links to LSJ (Logeion) and
  Wiktionary, and the other pages and texts where the word occurs.
- **Line magnifier:** a crop of the scan for the selected line; the line is marked on the full page.
- **"Show where the transcriptions differ":** marks on the scan each line where the three runs did not
  agree. The line panel says "3 transcriptions, identical" or shows the readings.
- **Small items:** "Suggest a correction" (a GitHub issue with book and page filled in), "Share line",
  text size (Smaller / Normal / Larger / Compact), a General index of names and terms (5,931 terms).
- **Pipeline** (their Method page): three runs of one model per page, a fourth call that reconciles them
  and may fix only obvious errors, then a dictionary step that is not an LLM. Cost 8 to 20 cents a page.
- **Dictionary data:** Wiktionary through the kaikki.org extraction (Wiktextract), LSJ and Lewis and Short
  in the Logeion editions, Steingass for Persian, and the Diorisis corpus for the Greek headword table.
  All joined at build time.

A weakness: the headword step makes errors. On the sample page προβολῆς (genitive of προβολή,
"projection") has the headword προβολεύς, "producer, originator", while their own line translation says
"projection". An always-visible gloss can be wrong and look authoritative.

## Decisions

| # | Feature | Decision | State |
|---|---|---|---|
| 1 | Wiktionary card on a selected word | add | done 15-Nov-2026 |
| 2 | Scan crop of the line or paragraph | add, as a switch | open |
| 3 | Uncertain readings marked in the text | add (already in the AGENTS.md backlog) | open |
| 4 | "Suggest a correction" link per paragraph | add, small | open |
| 5 | Text size control | add, small | open |
| 6 | A gloss below each word | no | |
| 7 | Line-by-line layout | no | |
| 8 | Their General index | no (we have names, passages, Hebrew and search pages) | |

Why not 6 and 7: the gloss row is the crowded part, and it needs a headword table that makes errors; the
card on demand gives the same help. Paragraph columns read better for long Latin prose; their layout fits
catalogue entries.

## 1. The Wiktionary card (done)

Code: the block "Wiktionary card" in the `JS` string of `build_site.py`, and the `.wikt` rules in `CSS`.

- With "Look-up on selection" on, one selected word gets a **Wiktionary** button, first in the bar. The
  button opens a card on the page. The old link "Wiktionary (Arabic)" is gone.
- The definition comes from `https://en.wiktionary.org/api/rest_v1/page/definition/WORD`. The API permits
  calls from a browser page (CORS), needs no key, and is called only when the reader taps the button.
- The card shows only the language of the script: Hebrew letters give Hebrew and Aramaic; Arabic gives
  Arabic; Greek gives Ancient Greek; Syriac gives Classical Syriac; Latin letters give Latin in the Latin
  column, and English then Latin in the English column. Without this filter `muris` shows Catalan and
  French first.
- Forms tried, in order, until an entry is found (`forms()`):
  - Hebrew: points and accents removed; then the plural ending (ים, ות) removed; then one or two prefix
    letters (והבכלמש) removed. The ending goes first: שפנים must give שפן, not ש + פנים ("face").
  - Arabic: vowel signs removed; then the article ال; then a prefix letter.
  - Greek: a grave accent becomes an acute; then lower case.
  - Latin: accents removed, æ and œ opened, lower case, j to i, then -que / -ve / -ne removed.
- When the form in the card is not the selected word, the head says "from WORD".
- A form-of entry ("dative/ablative plural of mūs") has the headword as a link; it opens in the same card.
- The text of the API is copied as text nodes; only `i`, `b` and the headword links become elements.
- Footer: a link to the full entry, a Logeion link for Greek and Latin, and the licence line
  (Wiktionary, CC BY-SA 4.0).

Tested 15-Nov-2026 on `shafan.html`, desktop and phone width: `cuniculi`, `muribus` and its headword link,
`Hieronymus`, שפנים, השפן, ארנבת, اليربوع, and "hedgehogs" in the English column.

Known limits:

- **Greek is weak.** Wiktionary has few inflected Greek forms and no entry for rare words
  (χοιρογρύλλιος: none). The card then says so and gives the Logeion link. A Greek headword table (as
  Scriptorai builds from Diorisis) would help, with the error rate shown above.
- The Hebrew and Arabic prefix cut is a guess. The head shows "from WORD" so that the reader can see it.
- The API gives the sub-lines of an "inflection of" entry twice; the card drops the second copy.
- No entry for a construct form or a suffixed form (בשפניהם).

Possible next steps: Sefaria's lexicon API (Jastrow, BDB, Klein) for Hebrew and Aramaic as a second source
in the same card; a build-time table from kaikki.org if the reader must work offline.

## 2. Scan crop of the line (open)

The line coordinates are already in `data/mdz_hocr`, and the images come from the MDZ IIIF server
(`.../iiif/image/v2/bsb10353454_00425/x,y,w,h/full/0/default.jpg`), so no image needs hosting. Idea: a
switch "Scan beside the text"; a tap on the ¶ of a paragraph (or on a page link) shows the crop of those
lines above the paragraph. Needs: a table paragraph to page and line box, written by `build_site.py`. This
is the Scriptorai feature that helps a reader most, and it fits the note "check the scan before you cite".

## 3. Uncertain readings (open)

See "Mark the uncertain readings in the reading edition" in AGENTS.md. Our equivalent of "where the
transcriptions differ": a dotted underline with the reason, from the `UNSURE` rows and the `entry.FIXES`
comments. A switch, off by default.

## 4 and 5. Small items (open)

- A "Suggest a correction" link at each ¶: a GitHub issue link with the chapter and the `#p12` anchor in
  the title.
- Text size: three steps, kept in the browser like the other switches.
