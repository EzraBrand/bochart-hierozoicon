# Notes for agents working on this repository

How the pipeline runs is in [README.md](README.md) (`tranche.py` since 11-Nov-2026); why these
models, in [COST_TEST.md](COST_TEST.md); the translation rules, in
[TRANSLATION_RULES.md](TRANSLATION_RULES.md). The owner checks each deliverable; stop and report
after each one. Commits to this repository are allowed without asking (standing OK, 01-Nov-2026).

Lessons that cost a run: run `mdz_ocr.py` right after `fetch.py sample` (a page without the MDZ
reader gets no judge lines); the models "correct" the print toward the expected word, so MDZ-only
flags are kept (they find the printer's errors); type quirks the judge gets wrong: the ȣ (ου)
ligature read as ε, the lower-case φ that looks like Φ, ד/ר, ذ/ن, قلي read قلى, the lead-in stroke of ج/خ read as an alif (عجر, السخي). `ACCEPT` in `vote.py` applies
only to "MDZ only" items: a reader's APPLY on another kind of review item, and every word with `[?]`,
needs a pair in `entry.FIXES` (grep `la.md` for `[?]` before translating). A page number written twice in
the `FIXES` literal keeps only the second list (`entry.py` now stops at import when that happens). Do not
edit `entry.py` while `tranche.py translate` runs. Write edit scripts with a file tool, not a shell heredoc
(the heredoc halves backslashes). The Greek σθ ligature looks like a θ with a loop in front: MDZ and the
judge drop the σ (δυσθαλπής, ἐσθίομεν, αἰσθήσει); keep it. The scan check runs well in the main session
from contact sheets (`logs/sheets_t4.py`: 8 line crops per image, 4 images per call; 214 items in about an
hour: by the clock it is nearer 10 to 15 minutes for 200 items).

Tranche 5 (13-Nov-2026): the MDZ OCR can miss a chapter head (`find_chapters.py` did not show chs. 22 and
23): after the OCR, grep the Opus text for `CAP.` before `entry.ENTRIES` is written. In Hebrew, ו/ז, ד/ר,
ח/ת and י/ו look alike and all three readers can agree on the wrong letter, so the vote sees nothing: the
check is Bochart's own romanization and Latin next to the word (*zana* for a printed-looking ונה is זנה).
`spotcheck.py` lists these (kind `quote`); read each on the scan (`logs/hebcrops_t5.py`) before a change,
and do not "correct" a letter against the romanization (two such corrections of tranches 1-2, צרק for *tsuk*
and מרת for *mensura*, were taken back). Corrections of the English go into the cached chunks
(`logs/patch_en_t5.py`), not into `en.json`, which the next run writes again. `entry.py NAME --batch`
translates again every chunk whose Latin changed: to run only the fixed steps, call `translate.finish`
(`logs/refinish_t5.py`). The owner reviews the Hebrew in `docs/hebrew.html` (`concordance.py`).

Tranche 6 (14-Nov-2026): OpenRouter refuses a batch whose cost ESTIMATE is above the key's balance (HTTP
402). The estimate comes from `max_tokens` and is about 5 times the real cost (judge batch of 939 lines:
estimate $18.32, real cost about $4). `orbatch.run_batch` now sends such a batch in parts, one after the other
(state files `logs/batch_NAME.partKofN.json`); nothing to do by hand. To keep one batch, the key needs a
balance of about 5 times the step's real cost. Two free Hebrew checks run in code after the vote and before the
translation: `uv run hebcheck.py CHAPTER ...` (Bochart's romanization against the letters) and
`uv run biblecheck.py CHAPTER ...` (quotations against the Masoretic text; `biblecheck.py fetch` once per
machine, it needs `gcloud`). Both are report-only: read each row on the scan (`uv run hebcrops.py NAME
PAGE:WORD ...` writes sheets to `logs/review/heb/`). Most rows are not errors: a Latin translation that fits
the pattern by accident, a ketiv, a construct form that Bochart writes on purpose (טלטלת, p. 686), a printer's
form (פטדת, p. 600). On the 44 chapters of tranches 1-5 the two checks found no error that was still open. Other lessons of tranche 6: read `logs/tranche_TAG_qa.log` before the
scan check (a page with a length far below the MDZ text was cut by the crop: pp. 844 and 846); `vote.ACCEPT`
does not apply items of the kind "not similar", so look for each accepted word in the voted text; a FIXES
pair that spans a printed line needs the `\n` of the page text; `logs/linecrop.py PAGE "Latin words" OUT.jpg`
crops any line of a page for a look. The scan check of 194 items took about 45 minutes from contact sheets
(`logs/sheets_t4.py`, group folders named `T6A`: a plain `A` writes over the folder of an older tranche).

Tranche 7 (15-Nov-2026, vol. 3 pp. 1-124): two OpenRouter batches never started (in progress for hours; no cancel call;
24 h window). Rules since then: (1) before a tranche, send a test batch of about 5 pages; if it is not back in 10
minutes, run the whole tranche with synchronous calls and send no batch at all, because a pending batch holds its
estimate (about 5 times its cost) against the key limit and the account's in-flight budget, and synchronous calls are
then refused with HTTP 402. (2) Stop waiting for a batch after 35 minutes. (3) A synchronous tranche of 125 pages costs
about $29 and needs about $35 of free account credit and key limit; tell the owner the balance before the start. (4)
The judge has about 14 lines a page (1,735 lines for 125 pages at $0.007): the batch packs two lines in a request, so
its request count is half of that. (5) Synchronous workers: `ocr.py` 5 workers, 10 minutes for 125 pages; `judge.py` 8
workers; `entry.py NAME --effort low` for 5 chapters at a time, 10 minutes for 16 chapters. Do not let a chain go on to
`vote.py` while judge lines are missing: loop until a pass has no FAILED line. (6) Sort the review items with
`logs/triage_t7.py` before the scan check and write the verdicts with a script like `logs/decisions_t7.py`. (7)
`logs/open_t7.py VOL FIRST LAST` lists every `[?]` and every page whose notes and marks do not match: run it before the
translation. (8) Medial ف, ق and غ: the readers gave غ for ف five times in one chapter (الخغاش); the romanization
decides. (9) `logs/linecrop.py` matches a short line by accident: give it a long phrase from the MDZ text.

Tranche 8 (16-Nov-2026, vol. 3 pp. 125-193, Book 3 chs. 1-10): the test batch (4 pages) was not back in 10 minutes, so
everything ran synchronously with `logs/prepare_sync_t8.sh FIRST LAST` (mdz_ocr, Opus and Flash OCR, check, judge loop,
vote, qa: 15 minutes for 69 pages) and `entry.py NAME --effort low`, 5 chapters at a time. One hour for the tranche,
$0.230 a page. The owner's rule (16-Nov-2026): he would rather pay the synchronous price than wait for hours; budget of a
session $30 at most. Lessons: (1) a batch that is "stuck" does complete hours later and is billed, so a test batch costs
its price in any case: keep it at 4 pages, and collect its pages the next day with the same `--batch-log` name. (2)
`--finish-only` reads `en.raw.json`, not the chunks: after `logs/patch_en_t8.py` run `entry.py NAME --effort low` (cached
chunks, no cost). (3) A FIXES pair for Greek typed by hand can miss the text for a different Unicode form: take a
short, plain part of the word (`'ρπης' -> 'ρπηστ'`). (4) `logs/ctx_t8.py PAGE PHRASE` prints the voted text around a
phrase: call it for one page at a time, or the page of a hit is not known. (5) Words of two or more in Syriac or Arabic
inside a Latin line can come out in the order of the eye (p. 159, twice); the vote lists them as "not similar" pairs
that swap. (6) `no_id` skips the first n uses: give 99 when every use in the chapter is another person or work. (7) The
next tranche: Book 3 chs. 11-14, pp. 194-250 (57 pages; pp. 194-211 are fetched), then Book 4 (the insects) from p. 251.

Tranche 9 (17-Nov-2026, vol. 3 pp. 195-271, Book 3 chs. 11-14 and Book 4 ch. 1): synchronous again, $0.226 a page. The
first session stopped at the Claude usage limit right after `prepare_sync_t9.sh`; the next session found the state from
the logs and the untracked files (`git status`, `ls -t logs`) and from the old transcript (`~/.claude/projects/.../*.jsonl`).
Lessons: (1) `draft_entries.py` takes the volume as the first argument (`draft_entries.py 3 194 250 --book "Part 2, Book
3"`), not `--vol`. (2) A margin column that the printer got wrong (p. 221: "248" for 428) gives a wrong `first_col` and
column range in the draft: read `qa.log` ("margin [248] after 427") first, and correct the mark with a FIXES pair on
`⟦p. 248⟧`. (3) The last chapter of a book ends with `"end": r"LIBER QUARTUS"` and the page of the next book's head in
`pages`. (4) The spot-check's page number can be one off (p. 232 for p. 233): grep the voted pages for the phrase. (5)
`logs/linecrop.py` matched the wrong lines for most spot-check rows (fuzzy match of short phrases): give it long MDZ
phrases. (6) The next tranche: Book 4 (the insects) from ch. 2, vol. 3 p. 271 (chs. 2-5 run to p. 319, ch. 6 begins on p. 320; pp. 272-282 are
fetched; chapter heads in `logs/find_chapters_t9.log`).

Tranche 10 (18-Nov-2026, vol. 3 pp. 272-326, Book 4 chs. 2-6): synchronous, no test batch, $0.211 a page, about 50 minutes (10:25 to 11:14).
Lessons: (1) a long block in Syriac (10 lines or more) is not read by any model: Opus leaves `[?]`, and a re-read of the
crop alone gives fluent text that is not the print (Opus at high effort returned nothing in 6,000 tokens; low effort
invented). Do not use it; mark the block with a FIXES pair (`[Syriaca, versus XIV, hic non transcripta]`). (2) Opus can
write an Arabic line in Syriac letters (p. 280); the vote lists the words as "not similar". (3) `hebcheck.py` and
`biblecheck.py` found 2 more ד/ר errors on a page where the vote had flagged 3; after a ד/ר FIXES pair, grep the page
for the other forms of the root. (4) A Greek verse quoted twice: read the clearer copy before a verdict (p. 307 against
p. 309). (5) `logs/linecrop.py` takes `3:PAGE` for vol. 3 and the MDZ spelling (long s as f). (6) A shell heredoc
halves `\n` in a FIXES pair (entry.py would not import): write such edits with a file tool. (7) The next tranche: Book 4
from ch. 7, vol. 3 p. 326 (John the Baptist's locusts; ch. 8 p. 334, ch. 9 the fly p. 341, ch. 10 p. 352, ch. 11 the bees
p. 365, ch. 12 honey p. 374, ch. 13 wasps p. 402, ch. 14 the gadfly p. 417; heads in `logs/find_chapters_t10.log`).

## Plan for the next tranche (14-Nov-2026, agreed with the owner)

Where the time goes, from the logs of tranche 6 (1 h 20 min for 83 pages): waiting for the batches about 50
minutes (OCR 7, judge 13, translation 15, plus the failed submits), the scan check about 10, the rest is
chapter definitions, joins, corrections and notes. Take times from the log timestamps and the commit, not from
an impression: the README had "about 3 h" for tranches that took 1 h to 1 h 35 min.

- **Larger tranches: 120 to 130 pages**, ending at a chapter end. The fixed work is the same for 80 or 130
  pages, and the batch split removed the balance limit. With about $25 on the key nothing is split.
- **Overlap the batches.** Start `tranche.py prepare` for tranche N+1 as soon as the OCR of tranche N is voted,
  and do the scan check of N while it runs. `SAMPLE`, `ENTRIES` and `DOCS` must then hold both tranches.
- **Generate the fixed work.** A script that writes the `ENTRIES`, `DOCS` and README rows from the chapter heads
  in the Opus OCR (pages, start and end patterns, `first_col`, column range, the Latin summary as a draft
  title); the agent writes only the subject and the fixed terms.
- **Before the scan check:** read `logs/tranche_TAG_qa.log` (cut pages, note marks), then
  `uv run decisions_stats.py` shows which kinds of item are confirmed almost always (Greek accents with Flash:
  94%; Latin with Flash and MDZ: 97%; Hebrew with both: 100%); look at those last, and fast.
- **After `apply_review.py`:** check that each accepted word is in the voted text; run `hebcheck.py` and
  `biblecheck.py`; after the translation `banned.py` and `spotcheck.py`, and read its rows of kind `quote`
  and `meaning` on the scan (`logs/linecrop.py`).
- **The volume parameter and a new key** come first (see Project management below).
- **Do not replace the scan check with a model call.** Tested 14-Nov-2026 (`arbiter_test.py`, table in
  COST_TEST.md): a second Opus call with all the readings and the type notes agrees with the scan check in
  69% of the items, less than the plain vote (80%). `decisions_stats.py` shows the kinds that are safe.

## Ideas backlog (11-Nov-2026, after tranche 3; updated 14-Nov-2026, in tranche 6)

Low-effort improvements, not yet done. Pick from the top; tick off here when done.

### Pipeline and cost

- [x] **Greek accent pre-filter for the Flash flags.** Measured 12-Nov-2026 and not done as written: a
      stripped key for Flash removes only 15 of the 1,467 flags of tranche 3. The Greek noise comes from MDZ
      (367 Greek flags where Flash agrees with Opus); see the next item. Tranche 3 flagged 613 Greek words, most
      of them accent differences. Compare Greek on a stripped key for Flash (as f/s is folded for
      MDZ) and let only MDZ raise accent flags. Biggest cost cut for the bird books.
- [x] **Rule list before the judge for the known MDZ quirks.** Done 12-Nov-2026 for Greek (`check.is_mdz_quirk`,
      kind `quirk`): Flash agrees with Opus and MDZ differs only by an accent, ε for the ου ligature or Φ for φ.
      133 of 1,555 flags in tranche 4 were not judged. The price, from tranche 3: about 2 real accent changes
      (an iota subscript) per tranche are not found. Still open: the same for Latin (f/s is folded already).
      Flags where Flash agrees with Opus
      and MDZ differs only by f/s, hamza, ى, a dropped accent or glued punctuation go to a rule,
      not to Opus. Done for Latin 13-Nov-2026 (`check.is_latin_quirk`: in for m, tt/ft for ct/st, fl for ss,
      S for s, l/J for I; 88 flags in tranche 5; accents and other capitals are still judged). Keep the MDZ-only flags that change a letter: those find the printer's errors.
- [x] **One translation batch per tranche.** Done 12-Nov-2026 (`entry.batch_all`; custom ids take only
      `[A-Za-z0-9_-]`). `tranche.py translate` submits one batch per chapter;
      collect all chunks and submit once.
- [x] **Cost per step in `tranche.py`.** Done 11-Nov-2026 (`tranche.spend`). The batch results carry no cost; read the key's spend
      (`/api/v1/key`) before and after each step and print the delta, so the README cost column
      needs no hand calculation.

### Quality

- [ ] **A small gold set per tranche.** One hand-checked half page per tranche (one Greek-heavy,
      one Arabic-heavy) to see if the error rate drifts as the scripts change. The three gold
      pages of the pilot cover only Book 3.
- [ ] **Table of the readers' disagreements with the judge, across tranches.** The readers already
      report them; collected, they say what to add to the judge prompt next (the φ/Φ and ȣ rules
      came from exactly this).
- [x] **Translation spot-check.** Done 13-Nov-2026 (`spotcheck.py`, Gemini Flash, report only; about a third
      of its rows are real). Nothing checks the English against the Latin. A cheap batch pass
      with another model (GPT or Gemini) that flags sentences where the English drops a clause, a
      hedge or a number. Report only; no rewriting.
- [x] **Banned-words grep after translation.** Done 11-Nov-2026 (`banned.py`; counts the English word against its Latin/Greek sources per paragraph). Each chapter sets its own fixed terms (dove, never
      pigeon; deror stays deror). A grep of the English for the banned words (pigeon, coney, hyrax,
      rock badger, swallow in the deror chapter, crane in the agur chapter) catches slips for free.

- [x] **A ו/ז pass over the Hebrew.** Done 14-Nov-2026 in code, without a judge call, and for all the
      look-alike letters: `hebcheck.py` (the romanization must fit the letters; "swap" = it fits only when one
      letter is changed for a look-alike) and `biblecheck.py` (every string of two words or more is placed in
      the Tanakh by its look-alike classes and compared letter by letter). The owner's QA found ו for ז four
      times in tranches 1-4.
- [ ] **The same check for the Targum, the Talmud and the Septuagint.** `biblecheck.py` knows only the Hebrew
      Bible. The Sefaria export has Onkelos, Jonathan and the Bavli (`gs://sefaria-export/json/...`); the same
      index over those texts covers most of the Aramaic. For Greek, a Septuagint text (Rahlfs, public domain)
      would be a reader for the accents that MDZ gets wrong.
- [ ] **Use the scan-check decisions as data.** `logs/review/*/decisions.tsv` of tranches 2-6 hold about 1,100
      verdicts. Count, per kind of item (script, kind of difference, who supports the change), how often the
      change was confirmed. A kind that is confirmed 98% of the time can be applied by rule, and the scan check
      (1-2 hours of each tranche, and the step that reaches the Claude usage limit) becomes shorter.
- [ ] **Mark the uncertain readings in the reading edition.** The "not certain" words are only in the README.
      A table `data/uncertain.json` (page, word, why) from the `UNSURE` rows and from `entry.FIXES` comments,
      shown as a dotted underline with a tooltip, tells the reader at the place itself.
- [x] **An override for a wrong identification.** Done 14-Nov-2026: `"no_id": {"Elias": 99}` in an entry
      of `entry.ENTRIES` leaves the first n uses of the name without the identification (`names.identify`).
      Was: "Jonathan" (the son of Saul, p. 751) gets the tooltip of
      the Targum; `names.identify` has no way to say "not here".

### Reader-facing

- [x] **Chapters grouped by book on the index page, in the order of the book.** Done 14-Nov-2026
      (`build_site.BOOK_NAMES`, `done_docs`); the chapter's thesis is the `sub` line. A new book needs a row in
      `BOOK_NAMES`.
- [x] **Index of Bible passages.** Done 14-Nov-2026 (`passages.html`, from the SBL references in the English).
      Still open: the same for rabbinic citations (tractate and folio) and for classical authors.
- [x] **Search.** Done 14-Nov-2026 (`search.html`; `docs/search-en.json` and `search-la.json`, one row per
      paragraph; accents and points are folded). The snippet shows the folded text.
- [x] **Flags on the Hebrew QA page.** Done 14-Nov-2026: a tick per row, kept in the browser, and "Copy the
      flagged rows" gives a tab-separated list to send.
- [x] **Link previews and title.** Done 14-Nov-2026 (Open Graph tags; "pilot" removed from the title). No
      preview image yet: a 1200x630 image of a page spread would make the card stronger.
- [x] **Wiktionary card on a selected word.** Done 15-Nov-2026 (the "Wiktionary card" block in the `JS` of
      `build_site.py`). The comparison with the Scriptorai reader and how each feature works are in
      [READER_IDEAS.md](READER_IDEAS.md).
- [x] **Scan crop of the paragraph, "correct" link, text size.** Done 15-Nov-2026 (issue 1). The build prints
      "scan crops: N placed by their text, M by line count"; after a new tranche run
      `uv run python logs/scanbox_check.py` and look at the rows it prints (`logs/scanbox_debug.py ENTRY PAGE`
      shows the OCR lines of a page). A large gap or overlap is a paragraph placed on the wrong lines.
- [ ] **Check the two-column layout on a phone.** Not looked at since the pilot.

- [ ] **Names and abbreviations pages sorted by basis**, "guess" and "general knowledge" first, so
      the owner's review takes ten minutes.
- [ ] **The chapter's thesis on the index page.** One short paragraph per chapter (the `about` text
      in `entry.py` exists already).
