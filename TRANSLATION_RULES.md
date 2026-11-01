# Translation rules for Bochart (accepted 01-Nov-2026)

Accepted on 01-Nov-2026 with all four open points as recommended (see the end). Written as a
proposal before any translation run. Base: the Lewysohn rules v5 (`translate.py`,
`abbrev.py` in lewysohn-zoologie), changed for 17th-century Latin. Examples are from the pilot,
Rosenmüller vol. 2, pp. 409–429. **R** = my recommendation where there is a choice.

The method stays the same: Opus 5.5 @medium; chunks of whole paragraphs, cached; rules in the
prompt with a `RULES_VERSION`; **fixed corrections in code after the translation**, not in the
prompt (citations, page marks, votes, abbreviation expansions, name identifications).

## 1. What is translated, and what stays

| Source | English text | Example |
|---|---|---|
| Bochart's and Rosenmüller's Latin | translated | |
| Latin quotations (Vulgate, Jerome, Pliny, Bede …) | translated; italics kept; quotation marks as printed | *Lepusculus plebs invalida* → *the little hare, a feeble folk* |
| Bochart's Latin translation of a Greek, Hebrew or Arabic quotation | translated (it is his reading of the source) | *Petra refugium leporibus* → *the rock is a refuge for the hares* |
| Greek, Hebrew, Aramaic, Arabic, Persian, Syriac | kept in their script, as in the gold/OCR | |
| A Latin word **discussed as a word** | kept in Latin, italics, English in brackets | `Et a Graeco ὕραξ deductum sorex` (p. 428) → "And from the Greek ὕραξ [hyrax] comes *sorex* [shrew]" |
| Bochart's transliterations (*sephanim*, *aljarbuo*, *chagas*, *taphza*, *dur-romchi*) | kept exactly, with their italics; never modernized | |
| Linnaean and other zoological names (Rosenmüller: *viverra aurita*, *mus jaculus*) | kept as printed | |
| Titles of books, as printed (*Porta coeli*, *Masal Kadmoni*, *Commentar. ad Prov.*) | kept (see §4, §5) | |
| Hedges (*nisi fallor*, *suspicor*, *videtur*, *fortasse*, *si mavis*, *Aliorum tamen esto judicium*) | kept: "if I am not mistaken", "I suspect", "seems" … | |

The model adds **no** translation of a Greek, Hebrew or Arabic quotation that Bochart does not
translate (the same rule as in Lewysohn). The transliterations (§3) make such passages readable.

## 2. Bochart's citations

**Bible** (a fixed step in code, `modern_citations`, from a reviewed table of Bochart's book
abbreviations; the model keeps the reference as printed):

| Print | English |
|---|---|
| `Levit. XI, 5.` | Lev 11:5 |
| `Deut. XIV, 7.` | Deut 14:7 |
| `Psal. CIV. 18.` / `Pf. CIV, 18.` | Ps 104:18 |
| `Prov. XXX, 26.` | Prov 30:26 |
| `Es. LXVI, 17.` | Isa 66:17 |
| `Psal. CIII, (Hebraeis CIV.) 18.` | Ps 103 (Hebrew 104):18, as printed (the Vulgate number is kept where Bochart names it) |

R: SBL abbreviations with chapter:verse. Bochart uses the Hebrew numbering of the Psalms; the code
changes only the form, never a number.

**Classical and patristic works**, often written out in words: the numbers become Arabic numerals,
the structure words are translated, the **numbers are not changed to a modern edition** (Bochart's
chapter numbers of Pliny and Aelian are those of his editions):

| Print | English |
|---|---|
| `Plinius libri octavi capite quinquagesimo quinto` | Pliny, book 8, chapter 55 |
| `Aelianus libri decimi tertii De animalibus capite decimo quinto` | Aelian, *On Animals* book 13, chapter 15 |
| `Aristoteles Hist. lib. 6. cap. 37.` (p. 429, ch. 34) | Aristotle, *Hist.* book 6, ch. 37 (`Hist.` expanded by §5) |
| `Hieronymus Epistola 135. ad Suniam et Fretelam` | Jerome, Letter 135, to Sunnia and Fretela |

R: a later, optional concordance to the modern references (for p. 411, "book 8, chapter 55" on
the rabbits of Spain is probably *NH* 8.217, to check) as a reviewed table and a tooltip, not in
the text.

**Rabbinic and Jewish sources:** `R. Gerson, Tract. 4. cap. 1. fol. 19. d.` → "R. Gerson, tract.
4, ch. 1, fol. 19d" (folio and column letter joined in code, as "106, a" → "106a" in Lewysohn;
here also c and d). Titles stay as printed (*Porta coeli*, *Bereschith Rabba*); the
identification is a tooltip (§4).

