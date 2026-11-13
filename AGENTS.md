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
hour).

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

## Ideas backlog (11-Nov-2026, after tranche 3; updated 13-Nov-2026, after tranche 5)

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

- [ ] **A ו/ז pass over the Hebrew.** The owner's QA found ו for ז four times in tranches 1-4. A judge call
      for every Hebrew word with ו or ז next to a romanization that has z (or has none where ו is read) would
      find the rest; the concordance has the rows.
- [ ] **An override for a wrong identification.** "Jonathan" (the son of Saul, p. 751) gets the tooltip of
      the Targum; `names.identify` has no way to say "not here".

### Reader-facing

- [ ] **Names and abbreviations pages sorted by basis**, "guess" and "general knowledge" first, so
      the owner's review takes ten minutes.
- [ ] **The chapter's thesis on the index page.** One short paragraph per chapter (the `about` text
      in `entry.py` exists already).
- [ ] **"See also" per chapter** to the matching Lewysohn entry and fact-check claim (the crane and
      the swallow overlap with both): one dictionary in `build_site.py`.
- [ ] **Anchors for the columns of 1663.** The `[col. N]` marks are in the text; as HTML anchors
      they let the blog post and the fact-check link to "Hieroz. II, col. 66".

### Project management

- [x] **Tranche table in the README** Done 11-Nov-2026. (date, pages, cost, minutes, review items, changes). The three
      tranches are in prose now; a table shows the trend.

Done: the blog post on the project was published 10-Nov-2026:
https://www.ezrabrand.com/p/reading-bocharts-hierozoicon-with