- [ ] **"See also" per chapter** to the matching Lewysohn entry and fact-check claim (the crane and
      the swallow overlap with both): one dictionary in `build_site.py`.
- [x] **Anchors for the columns of 1663.** Done 14-Nov-2026: `chapter.html#col198`, `#pg787` (a page of
      Rosenmüller) and `#p12` (a paragraph; the ¶ at its end). A paragraph number changes if the Latin of the
      chapter is joined again in another way; page and column anchors do not.

### Project management

- [x] **Make the volume a parameter.** Done 15-Nov-2026 (`--vol`; vol. 3: printed page = canvas - 22). Was: Volume 2 is complete with tranche 6.
      Part 1, Books 1-3 chs. 1-32 are in vol. 1 and the rest of vol. 2 (pp. 1-408); Part 2 goes on in vol. 3.
      `tranche.keys`, `fetch.SAMPLE`, the `v2-` file names, `find_chapters.py` and "printed page = canvas - 16"
      assume vol. 2 (`VOL_IDS` in `build_site.py` already has the three ids). Find the canvas offset of the
      other volume first (it has front matter of another length), then give `tranche.py` a `--vol`.
- [x] **A new OpenRouter key.** Done 15-Nov-2026 (limit $90, expires 22-Nov-2026). Was: the project key expires on 15-Nov-2026. Ask for a balance of about $20 or
      more for a tranche of 80 pages (5 times the largest step), so that no batch is split.
- [ ] **Send the parts of a split batch at the same time where the balance permits.** `orbatch.run_batch`
      sends the parts one after the other. For 3 or more parts it can send as many together as fit under the
      balance (the estimate of a part is the refused estimate divided by the number of parts). With 2 parts
      there is nothing to gain: both together are the refused batch.

**Tell the owner about the key balance (owner's instruction, 14-Nov-2026).** `tranche.py` prints `NOTICE FOR
THE OWNER` at the start when the key has less than about $20, and `orbatch` prints `estimate ... is above the
balance` when a batch is refused and split. When either line shows, tell the owner in the next message: the
balance, what was refused or split, and the waiting time it costs. Do not only work around it.

- [x] **Tranche table in the README** Done 11-Nov-2026. (date, pages, cost, minutes, review items, changes). The three
      tranches are in prose now; a table shows the trend.

Done: the blog post on the project was published 10-Nov-2026:
https://www.ezrabrand.com/p/reading-bocharts-hierozoicon-with