**The Qur'an:** `Azoaram Alcorani LXXIII. cui titulus المنافقون` → "Azoara 73 of the Qur'an,
entitled المنافقون [al-munāfiqūn]". The number is kept as printed: Bochart counts the azoaras
of the Latin Qur'an of his time, not the modern suras (al-Munāfiqūn is sura 63 today). R: the
modern sura number as a tooltip from a reviewed table.

**Cross-references inside the Hierozoicon:** `supra p. 1012`, Bochart's note `c) Pag. 1003.`,
Rosenmüller's `vid. Bochartum supra`. These numbers are columns of 1663 (Rosenmüller calls them
"p."). R: keep "p. 1012" as printed in the English; the reading edition links each one to the
margin mark ⟦p. 1012⟧, and the introduction says once that "p." here means a column of 1663.

**Page marks:** two kinds, both kept in code after translation (the model does not touch them):
- Rosenmüller's page: `[II, 409]` at each page start (vol. 2, p. 409), with the scan link.
- The 1663 column from the margin: `⟦p. 1001⟧` → `[col. 1001]`, at the same place in the English
  sentence. R: "col." in the English, because scholars cite the 1663/1675 editions by column.

## 3. Foreign scripts and transliterations

As in Lewysohn: Hebrew and Aramaic in square script, **no transliteration**; Syriac gets Hebrew
letters in brackets (in code, `add_hebrew_letters`); Arabic and Persian get **IJMES**, Greek
**SBL** transliteration in brackets.

The new point: Bochart already gives his own transliteration after most foreign words:
`اليربوع aljarbuo`. R: keep both. The IJMES form goes in its bracket right after the Arabic, and
Bochart's form stays after it: `اليربوع [al-yarbūʿ] aljarbuo`. In the reading edition, the
brackets are tooltips (with the "inline" toggle), so the text reads as Bochart wrote it.

The transliteration follows **the Arabic as printed**, also where the print is wrong (gold rule):
`الجرد [al-jurd]`, not al-juradh. The list of printer's errors (gold rules in README) goes into the
translation as a tooltip "[print: …; read …]", added in code, never by the model.

Vowelled Arabic in Rosenmüller's notes (`أَلشَّعْنُ`): the transliteration follows the printed
vowels.

## 4. Names

Latin texts decline names (`Hieronymo`, `Plinii`, `Geuhario`, `Damiris`). The English needs one
fixed form for each person or work. R: a reviewed table `names.json`, like `abbreviations.json`:
each Latin form → the English form the model must use, plus an identification that code adds as
a tooltip at the first use in the chapter.

| Kind | English form | Examples from the pilot |
|---|---|---|
| Greek and Latin authors, Church Fathers | the usual English name | Jerome, Pliny, Aelian, Aristotle, Theophrastus, Herodotus, Photius, Hesychius, Nicander, Oppian, Basil, Theodoret, Apollinaris, Augustine, Arnobius, Bede, Eucherius, Strabo, Polybius, Galen |
| Arabic authors and works | **Bochart's form in the nominative** (as Lewysohn's romanizations are kept), identification as tooltip | Damiri [= al-Damīrī, *Ḥayāt al-ḥayawān*]; Giauhari [= al-Jawharī, *al-Ṣiḥāḥ*]; Abenbitar [= Ibn al-Bayṭār]; **Alcamus [= *al-Qāmūs al-muḥīṭ* of al-Fīrūzābādī: a dictionary, which Bochart cites like an author]**; Geographia Nubiensis [= al-Idrīsī, Latin by Gabriel Sionita, 1619] |
| Jewish authors and works | Bochart's form, identification as tooltip | R. Gerson, *Porta coeli* [= Gershon ben Solomon of Arles, *Shaʿar ha-shamayim*]; R. Isaac son of Solomon, *Masal Kadmoni* [= Isaac ibn Sahula, *Meshal ha-qadmoni*] |
| Early-modern scholars and travellers | the usual modern form | Giggei (Giggeius), Golius, Teixeira, Olearius, Gesner, Maundrell, Shaw, Bruce, Hasselquist, Ludolf, Schultens, Michaelis, Simonis, Buffon, Blumenbach, Hassencamp, Oedmann |

