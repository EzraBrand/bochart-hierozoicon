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
needs a pair in `entry.FIXES` (grep `la.md` for `[?]` before translating).

## Ideas backlog (11-Nov-2026, after tranche 3)

Low-effort improvements, not yet done. Pick from the top; tick off here when done.

### Pipeline and cost

- [ ] **Greek accent pre-filter for the Flash flags.** Tranche 3 flagged 613 Greek words, most
      of them accent differences. Compare Greek on a stripped key for Flash (as f/s is folded for
      MDZ) and let only MDZ raise accent flags. Biggest cost cut for the bird books.
- [ ] **Rule list before the judge for the known MDZ quirks.** Flags where Flash agrees with Opus
      and MDZ differs only by f/s, hamza, ى, a dropped accent or glued punctuation go to a rule,
      not to Opus. Keep the MDZ-only flags that change a letter: those find the printer's errors.
- [ ] **One translation batch per tranche.** `tranche.py translate` submits one batch per chapter;
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
- [ ] **Translation spot-check.** Nothing checks the English against the Latin. A cheap batch pass
      with another model (GPT or Gemini) that flags sentences where the English drops a clause, a
      hedge or a number. Report only; no rewriting.
- [x] **Banned-words grep after translation.** Done 11-Nov-2026 (`banned.py`; counts the English word against its Latin/Greek sources per paragraph). Each chapter sets its own fixed terms (dove, never
      pigeon; deror stays deror). A grep of the English for the banned words (pigeon, coney, hyrax,
      rock badger, swallow in the deror chapter, crane in the agur chapter) catches slips for free.

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