**Fixed terms** (in the prompt, as Lewysohn's "Abtheilung → Part"):

| Latin | English |
|---|---|
| *Seniores* (the translators of the Greek Bible) | "the Elders", tooltip [= the Septuagint translators] |
| *LXX* | LXX |
| *Vulgatus interpres* | the Vulgate translator |
| *Chaldaeus*, *Chaldaice* | the Chaldee, in Chaldee (tooltip: Aramaic; the Targum) |
| *Arabs interpres* | the Arabic translator |
| *Hebraei*, *Judaei* | the Hebrews, the Jews (as printed) |
| *cuniculus* | rabbit |
| *lepus*, *lepusculus* | hare, little hare |
| *herinaceus*, *hericius*, *erinaceus*, *echinus* | hedgehog |
| *mus*; *mus Alpinus*; *mus iaculus* | mouse; Alpine mouse (tooltip: marmot); jerboa (*mus iaculus*) |
| *choerogryllius* (χοιρογρύλλιος), *hyrax*, *Daman Israel* | kept as printed |
| *Palaestina* (in Bochart's and Rosenmüller's own words) | Eretz Yisrael; in a translated quotation of an ancient author: Palestine (R) |
| *Cap.* (a chapter of this book) | Chapter; `L. III.` in the running head: Book 3 |

R for *saphan* / שפן: keep "saphan" (Bochart's transliteration) everywhere; never "rock badger",
"coney" or "hyrax" in the translation, because the identity of the animal is what the chapter
argues about.

## 5. Abbreviations

As in Lewysohn v4: the model does **not** expand abbreviations. The prompt lists the
abbreviations of the chunk in two groups from a reviewed `abbreviations.json`:

- **translate** (general Latin): `vid.` → see; `cf.` → cf.; `l. c.` → loc. cit.; `ibid.` → ibid.;
  `seqq.` → ff.; `p.`, `pag.` → p.; `cap.` → ch.; `lib.` → book; `fol.` → fol.; `tom.` → vol.;
  `not.` → note; `vers. germ.` → German trans.; `P. V.` (a part of a work) → vol. 5;
  `al.` (a variant reading: `b) al. erit.`) → var.; `etc.` → etc.
- **expand** (sources; kept as printed, code adds `[=…]` at the first use):
  `Itiner.` (Shaw, Bruce, Maundrell: each a different book: the expansion depends on the author
  before it), `Lexic. Amhar.` [= Ludolf, *Lexicon Amharico-Latinum*], `Hist.` [= Aristotle,
  *Historia animalium*], `Commentar. ad Prov.` [= Schultens, *Commentarius in Proverbia
  Salomonis*], `Annotatt.`, `Clim. 1. part. 1.` [= climate 1, section 1 of al-Idrīsī].

## 6. The two layers of notes

- Bochart's notes (`a)`, `b)`, `c)`) and Rosenmüller's notes (`(1)`, `(13)`) stay separate. R: in
  the English and in the reading edition, Rosenmüller's notes are numbered "R1, R2 …" and printed
  with the label "Rosenmüller"; Bochart's keep their letters. A note mark is kept only where it
  stands in the chapter's own text (as in Lewysohn).
- Rosenmüller writes in Latin too; the same rules apply. His modern works keep their titles as
  printed.

## 7. Form of the English

- Clear, accurate scholarly English; not archaic, and not a paraphrase. Bochart's long periods may
  be split into shorter sentences; his numbered arguments (`1.`, `2.`, `I.`, `II.`) stay numbered.
- Roman numerals as numbers become Arabic numerals (book, chapter, verse, volume, sura); Roman
  numerals in names stay.
- Line breaks are joined, words broken at a line end are joined. A chunk that starts or ends
  mid-sentence is translated as a fragment.
- Italics: kept for quotations and for words discussed as words; moved to fit the English.

## 8. Order of the fixed steps after translation

1. Page marks `[II, 409]` and `[col. 1001]` copied from the source blocks.
2. Bible references (§2), folio columns (`fol. 19d`).
3. Hebrew letters for Syriac (`add_hebrew_letters`).
4. Votes of the second reading (Arabic, Greek, Hebrew, Latin), synced into the English.
5. `abbrev.py` (abbreviations) and `names.py` (identifications), first use only.
6. Printer's errors as tooltips.

## Cost

About 50,000 characters of source; with Opus @medium about $0.05 per page, so **about $1** for the
21 pages (Lewysohn: $0.031–0.051 per page).

## Open points (decided 01-Nov-2026: all four as recommended)

1. Bible references in the modern SBL form (`Lev 11:5`), or as printed with Arabic numerals
   (`Levit. 11, 5`)? R: SBL.
2. Arabic and Jewish authors: Bochart's form + tooltip (R), or the modern form in the text?
3. The 1663 column marks as `[col. 1001]` (R) or as printed (`[p. 1001]`)?
4. Rosenmüller's notes labelled "R1 …" (R), or kept as (1) … with a label?
