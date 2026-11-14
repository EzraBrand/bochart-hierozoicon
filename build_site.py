"""Build the reading edition in docs/ (served by GitHub Pages from main:/docs).

  uv run build_site.py

Pages: an index, one page per chapter with Latin and English side by side, and searchable tables
of abbreviations and names. Built only from files in data/; no model calls. Scans are shown from
the MDZ (Munich) IIIF server; each column mark of 1663 links to that column in the Frankfurt 1675
edition (same column numbers). Ported from lewysohn-zoologie.
"""

import hashlib
import html
import json
import re
import sys
from pathlib import Path

import names as N

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
DATA = ROOT / "data"
OUT = ROOT / "docs"
REPO = "https://github.com/EzraBrand/bochart-hierozoicon"
FACTCHECK = "https://ezrabrand.github.io/talmud-zoology-factcheck/"  # companion project (claim 7: hyrax)
LEWYSOHN = "https://ezrabrand.github.io/lewysohn-zoologie/"
MDZ_IIIF = "https://api.digitale-sammlungen.de/iiif/image/v2"
MDZ_VIEW = "https://www.digitale-sammlungen.de/en/view"
VOL_IDS = {1: "bsb10353453", 2: "bsb10353454", 3: "bsb10353455"}
F1675 = "bsb11935761"  # Frankfurt 1675, Pars I: canvas 569 = cols. 1001-1002


def col_canvas(col: int) -> int:
    return 569 + (col - 1001) // 2


DOCS = [
    {"slug": "shafan", "kind": "entry", "entry": "shafan", "vol": 2, "pages": list(range(409, 430)),
     "title": "Book 3, chapter 33: The shafan",
     "sub": "Vol. 2, pp. 409–429 · cols. 1001–1017 of 1663 · שפן saphan is not the rabbit but a kind of "
            "larger mouse (the jerboa): Hebrew, Greek, Latin, Arabic and Syriac sources"},
    {"slug": "choled", "kind": "entry", "entry": "choled", "vol": 2, "pages": list(range(435, 454)),
     "title": "Book 3, chapter 35: The choled",
     "sub": "Vol. 2, pp. 435–453 · cols. 1021–1036 of 1663 · חולד choled is not the weasel but the mole; "
            "other names of the mole. First chapter made with the Batch API pipeline (08-Nov-2026)"},
    {"slug": "achbar", "kind": "entry", "entry": "achbar", "vol": 2, "pages": list(range(429, 436)),
     "title": "Book 3, chapter 34: The common mouse",
     "sub": "Vol. 2, pp. 429–435 · cols. 1017–1020 of 1663 · עכבר achbar, the common mouse: plagues of mice, the golden mice of the Philistines (1 Sam 6)"},
    {"slug": "kippod", "kind": "entry", "entry": "kippod", "vol": 2, "pages": list(range(454, 463)),
     "title": "Book 3, chapter 36: The kippod",
     "sub": "Vol. 2, pp. 454–462 · cols. 1035–1042 of 1663 · קפוד kippod is the hedgehog and the porcupine, not a bird"},
    {"slug": "tsab", "kind": "entry", "entry": "tsab", "vol": 2, "pages": list(range(463, 488)),
     "title": "Book 4, chapter 1: The tsab",
     "sub": "Vol. 2, pp. 463–487 · cols. 1043–1063 of 1663 · Book 4, the oviparous quadrupeds. צב tsab (Lev 11:29) is the land crocodile, with Arabic sources on the dabb"},
    {"slug": "anaqah", "kind": "entry", "entry": "anaqah", "vol": 2, "pages": list(range(487, 494)),
     "title": "Book 4, chapter 2: The anaka",
     "sub": "Vol. 2, pp. 487–493 · cols. 1063–1068 of 1663 · אנקה anaka is a kind of stellio, named from its harsh cry"},
    {"slug": "koach", "kind": "entry", "entry": "koach", "vol": 2, "pages": list(range(493, 498)),
     "title": "Book 4, chapter 3: The coach",
     "sub": "Vol. 2, pp. 493–497 · cols. 1069–1072 of 1663 · כח coach is the Arabic waral, the largest lizard of Arabia"},
    {"slug": "letaah", "kind": "entry", "entry": "letaah", "vol": 2, "pages": list(range(497, 501)),
     "title": "Book 4, chapter 4: The leta",
     "sub": "Vol. 2, pp. 497–500 · cols. 1073–1075 of 1663 · לטאה leta is a venomous lizard like the stellio"},
    {"slug": "chomet", "kind": "entry", "entry": "chomet", "vol": 2, "pages": list(range(500, 504)),
     "title": "Book 4, chapter 5: The chomet",
     "sub": "Vol. 2, pp. 500–503 · cols. 1075–1078 of 1663 · חומט chomet is a lizard that lives in the sand"},
    {"slug": "tinshemet", "kind": "entry", "entry": "tinshemet", "vol": 2, "pages": list(range(503, 511)),
     "title": "Book 4, chapter 6: The tinshemeth",
     "sub": "Vol. 2, pp. 503–510 · cols. 1078–1083 of 1663 · תנשמת tinshemeth (Lev 11:30) is the chameleon"},
    {"slug": "semamit", "kind": "entry", "entry": "semamit", "vol": 2, "pages": list(range(510, 521)),
     "title": "Book 4, chapter 7: The semamith",
     "sub": "Vol. 2, pp. 510–520 · cols. 1083–1090 of 1663 · שממית semamith (Prov 30:28) is not the ape nor the spider but the stellio"},
    {"slug": "chelonai", "kind": "entry", "entry": "chelonai", "vol": 2, "pages": list(range(520, 524)),
     "title": "Book 4, chapter 8: Altars like tortoises",
     "sub": "Vol. 2, pp. 520–523 · cols. 1090–1094 of 1663 · why the altars of the idols are ὡς χελῶναι, like tortoises, in the Greek of Hos 12:12; the chelonis of Holofernes (Jdt 14:13)"},
    # Tranche 2 (10-Nov-2026): Part 2 (the birds), Book 1 (the clean birds), chs. 1-7, the dove. The
    # column numbers of 1663 begin again at 1 in Part 2.
    {"slug": "jonah", "kind": "entry", "entry": "jonah", "vol": 2, "pages": list(range(524, 533)),
     "title": "Part 2, Book 1, chapter 1: The Hebrew name of the dove",
     "sub": "Vol. 2, pp. 524–532 · cols. 1–8 of 1663 (Part 2) · Part 2, the birds; Book 1, the clean birds. יונה jonah, the dove's Hebrew name, and its etymology"},
    {"slug": "columba-pennae", "kind": "entry", "entry": "columba-pennae", "vol": 2, "pages": list(range(533, 545)),
     "title": "Part 2, Book 1, chapter 2: The dove's feathers, neck, eyes, moaning and flight",
     "sub": "Vol. 2, pp. 533–544 · cols. 9–16 of 1663 (Part 2) · the dove's feathers, neck, eyes, moaning and flight in the Bible and the ancient authors"},
    {"slug": "columbaria", "kind": "entry", "entry": "columbaria", "vol": 2, "pages": list(range(545, 549)),
     "title": "Part 2, Book 1, chapter 3: The dwellings of doves",
     "sub": "Vol. 2, pp. 545–548 · cols. 17–19 of 1663 (Part 2) · dovecotes, rocks and clefts (Isa 60:8, Song 2:14, Jer 48:28)"},
    {"slug": "columba-mores", "kind": "entry", "entry": "columba-mores", "vol": 2, "pages": list(range(549, 557)),
     "title": "Part 2, Book 1, chapter 4: The dove's simplicity, gentleness, chastity and timidity",
     "sub": "Vol. 2, pp. 549–556 · cols. 20–25 of 1663 (Part 2) · the dove's simplicity, gentleness, chastity and timidity (Matt 10:16, Hos 7:11)"},
    {"slug": "columba-sacrificia", "kind": "entry", "entry": "columba-sacrificia", "vol": 2, "pages": list(range(557, 560)),
     "title": "Part 2, Book 1, chapter 5: The sacrifices of doves and turtledoves",
     "sub": "Vol. 2, pp. 557–559 · cols. 26–27 of 1663 (Part 2) · the doves and turtledoves of the Law's sacrifices"},
    {"slug": "columba-noachi", "kind": "entry", "entry": "columba-noachi", "vol": 2, "pages": list(range(560, 572)),
     "title": "Part 2, Book 1, chapter 6: Noah's dove, and the dove at the baptism of Christ",
     "sub": "Vol. 2, pp. 560–571 · cols. 28–38 of 1663 (Part 2) · Noah's dove and the olive branch (Gen 8); the form of a dove at the baptism of Christ (Matt 3:16)"},
    {"slug": "chiryonim", "kind": "entry", "entry": "chiryonim", "vol": 2, "pages": list(range(572, 590)),
     "title": "Part 2, Book 1, chapter 7: Chiryonim, dove's dung or chickpeas",
     "sub": "Vol. 2, pp. 572–589 · cols. 39–50 of 1663 (Part 2) · חריונים chiryonim or דביונים dibyonim (2 Kgs 6:25), sold dear in the siege of Samaria, is a kind of chickpea, not dove's dung"},
    # Tranche 3 (11-Nov-2026): Part 2, Book 1, chs. 8-13.
    {"slug": "deror", "kind": "entry", "entry": "deror", "vol": 2, "pages": list(range(590, 597)),
     "title": "Part 2, Book 1, chapter 8: The deror",
     "sub": "Vol. 2, pp. 590–596 · cols. 51–54 of 1663 (Part 2) · דרור deror (Ps 84:4, Prov 26:2) is not the swallow but a wild dove, the turtledove or the wood pigeon"},
    {"slug": "turtur", "kind": "entry", "entry": "turtur", "vol": 2, "pages": list(range(596, 603)),
     "title": "Part 2, Book 1, chapter 9: The turtledove",
     "sub": "Vol. 2, pp. 596–602 · cols. 54–59 of 1663 (Part 2) · תור thor, the turtledove: its names, moaning, chastity and migration (Song 2:12, Jer 8:7)"},
    {"slug": "sis", "kind": "entry", "entry": "sis", "vol": 2, "pages": list(range(602, 614)),
     "title": "Part 2, Book 1, chapter 10: The swallow",
     "sub": "Vol. 2, pp. 602–613 · cols. 59–68 of 1663 (Part 2) · סיס sis (Jer 8:7, Isa 38:14) is the swallow: its names, migration and chirping"},
    {"slug": "agur", "kind": "entry", "entry": "agur", "vol": 2, "pages": list(range(614, 632)),
     "title": "Part 2, Book 1, chapter 11: The crane",
     "sub": "Vol. 2, pp. 614–631 · cols. 68–80 of 1663 (Part 2) · עגור agur (Isa 38:14, Jer 8:7) is the crane: its voice, migration and order of flight"},
    {"slug": "kore", "kind": "entry", "entry": "kore", "vol": 2, "pages": list(range(632, 645)),
     "title": "Part 2, Book 1, chapter 12: The kore",
     "sub": "Vol. 2, pp. 632–644 · cols. 80–89 of 1663 (Part 2) · קורא kore (1 Sam 26:20, Jer 17:11) is not the partridge but a kind of woodcock"},
    {"slug": "perdix-cavea", "kind": "entry", "entry": "perdix-cavea", "vol": 2, "pages": list(range(645, 648)),
     "title": "Part 2, Book 1, chapter 13: The hunter partridge in a cage",
     "sub": "Vol. 2, pp. 645–647 · cols. 89–91 of 1663 (Part 2) · the πέρδιξ θηρευτὴς ἐν καρτάλλῳ, the hunter partridge in a cage, of Sir 11:30, and the true partridge"},
    {"slug": "selav", "kind": "entry", "entry": "selav", "vol": 2, "pages": list(range(648, 656)),
     "title": "Part 2, Book 1, chapter 14: The names of the quail",
     "sub": "Vol. 2, pp. 648–655 · cols. 92–96 of 1663 (Part 2) · שלו selau, the quail: its names and the four kinds that the Talmud counts"},
    {"slug": "selav-quaestiones", "kind": "entry", "entry": "selav-quaestiones", "vol": 2, "pages": list(range(656, 676)),
     "title": "Part 2, Book 1, chapter 15: Five questions about the quails of Moses",
     "sub": "Vol. 2, pp. 656–675 · cols. 97–109 of 1663 (Part 2) · how often, how wholesome, from where, how many, and the punishment (Exod 16, Num 11)"},
    {"slug": "gallinaceum", "kind": "entry", "entry": "gallinaceum", "vol": 2, "pages": list(range(676, 688)),
     "title": "Part 2, Book 1, chapter 16: Twelve passages referred to the cock and the hen",
     "sub": "Vol. 2, pp. 676–687 · cols. 110–119 of 1663 (Part 2) · twelve passages of the Old Testament that some interpreters refer to the gallinaceous kind"},
    {"slug": "galli-cantus", "kind": "entry", "entry": "galli-cantus", "vol": 2, "pages": list(range(688, 695)),
     "title": "Part 2, Book 1, chapter 17: The crowing of the cock",
     "sub": "Vol. 2, pp. 688–694 · cols. 120–124 of 1663 (Part 2) · the cockcrow of the Gospels and the denial of Peter"},
    {"slug": "gallina-pulli", "kind": "entry", "entry": "gallina-pulli", "vol": 2, "pages": list(range(695, 698)),
     "title": "Part 2, Book 1, chapter 18: The hen's love for her chicks",
     "sub": "Vol. 2, pp. 695–697 · cols. 125–126 of 1663 (Part 2) · the hen that gathers her chicks under her wings (Matt 23:37)"},
    {"slug": "barburim", "kind": "entry", "entry": "barburim", "vol": 2, "pages": list(range(698, 709)),
     "title": "Part 2, Book 1, chapter 19: The barburim of Solomon's table",
     "sub": "Vol. 2, pp. 698–708 · cols. 127–135 of 1663 (Part 2) · ברבורים אבוסים barburim abusim (1 Kgs 4:23) are the choicest fattened fowl"},
    {"slug": "tukkiyim", "kind": "entry", "entry": "tukkiyim", "vol": 2, "pages": list(range(709, 721)),
     "title": "Part 2, Book 1, chapter 20: The peacocks",
     "sub": "Vol. 2, pp. 709–720 · cols. 136–145 of 1663 (Part 2) · תכיים thuccijim (1 Kgs 10:22) are peacocks; ivory and ebony"},
    {"slug": "tsippor", "kind": "entry", "entry": "tsippor", "vol": 2, "pages": list(range(721, 728)),
     "title": "Part 2, Book 1, chapter 21: The word tsippor",
     "sub": "Vol. 2, pp. 721–727 · cols. 145–150 of 1663 (Part 2) · צפור tsippor means any bird and specially the sparrow; its kinds according to the Arabs"},
    {"slug": "passer-prophetae", "kind": "entry", "entry": "passer-prophetae", "vol": 2, "pages": list(range(727, 736)),
     "title": "Part 2, Book 1, chapter 22: Nine passages referred to sparrows",
     "sub": "Vol. 2, pp. 727–735 · cols. 150–157 of 1663 (Part 2) · nine passages of the Old Testament that some interpreters refer to sparrows"},
    {"slug": "passer-providentia", "kind": "entry", "entry": "passer-providentia", "vol": 2, "pages": list(range(735, 739)),
     "title": "Part 2, Book 1, chapter 23: The providence of God for sparrows",
     "sub": "Vol. 2, pp. 735–738 · cols. 157–160 of 1663 (Part 2) · the sparrows sold for an assarion (Matt 10:29, Luke 12:6)"},
    {"slug": "aquila", "kind": "entry", "entry": "aquila", "vol": 2, "pages": list(range(739, 750)),
     "title": "Part 2, Book 2, chapter 1: The eagle, king of the birds",
     "sub": "Vol. 2, pp. 739–749 · cols. 161–169 of 1663 (Part 2) · נשר nesher: its name, beak, talons, plumage, baldness, renewal and colour"},
    {"slug": "aquila-volatus", "kind": "entry", "entry": "aquila-volatus", "vol": 2, "pages": list(range(750, 759)),
     "title": "Part 2, Book 2, chapter 2: The eagle's wings, flight, nest, sight and food",
     "sub": "Vol. 2, pp. 750–758 · cols. 169–176 of 1663 (Part 2) · the eagle's wings, flight, nest, sight and food"},
    {"slug": "aquila-pulli", "kind": "entry", "entry": "aquila-pulli", "vol": 2, "pages": list(range(759, 767)),
     "title": "Part 2, Book 2, chapter 3: The eagle's love for its young",
     "sub": "Vol. 2, pp. 759–766 · cols. 176–181 of 1663 (Part 2) · the eagle that stirs up its nest and carries its young (Deut 32:11)"},
    {"slug": "aquila-mystica", "kind": "entry", "entry": "aquila-mystica", "vol": 2, "pages": list(range(766, 771)),
     "title": "Part 2, Book 2, chapter 4: Mystical eagles",
     "sub": "Vol. 2, pp. 766–770 · cols. 182–185 of 1663 (Part 2) · God, the angels, the faithful and the great kings as eagles"},
    {"slug": "peres", "kind": "entry", "entry": "peres", "vol": 2, "pages": list(range(770, 774)),
     "title": "Part 2, Book 2, chapter 5: Peres is the ossifrage",
     "sub": "Vol. 2, pp. 770–773 · cols. 185–188 of 1663 (Part 2) · פרס peres (Lev 11:13) is the ossifrage"},
    {"slug": "oznija", "kind": "entry", "entry": "oznija", "vol": 2, "pages": list(range(774, 777)),
     "title": "Part 2, Book 2, chapter 6: Oznija is the black eagle",
     "sub": "Vol. 2, pp. 774–776 · cols. 188–190 of 1663 (Part 2) · עזניה oznija (Lev 11:13) is not the haliaeetus but the melanaeetus or Valerian eagle"},
    {"slug": "daah", "kind": "entry", "entry": "daah", "vol": 2, "pages": list(range(777, 779)),
     "title": "Part 2, Book 2, chapter 7: Daa or raa, the kite",
     "sub": "Vol. 2, pp. 777–778 · cols. 191–192 of 1663 (Part 2) · דאה daa (Lev 11:14) and ראה raa (Deut 14:13): the kite, named from its flight"},
    {"slug": "ajah", "kind": "entry", "entry": "ajah", "vol": 2, "pages": list(range(779, 783)),
     "title": "Part 2, Book 2, chapter 8: Aja is the merlin",
     "sub": "Vol. 2, pp. 779–782 · cols. 192–195 of 1663 (Part 2) · איה aja (Lev 11:14, Job 28:7) is a kind of hawk, the aesalon or merlin"},
    {"slug": "dajah", "kind": "entry", "entry": "dajah", "vol": 2, "pages": list(range(782, 787)),
     "title": "Part 2, Book 2, chapter 9: Daja is the black vulture",
     "sub": "Vol. 2, pp. 782–786 · cols. 195–197 of 1663 (Part 2) · דיה daja (Deut 14:13, Isa 34:15) is the black vulture"},
    {"slug": "corvus", "kind": "entry", "entry": "corvus", "vol": 2, "pages": list(range(787, 795)),
     "title": "Part 2, Book 2, chapter 10: The raven",
     "sub": "Vol. 2, pp. 787–794 · cols. 197–203 of 1663 (Part 2) · ערב oreb, the raven: its names, voice, colour, haunts, food and kinds"},
    {"slug": "corvus-providentia", "kind": "entry", "entry": "corvus-providentia", "vol": 2, "pages": list(range(794, 801)),
     "title": "Part 2, Book 2, chapter 11: The providence of God for ravens",
     "sub": "Vol. 2, pp. 794–800 · cols. 203–209 of 1663 (Part 2) · God feeds the young ravens (Job 38:41, Ps 147:9, Luke 12:24)"},
    {"slug": "corvus-noachi", "kind": "entry", "entry": "corvus-noachi", "vol": 2, "pages": list(range(800, 807)),
     "title": "Part 2, Book 2, chapter 12: Noah's raven",
     "sub": "Vol. 2, pp. 800–806 · cols. 209–214 of 1663 (Part 2) · the raven that Noah sent out of the ark (Gen 8:7)"},
    {"slug": "corvus-eliae", "kind": "entry", "entry": "corvus-eliae", "vol": 2, "pages": list(range(806, 812)),
     "title": "Part 2, Book 2, chapter 13: The ravens of Elijah",
     "sub": "Vol. 2, pp. 806–811 · cols. 214–217 of 1663 (Part 2) · the ערבים orebim that fed Elijah at the brook Cherith (1 Kgs 17) are ravens, not merchants or Arabs"},
    {"slug": "bath-jaana", "kind": "entry", "entry": "bath-jaana", "vol": 2, "pages": list(range(811, 831)),
     "title": "Part 2, Book 2, chapter 14: Bath jaana is the female ostrich",
     "sub": "Vol. 2, pp. 811–830 · cols. 217–231 of 1663 (Part 2) · בת יענה bath jaana (Lev 11:16) is not the owl but the female ostrich"},
    {"slug": "thachmas", "kind": "entry", "entry": "thachmas", "vol": 2, "pages": list(range(830, 839)),
     "title": "Part 2, Book 2, chapter 15: Thachmas is the male ostrich",
     "sub": "Vol. 2, pp. 830–838 · cols. 231–238 of 1663 (Part 2) · תחמס thachmas (Lev 11:16) is not a bird of prey but the male ostrich"},
    {"slug": "struthio-iob", "kind": "entry", "entry": "struthio-iob", "vol": 2, "pages": list(range(838, 855)),
     "title": "Part 2, Book 2, chapter 16: The ostrich in Job 39:13",
     "sub": "Vol. 2, pp. 838–854 · cols. 238–249 of 1663 (Part 2) · the most obscure verse on the ostrich, Job 39:13: the versions and Bochart's interpretation"},
    {"slug": "struthio-iob-reliqua", "kind": "entry", "entry": "struthio-iob-reliqua", "vol": 2, "pages": list(range(854, 871)),
     "title": "Part 2, Book 2, chapter 17: The rest of Job on the ostrich",
     "sub": "Vol. 2, pp. 854–870 · cols. 249–262 of 1663 (Part 2) · Job 39:14-18: the eggs left on the ground, the hardness to the young, the speed that laughs at the horse. End of vol. 2"},
]
CONTENTS = []

RTL_OR_GREEK = r"[ࠀ-࠿ሀ-᎟֐-׿יִ-ﭏ؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿܀-ݏͰ-Ͽἀ-῿]"
_TAIL = r"[^\s\[\]<>()*†,;:.?!]*"  # a run ends before Latin punctuation and footnote marks
# a run stays within one script ("השפן ኮሮገሬሊወን፡" on p. 418 is two runs: Hebrew RTL, Ethiopic LTR)
_SCRIPTS = [r"[֐-׿יִ-ﭏ]", r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]",
            r"[܀-ݏ]", r"[Ͱ-Ͽἀ-῿]", r"[ሀ-᎟]", r"[ࠀ-࠿]"]
_RUNS = "|".join(rf"{c}{_TAIL}(?:\s+{c}{_TAIL})*" for c in _SCRIPTS)
RUN = re.compile(rf"((?:{_RUNS}))(\s\[(?!=)([^\]]+)\])?")
import abbrev  # noqa: E402  (the whole abbreviation, e.g. "B. Kama", gets the tooltip, not only "Kama")
_ABBRS = "|".join(re.escape(r["abbr"]) for r in sorted(abbrev.items(), key=lambda r: -len(r["abbr"])))
# a name with an identification ("R. Isaac, son of Solomon [=...]") gets the tooltip as a whole
_NAMES = "|".join(re.escape(r["english"]) for r in sorted(N.items(), key=lambda r: -len(r["english"])) if r["id"])
EXPANSION = re.compile(rf"((?<![\w.])(?:{_ABBRS})|(?<![\w])(?:{_NAMES})(?:'s|')?|[^\s(\[<>]+)((?:</i>)?)\s\[=([^\]]*)\]")
PAGE_MARK = re.compile(r"\[(I{1,3}), (\d+)\]")
COL_MARK = re.compile(r"\[col\. (\d+)\]")
PARTICLES = {"el", "al", "ul", "il", "ad", "an", "as", "aš", "at", "ha", "ba", "bi", "li", "wa", "be", "le"}
NOTE_MARK = re.compile(r"<sup>(\(\d+\)|R\d+|[a-z]\))</sup>")  # Rosenmüller (13) / R13, Bochart c)


def mark_key(mark: str) -> str:
    """'(13)', 'R13', '13', 'c)', 'c' -> '13' or 'c'."""
    return re.sub(r"[()R\s]|<sup>|</sup>|\^\{|\}", "", mark)


def scan_ids() -> dict[str, int]:
    """page key ("v2-0409") -> MDZ canvas."""
    man = json.loads((DATA / "raw" / "manifest.json").read_text(encoding="utf-8"))["pages"]
    return {p["key"]: p["canvas"] for p in man}


def page_key(vol: int, page) -> str:
    return f"v{vol}-{int(page):04d}"


def page_label(key) -> str:
    vol, page = str(key).split("-")
    return f"{'I' * int(vol[1:])},&nbsp;{int(page)}"


def script_class(run: str) -> str:
    c = ord(run[0])
    if 0x0370 <= c <= 0x03FF or 0x1F00 <= c <= 0x1FFF:
        return "grc"
    if 0x0700 <= c <= 0x074F:
        return "syc"
    if 0x1200 <= c <= 0x139F:
        return "eth"
    if 0x0800 <= c <= 0x083F:
        return "sam"
    if 0x0600 <= c <= 0x06FF or 0x0750 <= c <= 0x077F or c >= 0xFB50:
        return "ara"
    return "heb"


def inline(text: str, page: int, ctx: dict) -> str:
    """One paragraph of text -> HTML. ctx: ids (page -> image id), notes ((page, mark) -> n)."""
    s = html.escape(text, quote=False).replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
    s = re.sub(r"\^\{(.+?)\}", r"<sup>\1</sup>", s)
    s = re.sub(r"_\{(.+?)\}", r"<sub>\1</sub>", s)
    # printed line breaks: re-join words split at a line end ("Te-\nrebinthus"), but keep the
    # hyphen after Arabic/Hebrew particles in transliterations ("el-\nanbāṭ") and before capitals
    def hyphen(m):
        return m.group(0).replace("\n", "") if m.group(1).lower() in PARTICLES else m.group(1) + m.group(2)
    s = re.sub(r"(\w+)-\n([a-zäöüßāēīōūăĕŏḥṭṣḳ])", hyphen, s)
    if ctx.get("lines"):  # a contents list: one entry per line; leader dots -> " … "
        s = re.sub(r"(?:\s*\.){3,}\s*", " … ", s).replace("\n", "<br>")
    s = s.replace("-\n", "-").replace("\n", " ")

    def run(m):
        cls = script_class(m.group(1))
        direction = "ltr" if cls in ("grc", "eth") else "rtl"
        out = f'<bdi class="{cls}" dir="{direction}">{m.group(1)}</bdi>'
        br = m.group(3)
        # a bracket is a transliteration only where the rules add one: Syriac -> Hebrew letters,
        # Samaritan -> Hebrew letters, Arabic/Greek/Ethiopic -> Latin. Any other bracket (e.g. the author's own "[בית]") stays text.
        is_tr = br and ((cls in ("syc", "sam") and re.match(r"[א-ת]", br)) or
                        (cls in ("ara", "grc") and re.match(r"[A-Za-zʾʿĀ-ž(]", br)) or
                        (cls == "eth" and not re.search(r"[ሀ-᎟א-ת]", br)))  # in code since 13-Nov-2026
        if br and not is_tr:
            return out + " [" + RUN.sub(run, br) + "]"
        if br:
            tr = html.escape(m.group(3), quote=True)
            out = (f'<span class="nl" data-tr="{tr}" tabindex="0">{out}</span>'
                   f'<span class="tr"> [{m.group(3)}]</span>')
        return out
    s = RUN.sub(run, s)
    s = EXPANSION.sub(lambda m: f'<abbr title="{html.escape(m.group(3), quote=True)}">{m.group(1)}</abbr>{m.group(2)}'
                                f'<span class="exp"> [={m.group(3)}]</span>', s)

    # note marks, page marks and column marks, in reading order (a page mark changes the page)
    out, cur = [], str(page)
    for part in re.split(r"(\[I{1,3}, \d+\]|\[col\. \d+\])", s):
        m = PAGE_MARK.fullmatch(part)
        if m:
            vol = len(m.group(1))
            cur = page_key(vol, m.group(2))
            canvas = ctx["ids"].get(cur)
            href = f"{MDZ_VIEW}/{VOL_IDS[vol]}?page={canvas}" if canvas else "#"
            aid = f' id="pg{int(m.group(2))}"' if ctx.get("anchors") else ""
            out.append(f'<a class="pg"{aid} href="{href}" target="_blank" rel="noopener" '
                       f'title="Scan of this page (Rosenmüller, vol. {vol})">{page_label(cur)}</a>')
            continue
        c = COL_MARK.fullmatch(part)
        if c:
            col = int(c.group(1))
            aid = f' id="col{col}"' if ctx.get("anchors") else ""
            out.append(f'<a class="col"{aid} href="{MDZ_VIEW}/{F1675}?page={col_canvas(col)}" target="_blank" '
                       f'rel="noopener" title="Column {col} of the 1663 edition: scan of the Frankfurt 1675 '
                       f'edition (same column numbers)">col.&nbsp;{col}</a>')
            continue
        def note(n):
            num = ctx["notes"].get((cur, mark_key(n.group(1))))
            if num is None:
                return n.group(0)
            label = ctx["labels"][num] if ctx["lang"] == "en" else n.group(1)  # the Latin keeps "(13)"
            return f'<a class="fn" href="#{ctx["lang"]}-n{num}" id="{ctx["lang"]}-r{num}">{label}</a>'
        out.append(NOTE_MARK.sub(note, part))
    return "".join(out)


def note_html(text: str, page, ctx: dict) -> str:
    """A footnote; a numbered list in it ("\n4) ...", joined over pages) keeps its line breaks."""
    text = re.sub(r"\n(?=\d+\) )", "\u2063", text)  # invisible separator as a placeholder
    return inline(text, page, ctx).replace("\u2063", "<br>")


def paragraph_page(text: str, start: str) -> str:
    marks = PAGE_MARK.findall(text)
    return page_key(len(marks[-1][0]), marks[-1][1]) if marks else start


def load_doc(doc: dict) -> dict:
    """-> {"de": [blocks], "en": [blocks], "de_notes", "en_notes"}; every block has "page"."""
    if doc["kind"] == "entry":
        de = json.loads((DATA / "entries" / doc["entry"] / "la.json").read_text(encoding="utf-8"))
        en = json.loads((DATA / "entries" / doc["entry"] / "en.json").read_text(encoding="utf-8"))
        return {"de": de["main"], "en": en["main"], "de_notes": de["notes"], "en_notes": en["notes"],
                "rules": en["meta"].get("rules", "?")}
    raise ValueError(f"unknown document kind {doc['kind']!r}")


FONTS = ("https://fonts.googleapis.com/css2?family=Noto+Serif:ital,wght@0,400;0,600;1,400"
         "&family=Noto+Serif+Hebrew&family=Noto+Sans+Syriac&family=Noto+Naskh+Arabic"
         "&family=Noto+Sans+Ethiopic&family=Noto+Sans+Samaritan&display=swap")


DESC = ("Samuel Bochart, Hierozoicon (1663), the classic study of the animals of the Bible: Latin text and "
        "English translation side by side, with links to the scans")


def page_html(title: str, body: str, desc: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc or DESC, quote=True)}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Bochart, Hierozoicon: reading edition">
<meta property="og:title" content="{html.escape(title, quote=True)}">
<meta property="og:description" content="{html.escape(desc or DESC, quote=True)}">
<meta name="twitter:card" content="summary">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<link rel="stylesheet" href="style.css?v={stamp(CSS)}">
<script>try{{var t=localStorage.getItem('bh-theme');if(t)document.documentElement.setAttribute('data-theme',t)}}catch(e){{}}</script>
</head>
<body>
{body}
<script src="app.js?v={stamp(JS)}"></script>
</body>
</html>
"""


def header(active: str) -> str:
    links = [("index.html", "Chapters"), ("passages.html", "Passages"), ("search.html", "Search"),
             ("abbreviations.html", "Abbreviations"), ("names.html", "Names"), ("hebrew.html", "Hebrew"),
             (FACTCHECK, "Fact-check"), (REPO, "Code and data")]
    nav = " ".join(f'<a href="{h}"{" aria-current=page" if h == active else ""}>{t}</a>' for h, t in links)
    nav += ('<label class="theme">Theme <select id="theme" aria-label="Colour theme">'
            '<option value="">Auto</option><option value="light">Light</option><option value="paper">Paper</option>'
            '<option value="dark">Dark</option></select></label>')
    return (f'<header class="site"><a class="brand" href="index.html">Bochart, <i>Hierozoicon</i> '
            f'<span>· reading edition</span></a><nav>{nav}</nav></header>')


TOGGLES = """<div class="toggles" role="group" aria-label="Display">
<label><input type="checkbox" data-toggle="show-de" checked> Latin</label>
<label><input type="checkbox" data-toggle="show-exp" checked> Identifications inline</label>
<label><input type="checkbox" data-toggle="show-tr" checked> Transliterations inline</label>
<label title="Select text to ask Google's AI about it, or to look a word up"><input type="checkbox" data-toggle="show-ask" checked> Look-up on selection</label>
</div>"""


PARA = re.compile(r"^(?:\[p\. [^\]]+\]\s*)?§\.\s*(\d+)\.\s*(.*)$", re.S)


def plain(text: str, words: int = 0) -> str:
    """Heading or paragraph text without page marks, expansions and footnote marks, for the contents."""
    s = re.sub(r"\[I{1,3}, \d+\]|\[col\. \d+\]|\s*\[=[^\]]*\]|\^\{[^}]*\}", "", text)
    s = " ".join(s.split())
    if words and len(s.split()) > words:
        s = " ".join(s.split()[:words]) + " …"
    return s


REGISTER = re.compile(r"^(I|II|III|IV)\.\s+(\w+)")


def anchors(en: list[dict]) -> tuple[dict[int, str], list[dict]]:
    """-> ({block index: anchor id}, contents entries). A § heading gets id "sN" (§. 119. -> #s119);
    its label is the title on the same line, or the title heading after it, or the opening words of
    its first paragraph. Other headings (parts, classes) get "hI" and are listed as group headings.
    In the registers, a letter heading after "I. Greek Register." etc. gets "lR-K" (#l3-2: the second
    letter of register III) and is listed in one row under its register."""
    ids, toc, used = {}, [], set()
    reg, k = None, 0
    for i, b in enumerate(en):
        if b["type"] == "heading" and (r := REGISTER.match(plain(b["text"]))):
            reg, k = ["I", "II", "III", "IV"].index(r.group(1)) + 1, 0
            ids[i] = f"h{i}"
            toc.append({"id": ids[i], "label": plain(b["text"]).rstrip("."), "group": True})
            continue
        letter = plain(b["text"]).rstrip(".")
        if reg and b["type"] == "heading" and len(letter) <= 4:  # "Jod." (J, after the vowel "J.")
            k += 1
            ids[i] = f"l{reg}-{k}"
            toc.append({"id": ids[i], "label": letter, "title": "", "group": False, "letter": True,
                        "reg": ["Greek", "Latin", "Hebrew", "German"][reg - 1]})
            continue
        m = PARA.match(b["text"])
        # a few § lines are typed as body text (mammals §§ 114-115); take them when the line is short
        short_para = b["type"] != "heading" and m and len(b["text"]) < 60
        if (b["type"] != "heading" and not short_para) or i in used:
            continue
        if not m:
            ids[i] = f"h{i}"
            toc.append({"id": ids[i], "label": plain(b["text"]), "group": True})
            continue
        n, title = m.group(1), plain(m.group(2))
        nxt = en[i + 1] if i + 1 < len(en) else None
        if not title and nxt and nxt["type"] == "heading" and not PARA.match(nxt["text"]):
            title = plain(nxt["text"])
            used.add(i + 1)
        elif not title and nxt:  # part 1: §§ open with a topic word ("Gestation period. The greatest ...")
            first = re.match(r"([^.]{1,40}?\.)\s", plain(nxt["text"]))
            title = first.group(1) if first and len(first.group(1).split()) <= 4 else plain(nxt["text"], 8)
        ids[i] = f"s{n}"
        toc.append({"id": ids[i], "label": f"§ {n}", "title": title, "group": False})
    return ids, toc


def toc_html(toc: list[dict]) -> str:
    n = sum(not t["group"] for t in toc)
    if not n:
        return ""
    ctx = {"ids": {}, "notes": {}, "lang": "en"}
    items = "".join(
        f'<li class="grp"><a href="#{t["id"]}">{inline(t["label"], "", ctx)}</a></li>' if t["group"] else
        f'<li class="ltr"><a href="#{t["id"]}"><b>{t["label"]}</b><span class="rg" hidden> {t["reg"]} register</span></a></li>'
        if t.get("letter") else
        f'<li><a href="#{t["id"]}"><b>{t["label"]}</b> {inline(t["title"], "", ctx)}</a></li>'
        for t in toc)
    first, last = next(t for t in toc if not t["group"]), [t for t in toc if not t["group"]][-1]
    if first.get("letter"):
        head = (f'<span class="tn">{sum(t["group"] for t in toc)} registers · {n} letters</span>'
                f'<span class="th">open to jump to a register or letter</span></summary>'
                f'<p class="sub">Each letter has a fixed link: <code>#l3-2</code> for the second letter of '
                f'register III. The bar at the top of the screen shows where you are while you read.</p>')
        cls = "toc reg"
    else:
        head = (f'<span class="tn">{first["label"]}–{last["label"].removeprefix("§ ")} · {n} sections</span>'
                f'<span class="th">open to jump to any §</span></summary>'
                f'<p class="sub">Each § has a fixed link: <code>#s119</code> for § 119. The bar at the top of '
                f'the screen shows where you are while you read.</p>')
        cls = "toc"
    return (f'<details class="{cls}" id="toc"><summary><span class="ti">☰</span> Contents '
            f'{head}<ul>{items}</ul></details>\n'
            f'<nav class="where" aria-label="Position in this page"><div class="prog"><span></span></div>'
            f'<button type="button" class="open-toc" title="Contents">☰<span> Contents</span></button>'
            f'<button type="button" class="prev" title="Previous §" aria-label="Previous §">‹</button>'
            f'<span class="cur" aria-live="polite">Start of page</span>'
            f'<button type="button" class="next" title="Next §" aria-label="Next §">›</button></nav>')


def doc_html(doc: dict) -> str:
    d = load_doc(doc)
    ids = scan_ids()
    vol = doc["vol"]
    # notes in order; (page key, mark) -> number; the link text is the printed label (R13, c))
    keymap, labels = {}, {}
    for i, (la, en) in enumerate(zip(d["de_notes"], d["en_notes"]), 1):
        keymap[(page_key(vol, la["page"]), mark_key(la.get("marker", "")))] = i
        labels[i] = en.get("label") or la.get("marker", "")
    rows = []
    pages = [page_key(vol, p) for p in doc["pages"]]
    cur = {"de": pages[0], "en": pages[0]}
    for k, (la, en) in enumerate(zip(d["de"], d["en"])):
        cells = []
        for lang, b in (("de", la), ("en", en)):
            ctx = {"ids": ids, "notes": keymap, "labels": labels, "lang": lang, "anchors": lang == "en"}
            text = inline(b["text"], cur[lang], ctx)
            if lang == "en":  # a fixed link to the paragraph (14-Nov-2026): chapter.html#p12
                text += (f' <a class="anchor" href="#p{k}" title="Link to this paragraph" '
                         f'aria-label="Link to this paragraph">¶</a>')
            cur[lang] = paragraph_page(b["text"], cur[lang])
            tag = "h3" if b["type"] == "heading" else "p"
            cells.append(f'<div class="cell {lang}" lang="{"la" if lang == "de" else "en"}"><{tag}>{text}</{tag}></div>')
        rows.append(f'<div class="row" id="p{k}">{"".join(cells)}</div>')
    notes = []
    for i, (la, en) in enumerate(zip(d["de_notes"], d["en_notes"]), 1):
        cells = []
        who = "Rosenmüller" if labels[i].startswith("R") else "Bochart"
        for lang, b in (("de", la), ("en", en)):
            ctx = {"ids": ids, "notes": {}, "labels": labels, "lang": lang}
            pk = page_key(vol, b["page"])
            cells.append(f'<div class="cell {lang}" id="{lang}-n{i}"><p><a class="fnback" href="#{lang}-r{i}">'
                         f'{labels[i] if lang == "en" else b.get("marker", "")}</a> <span class="pgref">{who}, '
                         f'{page_label(pk)}</span> {note_html(b["text"], pk, ctx)}</p></div>')
        notes.append(f'<div class="row note">{"".join(cells)}</div>')
    thumbs = "".join(
        f'<a href="{MDZ_VIEW}/{VOL_IDS[vol]}?page={ids[p]}" target="_blank" rel="noopener" title="Scan of this page">'
        f'<img loading="lazy" src="{MDZ_IIIF}/{VOL_IDS[vol]}_{ids[p]:05d}/full/160,/0/default.jpg" alt="Scan" width="160">'
        f'<span>{page_label(p)}</span></a>' for p in pages if p in ids)
    notes_html = f'<h2 id="notes">Notes</h2>\n{"".join(notes)}' if notes else ""
    body = f"""{header("")}
<main class="doc">
<h1>{html.escape(doc["title"])}</h1>
<p class="sub">{html.escape(doc["sub"])}</p>
<details class="about"><summary>How to read this page</summary>
<p>Left: the Latin of Bochart's <i>Hierozoicon</i> (London 1663) in Rosenmüller's edition (Leipzig
1793–96), as transcribed by Claude Opus 5.5 and corrected by a second reading of every script
(Gemini Flash, the MDZ OCR and an image judge; see the repository). Three pages (II, 410, 422, 428)
are checked by hand. Right: an English translation by Claude Opus 5.5 (rules {d["rules"]}).
Hebrew-script words are not transliterated; point at an Arabic or Greek word for its
transliteration, at a Syriac word for its Hebrew letters. Dotted names and abbreviations show an
identification, added by a program after translation from tables reviewed by hand
(<a href="abbreviations.html">abbreviations</a>, <a href="names.html">names</a>). “II, 410”
links to the scan of that page; “col. 1003” to that column of the 1663 edition, in the Frankfurt
1675 reprint. Fixed links: <code>#p12</code> is a paragraph (the ¶ at its end), <code>#pg787</code> a page of
this edition, <code>#col198</code> a column of 1663. R1–R13 are Rosenmüller's notes, a)–c) Bochart's. Machine output: check the scan
before you cite.</p></details>
{TOGGLES}
<div class="scans" aria-label="Scans">{thumbs}</div>
<div class="cols-head row"><div class="cell de">Latin (Bochart, ed. Rosenmüller)</div><div class="cell en">English</div></div>
{"".join(rows)}
{notes_html}
</main>
<a class="totop" href="#" aria-label="Back to top">↑ Top</a>
<footer>Scans: <a href="https://www.digitale-sammlungen.de/en/view/{VOL_IDS[vol]}">Bayerische Staatsbibliothek
München (MDZ)</a>, rights statement NoC-NC 1.0 · Transcription, translation and code: <a href="{REPO}/blob/main/LICENSE">MIT License</a> · <a href="{REPO}">{REPO.split("//")[1]}</a></footer>"""
    return page_html(f"{doc['title']} · Bochart, Hierozoicon", body, doc["sub"])


# the books of the Hierozoicon that the chapter titles name (Part 1 has no "Part" in the titles)
BOOK_NAMES = {"Book 3": "Part 1, Book 3: the wild quadrupeds", "Book 4": "Part 1, Book 4: the oviparous quadrupeds",
              "Part 2, Book 1": "Part 2, Book 1: the clean birds", "Part 2, Book 2": "Part 2, Book 2: the unclean birds"}


def done_docs() -> list[dict]:
    """The published chapters in the order of the book (DOCS is in the order of the work on them)."""
    return sorted((d for d in DOCS if (DATA / "entries" / d["entry"] / "en.json").exists()),
                  key=lambda d: (d["vol"], d["pages"][0], d["pages"][-1]))


def index_html() -> str:
    docs = done_docs()
    groups = {}
    for d in docs:
        groups.setdefault(d["title"].split(", chapter")[0], []).append(d)
    jump = " · ".join(f'<a href="#g{i}">{html.escape(BOOK_NAMES.get(g, g))}</a> ({len(ds)})'
                      for i, (g, ds) in enumerate(groups.items()))
    items = "".join(
        f'<h2 class="grp" id="g{i}">{html.escape(BOOK_NAMES.get(g, g))} <span>{len(ds)} chapters · vol. '
        f'{ds[0]["vol"]}, pp. {ds[0]["pages"][0]}–{max(x["pages"][-1] for x in ds)}</span></h2><ul class="docs">'
        + "".join(f'<li><a href="{d["slug"]}.html"><strong><span class="chn">Ch. '
                  f'{d["title"].split("chapter ")[1].split(":")[0]}</span> {html.escape(d["title"].split(": ", 1)[1])}'
                  f'</strong></a><span>{html.escape(d["sub"])}</span></li>' for d in ds) + "</ul>"
        for i, (g, ds) in enumerate(groups.items()))
    first, last = min(d["pages"][0] for d in docs), max(d["pages"][-1] for d in docs)
    body = f"""{header("index.html")}
<main class="index">
<h1>Samuel Bochart, <i>Hierozoicon</i></h1>
<p class="lede"><i>Hierozoicon, sive bipertitum opus de animalibus Sacrae Scripturae</i> (London 1663):
the standard early-modern study of every animal in the Bible, in Latin with Greek, Hebrew, Aramaic,
Syriac and much Arabic, and a main source for later work on the animals of the Bible and the Talmud.
No modern translation exists. This project gives it chapter by chapter, in the edition of
E. F. C. Rosenmüller (Leipzig 1793–96), as a machine transcription and English translation. Done so
far: {len(docs)} chapters, vol. 2, pp. {first}–{last}. Find a verse in the <a href="passages.html">index of
Bible passages</a>, or a word in the <a href="search.html">search</a>.</p>
<p class="jump">{jump}</p>
<p class="lede">Related: <a href="{LEWYSOHN}">Lewysohn, <i>Die Zoologie des Talmuds</i></a> (1858) and
the <a href="{FACTCHECK}">Talmud zoology fact-check</a> (claim 7: the hyrax and the hare).</p>
{items}
<h2>What this is</h2>
<ul class="plain">
<li>The transcription and the translation are machine output (Claude Opus 5.5). Every word where a
second reader (Gemini Flash, the MDZ OCR) differs was judged on the scan, and the changes were read
by eye; three pages (II, 410, 422, 428) were checked by hand.</li>
<li>Bochart's citations: Bible references in modern form; classical references with Bochart's own
book and chapter numbers; “p. 1012” in Rosenmüller's notes is a column of 1663.</li>
<li>Abbreviations and names are identified from tables reviewed by hand (<a href="abbreviations.html">abbreviations</a>,
<a href="names.html">names</a>); “general knowledge” or “guess” marks an identification that is not certain.</li>
<li>Each page links to the scan: please check it before citing anything.</li>
<li>Code, data, method and costs: <a href="{REPO}">{REPO.split("//")[1]}</a>.</li>
</ul>
</main>
<footer>Scans: Bayerische Staatsbibliothek München (MDZ), NoC-NC 1.0. Transcription, translation and code: <a href="{REPO}/blob/main/LICENSE">MIT License</a>.</footer>"""
    return page_html("Bochart, Hierozoicon · reading edition", body, DESC)


def table_pages(rx_items) -> dict:
    """{key: [page labels]} for each table row whose pattern occurs in the Latin of an entry."""
    out = {}
    for d in DOCS:
        la = DATA / "entries" / d["entry"] / "la.json"
        if not la.exists():
            continue
        for b in (lambda j: j["main"] + j["notes"])(json.loads(la.read_text(encoding="utf-8"))):
            text = abbrev.joined(b["text"])
            for k, rx in rx_items:
                if rx.search(text):
                    lab = page_label(page_key(d["vol"], b["page"])).replace("&nbsp;", " ")
                    if lab not in out.setdefault(k, []):
                        out[k].append(lab)
    return out


def abbreviations_html() -> str:
    pages = table_pages([(r["abbr"], re.compile(abbrev.pattern(r["abbr"]))) for r in abbrev.items()])
    kinds = {"source": "Primary source", "bibliography": "Bibliography", "general": "General"}
    rows = "".join(
        f'<tr><td>{html.escape(r["abbr"])}</td><td>{html.escape(r["expansion"])}'
        + (f' → <i>{html.escape(r["english"])}</i>' if r["mode"] == "translate" else "")
        + f'</td><td>{kinds[r["kind"]]}</td><td>{html.escape(r["basis"])}</td>'
        f'<td>{", ".join(pages.get(r["abbr"], []))}</td></tr>'
        for r in sorted(abbrev.items(), key=lambda r: r["abbr"].casefold()))
    body = f"""{header("abbreviations.html")}
<main class="index">
<h1>Abbreviations and short references</h1>
<p class="lede">Built from the abbreviations as they occur and reviewed by hand. Sources and
bibliography stay as printed in the English, and a program adds the expansion after the first use;
general Latin abbreviations are translated (→). Basis: <b>standard</b>; <b>context</b> = from the
passage; <b>general knowledge</b> = likely, not checked in a catalogue; <b>guess</b> = check.</p>
<input id="filter" type="search" placeholder="Filter, e.g. Itiner. or Schultens" aria-label="Filter">
<table class="abbr"><thead><tr><th>Abbreviation</th><th>Expansion</th><th>Kind</th><th>Basis</th><th>Pages</th></tr></thead>
<tbody>{rows}</tbody></table>
</main>"""
    return page_html("Abbreviations · Bochart, Hierozoicon", body)


def names_html() -> str:
    pages = table_pages([(r["english"], re.compile("|".join(N.form_rx(f).pattern for f in r["forms"])))
                         for r in N.items()])
    rows = "".join(
        f'<tr><td>{html.escape(r["english"])}</td><td>{html.escape(", ".join(r["forms"]))}</td>'
        f'<td>{html.escape(r["id"])}</td><td>{html.escape(r["basis"])}</td>'
        f'<td>{", ".join(pages.get(r["english"], []))}</td></tr>'
        for r in sorted(N.items(), key=lambda r: r["english"].casefold().removeprefix("the ")))
    body = f"""{header("names.html")}
<main class="index">
<h1>Names</h1>
<p class="lede">Latin declines names (<i>Hieronymo</i>, <i>Plinii</i>, <i>Geuhario</i>); the English uses
one form for each person or work. Classical and church authors have their usual English name; Arabic
and Jewish authors and works keep Bochart's form, with an identification that a program adds at the
first use. Basis: <b>standard</b>; <b>context</b>; <b>general knowledge</b> = likely, not checked in a
catalogue; <b>guess</b> = check.</p>
<input id="filter" type="search" placeholder="Filter, e.g. Damir or Gesner" aria-label="Filter">
<table class="abbr"><thead><tr><th>English</th><th>Latin forms</th><th>Identification</th><th>Basis</th><th>Pages</th></tr></thead>
<tbody>{rows}</tbody></table>
</main>"""
    return page_html("Names · Bochart, Hierozoicon", body)


def hebrew_html() -> str:
    """The concordance of the Hebrew-letter strings (concordance.py), for a reader's QA."""
    import concordance as C
    occ = C.rows()
    ws = [w for w in C.words(occ) if w["looks_like"]]
    titles = {d["slug"]: d["title"].split(":")[0].replace("chapter ", "ch. ") for d in DOCS}
    esc = html.escape
    rows = "".join(
        f'<tr><td><bdi class="heb" dir="rtl">{esc(r["hebrew"])}</bdi></td>'
        f'<td>{esc(r["before"])} <b><bdi class="heb" dir="rtl">{esc(r["hebrew"])}</bdi></b> {esc(r["after"])}</td>'
        f'<td><i>{esc(r["romanization"])}</i></td>'
        f'<td><a href="{r["site_url"].rsplit("/", 1)[1]}">{esc(titles[r["chapter"]])}</a>'
        f'{" (note)" if r["part"] == "note" else ""}<br><a class="pg" href="{r["scan_url"]}" target="_blank" '
        f'rel="noopener" title="Scan of this page">II,&nbsp;{r["page"]}</a></td>'
        f'<td><input type="checkbox" class="flag" aria-label="Flag this row" '
        f'data-k="{esc(r["hebrew"])}|{esc(r["romanization"])}|{r["page"]}|{r["chapter"]}"></td></tr>'
        for r in sorted(occ, key=lambda r: (r["key"], r["page"])))
    like = "".join(
        f'<tr><td><bdi class="heb" dir="rtl">{esc(w["word"])}</bdi></td><td>{w["count"]}</td>'
        f'<td><bdi class="heb" dir="rtl">{esc(w["looks_like"])}</bdi></td><td>{esc(w["pages"])}</td></tr>'
        for w in sorted(ws, key=lambda w: (w["count"], w["word"])))
    body = f"""{header("hebrew.html")}
<main class="index">
<h1>Hebrew concordance</h1>
<p class="lede">Every string in Hebrew letters (Hebrew and Aramaic) in the chapters published so far:
{len(occ):,} strings, {len({r["key"] for r in occ}):,} distinct, in alphabetical order, each with the words
around it, Bochart's romanization where one follows, and a link to the scan. This is a list for
checking: the text is a machine transcription, and in this type ד and ר, ה, ח and ת, ו, ז, י and ן, ב and
כ are hard to tell apart. The same rows as a spreadsheet:
<a href="{REPO}/blob/main/data/concordance/hebrew.csv">hebrew.csv</a>,
<a href="{REPO}/blob/main/data/concordance/hebrew_words.csv">hebrew_words.csv</a>.</p>
<p>To report wrong readings: tick <b>Flag</b> on each row (the ticks are kept in this browser), then copy
the list and send it.</p>
<div class="flagbar"><b id="nflag">0</b> flagged · <button type="button" id="copyflags">Copy the flagged rows</button>
<button type="button" id="onlyflags">Show only flagged</button> <button type="button" id="clearflags">Clear</button>
<span id="flagmsg"></span></div>
<input id="filter" type="search" placeholder="Filter, e.g. שפן or saphan or a page number" aria-label="Filter">
<table class="abbr conc"><thead><tr><th>Hebrew</th><th>Context</th><th>Romanization</th><th>Chapter, page</th><th>Flag</th></tr></thead>
<tbody>{rows}</tbody></table>
<h2 id="lookalikes">Words with a look-alike</h2>
<p>{len(ws)} words that differ from another word of the concordance only by letters that look alike in this
type (the count of the other word in brackets). Most are different words; a word found once beside a
frequent look-alike is the first place to check. Rarest first.</p>
<table class="abbr"><thead><tr><th>Word</th><th>Count</th><th>Looks like</th><th>Pages (vol. 2)</th></tr></thead>
<tbody>{like}</tbody></table>
</main>
<script>{FLAG_JS}</script>"""
    return page_html("Hebrew concordance · Bochart, Hierozoicon", body)


FLAG_JS = """(function(){
  var K='bh-flags', set={};
  try{set=JSON.parse(localStorage.getItem(K)||'{}')}catch(e){}
  var boxes=[].slice.call(document.querySelectorAll('input.flag')), n=document.getElementById('nflag'), msg=document.getElementById('flagmsg');
  function save(){try{localStorage.setItem(K,JSON.stringify(set))}catch(e){} n.textContent=Object.keys(set).length;}
  boxes.forEach(function(b){b.checked=!!set[b.dataset.k];
    b.addEventListener('change',function(){if(b.checked)set[b.dataset.k]=1;else delete set[b.dataset.k];save();});});
  save();
  document.getElementById('copyflags').addEventListener('click',function(){
    var t='hebrew\\tromanization\\tpage\\tchapter\\n'+Object.keys(set).map(function(k){return k.split('|').join('\\t')}).join('\\n');
    var done=function(){msg.textContent=' copied '+Object.keys(set).length+' rows'};
    if(navigator.clipboard) navigator.clipboard.writeText(t).then(done,function(){prompt('Copy:',t)}); else prompt('Copy:',t);});
  var only=false;
  document.getElementById('onlyflags').addEventListener('click',function(){only=!only;this.textContent=only?'Show all':'Show only flagged';
    boxes.forEach(function(b){b.closest('tr').style.display=(!only||b.checked)?'':'none';});});
  document.getElementById('clearflags').addEventListener('click',function(){if(!confirm('Remove all flags?'))return;set={};boxes.forEach(function(b){b.checked=false});save();});
})();"""

# SBL book names in the order of the canon (the English has "Deut 14:13"; translate.modern_citations)
CANON = [b.replace("_", " ") for b in (
    "Gen Exod Lev Num Deut Josh Judg Ruth 1_Sam 2_Sam 1_Kgs 2_Kgs 1_Chr 2_Chr Ezra Neh Esth Job Ps Prov Eccl "
    "Song Isa Jer Lam Ezek Dan Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal Tob Jdt Wis Sir Bar "
    "1_Macc 2_Macc Matt Mark Luke John Acts Rom 1_Cor 2_Cor Gal Eph Phil Col 1_Thess 2_Thess 1_Tim 2_Tim "
    "Titus Phlm Heb Jas 1_Pet 2_Pet 1_John Jude Rev").split()]
REF = re.compile(r"(?<![\w.])(" + "|".join(sorted(map(re.escape, CANON), key=len, reverse=True)) + r") (\d+):(\d+)")


def blocks_en():
    """Every English block of the published chapters: (doc, anchor, page, text). A paragraph of the main
    text has the anchor "pK", a note "en-nK"."""
    for d in done_docs():
        en = json.loads((DATA / "entries" / d["entry"] / "en.json").read_text(encoding="utf-8"))
        for k, b in enumerate(en["main"]):
            yield d, f"p{k}", b["page"], b["text"]
        for k, b in enumerate(en["notes"], 1):
            yield d, f"en-n{k}", b["page"], b["text"]


def passages_html() -> str:
    """Index of the Bible passages: verse -> the paragraphs and notes that cite it (14-Nov-2026)."""
    refs = {}
    for d, anchor, page, text in blocks_en():
        marks = [(m.start(), int(m.group(2))) for m in PAGE_MARK.finditer(text)]
        for m in REF.finditer(text):
            pg = max([(pos, p) for pos, p in marks if pos < m.start()], default=(0, int(page)))[1]
            key = (CANON.index(m.group(1)), int(m.group(2)), int(m.group(3)))
            link = (d["slug"], anchor, d["vol"], pg, d["title"].split(": ", 1)[1])
            if link not in refs.setdefault(key, []):
                refs[key].append(link)
    rows = "".join(
        f'<tr id="{CANON[b].replace(" ", "")}{c}-{v}"><td>{CANON[b]} {c}:{v}</td><td>'
        + " · ".join(f'<a href="{slug}.html#{a}" title="{html.escape(t, quote=True)}">{"I" * vol}, {pg}'
                     f'{" n." if a.startswith("en-n") else ""}</a>' for slug, a, vol, pg, t in links)
        + f'</td><td>{html.escape("; ".join(dict.fromkeys(t for *_, t in links)))}</td></tr>'
        for (b, c, v), links in sorted(refs.items()))
    books = {}
    for (b, c, v), links in refs.items():
        books[b] = books.get(b, 0) + len(links)
    body = f"""{header("passages.html")}
<main class="index">
<h1>Index of Bible passages</h1>
<p class="lede">{len(refs):,} verses that Bochart cites in the chapters published so far
({sum(len(x) for x in refs.values()):,} citations), in the order of the canon. Each link opens the paragraph or
note (n.) that cites the verse; the number is the page of Rosenmüller's edition. Made by a program from the
references in the English translation: a reference to a whole chapter, and a verse that Bochart quotes without
its number, are not here. Bochart counts some verses differently from modern editions (Job 39 above all).</p>
<p class="jump">{" · ".join(f"{CANON[b]} ({n})" for b, n in sorted(books.items()))}</p>
<input id="filter" type="search" placeholder="Filter, e.g. Lev 11: or Job 39:13 or eagle" aria-label="Filter">
<table class="abbr pass"><thead><tr><th>Verse</th><th>Cited at</th><th>Chapter</th></tr></thead>
<tbody>{rows}</tbody></table>
</main>"""
    return page_html("Bible passages · Bochart, Hierozoicon", body,
                     "Index of the Bible passages cited in Bochart's Hierozoicon, with links to the paragraphs")


def search_text(text: str) -> str:
    s = re.sub(r"\[I{1,3}, \d+\]|\[col\. \d+\]|\^\{[^}]*\}|</?i>|⟦[^⟧]*⟧", "", text)
    return " ".join(s.replace("-\n", "").split())


SEARCH_JS = """(function(){
  var q=document.getElementById('q'), out=document.getElementById('hits'), info=document.getElementById('info'), la=document.getElementById('la');
  var data={};
  function load(name){return data[name]?Promise.resolve(data[name]):fetch(name).then(function(r){return r.json()}).then(function(j){data[name]=j;return j;});}
  function esc(s){return s.replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c]});}
  function fold(s){return s.normalize('NFD').replace(/[\\u0300-\\u036f\\u0591-\\u05c7\\u064b-\\u0652]/g,'').toLowerCase();}
  function run(){
    var term=fold(q.value.trim());
    try{history.replaceState(null,'','?q='+encodeURIComponent(q.value.trim())+(la.checked?'&la=1':''))}catch(e){}
    if(term.length<2){out.innerHTML='';info.textContent='Type two letters or more.';return;}
    info.textContent='Searching…';
    load(la.checked?'search-la.json':'search-en.json').then(function(j){
      var html=[], n=0;
      for(var i=0;i<j.rows.length;i++){var r=j.rows[i], t=fold(r[3]), at=t.indexOf(term);
        if(at<0) continue; n++;
        if(n>300) continue;
        var a=Math.max(0,at-110), b=Math.min(t.length,at+term.length+160);
        var snip=esc(t.slice(a,at))+'<mark>'+esc(t.slice(at,at+term.length))+'</mark>'+esc(t.slice(at+term.length,b));
        var d=j.docs[r[0]];
        html.push('<li><a href="'+d[0]+'.html#'+r[1]+'"><b>'+esc(d[1])+'</b></a><span class="w">II, '+r[2]+(r[1].charAt(0)==='p'?'':' · note')+'</span>'+(a>0?'… ':'')+snip+(b<t.length?' …':'')+'</li>');}
      out.innerHTML=html.join('');
      info.textContent=n+' paragraph'+(n===1?'':'s')+(n>300?' (the first 300 are shown)':'')+' in the '+(la.checked?'Latin':'English')+' text.';
    });}
  var t=null; q.addEventListener('input',function(){clearTimeout(t);t=setTimeout(run,250);}); la.addEventListener('change',run);
  var p=new URLSearchParams(location.search); if(p.get('la'))la.checked=true; if(p.get('q')){q.value=p.get('q');run();}
  q.focus();
})();"""


def search_html() -> str:
    """A search page over the paragraphs (14-Nov-2026): docs/search-en.json and search-la.json hold one
    row per paragraph and note; the page looks for the typed text in the browser (no server). The snippet
    shows the folded text (lower case, no accents or points): the link opens the paragraph itself."""
    docs = done_docs()
    num = {d["slug"]: i for i, d in enumerate(docs)}
    for lang in ("en", "la"):
        rows = []
        for d in docs:
            j = json.loads((DATA / "entries" / d["entry"] / f"{lang}.json").read_text(encoding="utf-8"))
            rows += [[num[d["slug"]], f"p{k}", b["page"], search_text(b["text"])] for k, b in enumerate(j["main"])]
            rows += [[num[d["slug"]], f"en-n{k}", b["page"], search_text(b["text"])] for k, b in enumerate(j["notes"], 1)]
        out = {"docs": [[d["slug"], d["title"]] for d in docs], "rows": [r for r in rows if r[3]]}
        (OUT / f"search-{lang}.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    body = f"""{header("search.html")}
<main class="index">
<h1>Search</h1>
<p class="lede">Looks for the exact text you type in every paragraph and note of the {len(docs)} chapters. Capitals,
accents, Hebrew points and Arabic vowel signs are ignored: <i>korax</i> finds the transliteration of κόραξ,
κοραξ finds κόραξ, and עורב finds the pointed word too.</p>
<input id="q" type="search" placeholder="e.g. ostrich, Damir, עורב, κοραξ" aria-label="Search">
<p><label><input type="checkbox" id="la"> Search the Latin text, not the English</label> · <span id="info">Type two letters or more.</span></p>
<ul id="hits"></ul>
</main>
<script>{SEARCH_JS}</script>"""
    return page_html("Search · Bochart, Hierozoicon", body, "Search the Latin and the English of Bochart's Hierozoicon")


def stamp(text: str) -> str:
    """Short content hash for the style.css / app.js links, so a browser never pairs a new page
    with an old cached file (01-Nov-2026: the registers contents showed with the old CSS)."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


CSS = """:root{--bg:#fbfaf7;--fg:#22201c;--muted:#6b665d;--line:#e4e0d6;--accent:#7a4b12;--panel:#f2efe7;--mark:#efe3cf}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17161a;--fg:#e8e4dc;--muted:#a39d92;--line:#33313a;--accent:#e0a95c;--panel:#201f25;--mark:#3a3022}}
:root[data-theme="dark"]{--bg:#17161a;--fg:#e8e4dc;--muted:#a39d92;--line:#33313a;--accent:#e0a95c;--panel:#201f25;--mark:#3a3022}
:root[data-theme="paper"]{--bg:#f3ead6;--fg:#33291b;--muted:#75654c;--line:#d9cbab;--accent:#8a4510;--panel:#ebdfc3;--mark:#e3cfa3}
header.site label.theme{margin-left:1rem;color:var(--muted);font-size:.9rem}
header.site select{font:inherit;background:var(--panel);color:var(--fg);border:1px solid var(--line);border-radius:5px;padding:.1rem .3rem}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.6 "Noto Serif",Georgia,serif}
a{color:var(--accent)}
header.site{display:flex;flex-wrap:wrap;gap:.5rem 1.5rem;align-items:baseline;justify-content:space-between;padding:.8rem 1rem;border-bottom:1px solid var(--line)}
header.site .brand{color:var(--fg);text-decoration:none;font-weight:600}
header.site .brand span{color:var(--muted);font-weight:400}
header.site nav a{margin-left:1rem;text-decoration:none}
header.site nav a[aria-current]{text-decoration:underline}
main{max-width:1200px;margin:0 auto;padding:1rem}
main.index{max-width:760px}
h1{font-size:1.9rem;margin:.6rem 0 .2rem}
.sub,.lede{color:var(--muted)}
.lede{font-size:1.05rem}
ul.docs{list-style:none;padding:0}
ul.docs li{padding:.7rem 0;border-bottom:1px solid var(--line);display:flex;flex-direction:column}
ul.docs li span{color:var(--muted);font-size:.95rem}
ul.plain li{margin:.3rem 0}
h2.grp{font-size:1.25rem;margin:2rem 0 0;padding-bottom:.3rem;border-bottom:2px solid var(--accent);scroll-margin-top:1rem}
h2.grp span{color:var(--muted);font-weight:400;font-size:.85rem;margin-left:.5rem}
.chn{color:var(--muted);font-weight:400;font-size:.9em;margin-right:.3rem}
p.jump{font-size:.95rem}
.askbar{position:absolute;z-index:8;display:flex;flex-wrap:wrap;gap:.3rem;max-width:calc(100vw - 16px);background:var(--bg);border:1px solid var(--accent);border-radius:8px;box-shadow:0 4px 14px rgba(0,0,0,.25);padding:.3rem}
.askbar[hidden]{display:none}
.askbar a{font:600 .82rem system-ui,sans-serif;text-decoration:none;background:var(--panel);color:var(--fg);border:1px solid var(--line);border-radius:5px;padding:.25rem .55rem;white-space:nowrap}
.askbar a:first-child{background:var(--accent);color:var(--bg);border-color:var(--accent)}
table.pass td:first-child{width:9rem}
table.pass td a{white-space:nowrap}
#hits{padding:0}
#hits li{padding:.6rem 0;border-bottom:1px solid var(--line);list-style:none}
#hits mark{background:var(--mark);color:var(--fg)}
#hits .w{color:var(--muted);font-size:.85rem;display:block}
input#q{width:100%;padding:.5rem .7rem;font:inherit;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}
.flagbar{position:sticky;top:0;background:var(--bg);padding:.4rem 0;z-index:3;font-size:.92rem}
.flagbar button{font:inherit;background:var(--panel);color:var(--fg);border:1px solid var(--line);border-radius:5px;padding:.15rem .6rem;cursor:pointer}
details.about{background:var(--panel);padding:.6rem .9rem;border-radius:6px;margin:.8rem 0}
details.about p{margin:.5rem 0 0;font-size:.95rem}
details.toc{border:2px solid var(--accent);background:var(--panel);padding:.7rem 1rem;border-radius:8px;margin:1rem 0}
details.toc summary{cursor:pointer;font-weight:600;font-size:1.1rem;color:var(--accent);display:flex;flex-wrap:wrap;align-items:baseline;gap:.2rem .6rem}
details.toc summary .ti{font-size:1.2rem}
details.toc summary .tn{color:var(--fg);font-weight:400;font-size:.95rem}
details.toc summary .th{color:var(--muted);font-weight:400;font-size:.85rem;margin-left:auto}
details.toc[open] summary .th{display:none}
details.toc li a.here{color:var(--accent);font-weight:600}
details.toc li a.here::before{content:"▸ "}
nav.where{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:.4rem;background:var(--bg);border-bottom:1px solid var(--line);padding:.35rem 0 .45rem;margin:0 0 .5rem;font-size:.9rem}
nav.where .prog{position:absolute;left:0;right:0;bottom:-1px;height:3px;background:transparent}
nav.where .prog span{display:block;height:100%;width:0;background:var(--accent)}
nav.where button{font:inherit;background:var(--panel);color:var(--fg);border:1px solid var(--line);border-radius:5px;padding:.15rem .55rem;cursor:pointer}
nav.where button:disabled{opacity:.35;cursor:default}
nav.where .cur{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--muted)}
nav.where .cur b{color:var(--fg)}
a.anchor{color:var(--muted);text-decoration:none;opacity:.35;font-weight:400;padding-left:.2rem}
.row:hover a.anchor,a.anchor:focus{opacity:1}
a.totop{position:fixed;right:1rem;bottom:1rem;z-index:6;background:var(--accent);color:var(--bg);text-decoration:none;font:600 .9rem system-ui,sans-serif;padding:.45rem .8rem;border-radius:20px;box-shadow:0 2px 6px rgba(0,0,0,.25);opacity:0;pointer-events:none;transition:opacity .2s}
a.totop.show{opacity:.92;pointer-events:auto}
@media (max-width:760px){nav.where button span{display:none}}
details.toc ul{list-style:none;padding:0;margin:.4rem 0 0;max-height:60vh;overflow-y:auto;columns:2 300px;column-gap:2rem}
details.toc li{break-inside:avoid;padding:.12rem 0;font-size:.93rem}
details.toc li a{text-decoration:none;color:var(--fg)}
details.toc li a:hover{color:var(--accent)}
details.toc li.grp{font-weight:600;margin-top:.5rem;column-span:all}
details.toc.reg ul{columns:auto}
details.toc.reg li.ltr{display:inline-block;margin-right:.9rem;font-size:1.05rem}
details.toc.reg li.ltr .rg{display:none}
.row[id],.row.note .cell{scroll-margin-top:3.2rem}
.fntip{position:absolute;z-index:7;background:var(--bg);color:var(--fg);border:1px solid var(--accent);border-radius:8px;box-shadow:0 4px 14px rgba(0,0,0,.25);padding:.6rem .8rem;font-size:.92rem;line-height:1.5;max-height:50vh;overflow-y:auto}
.fntip p{display:inline;margin:0}
.fntip a.fngo{display:block;margin-top:.4rem;font-size:.85rem}
.row.note .cell:target{background:var(--mark)}
.row:target{background:var(--mark)}
.toggles{display:flex;flex-wrap:wrap;gap:.4rem 1.2rem;margin:.8rem 0;font-size:.95rem}
.scans{display:flex;gap:.6rem;overflow-x:auto;padding:.4rem 0 .8rem;border-bottom:1px solid var(--line)}
.scans a{flex:0 0 auto;text-align:center;text-decoration:none;font-size:.8rem;color:var(--muted)}
.scans img{display:block;width:80px;height:auto;border:1px solid var(--line);background:#fff}
.row{display:grid;grid-template-columns:1fr 1fr;gap:2rem;border-bottom:1px solid var(--line)}
.cols-head{font-size:.85rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);padding:.6rem 0 .2rem}
.cell p,.cell h3{margin:.7rem 0}
.cell h3{font-size:1.05rem}
.cell.de{color:var(--muted)}
body:not(.show-de) .row{grid-template-columns:1fr;max-width:760px}
body:not(.show-de) .cell.de{display:none}
.row.note{font-size:.9rem}
h2#notes{margin-top:2rem}
bdi.heb{font-family:"Noto Serif Hebrew",serif;font-size:1.08em}
bdi.syc{font-family:"Noto Sans Syriac",sans-serif;font-size:1.08em}
bdi.ara{font-family:"Noto Naskh Arabic",serif;font-size:1.05em}
bdi.eth{font-family:"Noto Sans Ethiopic",sans-serif}
bdi.sam{font-family:"Noto Sans Samaritan",sans-serif}
a.col{font-size:.72rem;border:1px solid var(--line);color:var(--muted);padding:0 .25rem;border-radius:3px;text-decoration:none;white-space:nowrap;vertical-align:.1em}
.nl{border-bottom:1px dotted var(--muted);cursor:help;position:relative}
.nl:hover::after,.nl:focus::after{content:attr(data-tr);position:absolute;left:0;top:1.6em;background:var(--fg);color:var(--bg);font:14px/1.3 "Noto Serif",serif;padding:.2rem .45rem;border-radius:4px;white-space:nowrap;z-index:2}
abbr{text-decoration:underline dotted var(--muted);cursor:help}
.exp,.tr{display:none;color:var(--muted)}
.cn{color:var(--muted);font-size:.92em}
body:not(.show-cn) .cn{display:none}
body.show-exp .exp,body.show-tr .tr{display:inline}
a.pg{font-size:.75rem;background:var(--mark);color:var(--fg);padding:0 .3rem;border-radius:3px;text-decoration:none;white-space:nowrap;vertical-align:.1em}
a.fn{font-size:.72em;vertical-align:super;line-height:0;text-decoration:none;padding:0 .1em}
a.fnback{font-weight:600;text-decoration:none}
.pgref{color:var(--muted);font-size:.85em}
input#filter{width:100%;padding:.5rem .7rem;font:inherit;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg);margin:.5rem 0 1rem}
table.abbr{width:100%;border-collapse:collapse;font-size:.92rem}
table.abbr th,table.abbr td{text-align:left;vertical-align:top;padding:.35rem .5rem;border-bottom:1px solid var(--line)}
table.abbr td:first-child{white-space:nowrap;font-weight:600}
table.conc{table-layout:fixed}table.conc td:first-child{white-space:normal;overflow-wrap:anywhere}
table.conc th:nth-child(1){width:20%}table.conc th:nth-child(2){width:47%}table.conc th:nth-child(3){width:13%}table.conc th:nth-child(5){width:5%}
footer{max-width:1200px;margin:2rem auto;padding:1rem;color:var(--muted);font-size:.85rem;border-top:1px solid var(--line)}
@media (max-width:760px){body{font-size:16px}.row{grid-template-columns:1fr;gap:0}.cell.de{border-bottom:1px dashed var(--line)}table.abbr td:nth-child(3),table.abbr th:nth-child(3){display:none}}
"""

JS = """(function(){
  var store={get:function(k){try{return localStorage.getItem(k)}catch(e){return null}},
             set:function(k,v){try{localStorage.setItem(k,v)}catch(e){}}};
  document.querySelectorAll('[data-toggle]').forEach(function(box){
    var cls=box.getAttribute('data-toggle'), saved=store.get('bh2-'+cls);
    if(saved!==null) box.checked = saved==='1';
    var apply=function(){document.body.classList.toggle(cls, box.checked); store.set('bh2-'+cls, box.checked?'1':'0');};
    box.addEventListener('change', apply); apply();
  });
  var th=document.getElementById('theme');
  if(th){th.value=document.documentElement.getAttribute('data-theme')||'';
    th.addEventListener('change',function(){
      if(th.value) document.documentElement.setAttribute('data-theme',th.value);
      else document.documentElement.removeAttribute('data-theme');
      store.set('bh-theme',th.value);});}
  var f=document.getElementById('filter');
  if(f){f.addEventListener('input',function(){var q=f.value.toLowerCase();
    document.querySelectorAll('table.abbr tbody tr').forEach(function(tr){
      tr.style.display = tr.textContent.toLowerCase().indexOf(q)>=0 ? '' : 'none';});});}
  // reading position: current § and page in the sticky bar, progress, contents highlight, back to top
  var bar=document.querySelector('nav.where'), top=document.querySelector('a.totop');
  var secs=[].slice.call(document.querySelectorAll('.row[id^="s"],.row[id^="l"]'));
  var pgs=[].slice.call(document.querySelectorAll('.cell.en a.pg'));
  var toc=document.getElementById('toc'), links={};
  if(toc) toc.querySelectorAll('li a').forEach(function(a){links[a.getAttribute('href').slice(1)]=a;});
  var idx=-2, ticking=false;
  function lastAbove(els,y){var i=-1;for(var k=0;k<els.length;k++){if(els[k].getBoundingClientRect().top<=y)i=k;else break;}return i;}
  function go(i){if(i>=0&&i<secs.length) location.hash='#'+secs[i].id;}
  function update(){
    ticking=false;
    if(top) top.classList.toggle('show', window.scrollY>600);
    if(!bar) return;
    var y=bar.getBoundingClientRect().bottom+12, i=lastAbove(secs,y), p=lastAbove(pgs,y);
    var h=document.documentElement;
    bar.querySelector('.prog span').style.width=(100*h.scrollTop/Math.max(1,h.scrollHeight-h.clientHeight))+'%';
    if(i!==idx){
      if(idx>=0&&links[secs[idx].id]) links[secs[idx].id].classList.remove('here');
      if(i>=0&&links[secs[i].id]) links[secs[i].id].classList.add('here');
      idx=i;
      bar.querySelector('.prev').disabled=i<=0;
      bar.querySelector('.next').disabled=i>=secs.length-1;
    }
    var a=i>=0?links[secs[i].id]:null, cur=bar.querySelector('.cur');
    cur.innerHTML='';
    if(a){var b=document.createElement('b');b.textContent=a.querySelector('b').textContent;cur.appendChild(b);
      cur.appendChild(document.createTextNode(' '+a.textContent.replace(a.querySelector('b').textContent,'').trim()));}
    else cur.textContent='Start of page';
    if(p>=0) cur.appendChild(document.createTextNode(' · '+pgs[p].textContent));
  }
  window.addEventListener('scroll',function(){if(!ticking){ticking=true;requestAnimationFrame(update);}},{passive:true});
  if(bar){
    bar.querySelector('.prev').addEventListener('click',function(){go(idx-1);});
    bar.querySelector('.next').addEventListener('click',function(){go(idx+1);});
    bar.querySelector('.open-toc').addEventListener('click',function(){toc.open=true;toc.scrollIntoView({block:'start'});});
    toc.addEventListener('toggle',function(){var h=toc.querySelector('a.here'),ul=toc.querySelector('ul');
      if(toc.open&&h) ul.scrollTop=h.parentNode.offsetTop-ul.offsetTop-ul.clientHeight/3;});
  }
  update();
  // footnote preview: hover or focus a note number to read the note in place; on touch screens
  // the first tap shows it and a second tap (or "Go to note") jumps to the notes
  var tip=document.createElement('div'); tip.className='fntip'; tip.setAttribute('role','tooltip'); tip.hidden=true;
  document.body.appendChild(tip);
  var shownFor=null, hideT=null;
  function show(a){
    var cell=document.getElementById(a.getAttribute('href').slice(1)); if(!cell) return;
    var p=cell.querySelector('p').cloneNode(true), back=p.querySelector('a.fnback');
    if(back) back.remove();
    tip.innerHTML='<b>Note '+a.textContent+'</b> ';
    tip.appendChild(p);
    var go=document.createElement('a'); go.href=a.getAttribute('href'); go.className='fngo'; go.textContent='Go to note ↓';
    tip.appendChild(go);
    tip.hidden=false;
    var r=a.getBoundingClientRect(), w=Math.min(420, window.innerWidth-24);
    tip.style.width=w+'px';
    tip.style.left=Math.max(12, Math.min(r.left+window.scrollX-w/2, window.scrollX+window.innerWidth-w-12))+'px';
    var below=r.bottom+window.scrollY+8;
    tip.style.top=below+'px';
    if(r.bottom+tip.offsetHeight+16>window.innerHeight&&r.top>tip.offsetHeight+16) tip.style.top=(r.top+window.scrollY-tip.offsetHeight-8)+'px';
    shownFor=a;
  }
  function hide(){tip.hidden=true; shownFor=null;}
  function later(){clearTimeout(hideT); hideT=setTimeout(hide,250);}
  document.querySelectorAll('a.fn').forEach(function(a){
    a.addEventListener('mouseenter',function(){clearTimeout(hideT); show(a);});
    a.addEventListener('mouseleave',later);
    a.addEventListener('focus',function(){show(a);});
    a.addEventListener('blur',later);
    a.addEventListener('click',function(ev){
      if(matchMedia('(hover: none)').matches&&shownFor!==a){ev.preventDefault(); show(a);}});
  });
  tip.addEventListener('mouseenter',function(){clearTimeout(hideT);});
  tip.addEventListener('mouseleave',later);
  document.addEventListener('click',function(ev){if(!tip.hidden&&!tip.contains(ev.target)&&!ev.target.closest('a.fn')) hide();});
  document.addEventListener('keydown',function(ev){if(ev.key==='Escape') hide();});
  // look-up on selection (14-Nov-2026): select text in a chapter to ask Google's AI mode about it, or to
  // look a Hebrew, Greek, Arabic or Latin word up, in a narrow window beside the page
  var doc=document.querySelector('main.doc');
  if(doc){
    var ask=document.createElement('div'); ask.className='askbar'; ask.hidden=true; document.body.appendChild(ask);
    var chapter=document.title.split(' · ')[0];
    function links(t){
      var e=encodeURIComponent, one=t.split(' ').length===1, out=[];
      out.push(['Ask Google AI','https://www.google.com/search?udm=50&q='+e('In Samuel Bochart, Hierozoicon (1663), '+chapter+', explain: "'+t+'"')]);
      out.push(['Google','https://www.google.com/search?q='+e(t)]);
      if(/[֐-׿]/.test(t)) out.push(['Sefaria','https://www.sefaria.org/search?q='+e(t)]);
      if(/[Ͱ-Ͽἀ-῿]/.test(t)&&one) out.push(['Logeion (Greek)','https://logeion.uchicago.edu/'+e(t.replace(/[.,;:·]+$/,''))]);
      if(/[؀-ۿ]/.test(t)) out.push(['Wiktionary (Arabic)','https://en.wiktionary.org/wiki/Special:Search?search='+e(t)]);
      if(/^[A-Za-z]+$/.test(t)) out.push(['Logeion (Latin)','https://logeion.uchicago.edu/'+e(t.toLowerCase())]);
      return out;
    }
    function place(){
      var s=window.getSelection(), t=s?String(s).replace(/\\s+/g,' ').trim():'';
      if(!document.body.classList.contains('show-ask')||!t||t.length>400||s.rangeCount===0||!doc.contains(s.anchorNode)){ask.hidden=true;return;}
      var r=s.getRangeAt(0).getBoundingClientRect();
      ask.innerHTML='';
      links(t).forEach(function(l){var a=document.createElement('a');a.textContent=l[0];a.href=l[1];a.target='bh-ask';a.rel='noopener';
        a.addEventListener('click',function(ev){
          if(window.innerWidth>=900){ev.preventDefault();
            var w=Math.min(560,Math.round(screen.availWidth*0.36));
            window.open(l[1],'bh-ask','popup=yes,width='+w+',height='+screen.availHeight+',left='+(screen.availWidth-w)+',top=0');}});
        ask.appendChild(a);});
      ask.hidden=false;
      ask.style.left=Math.max(8,Math.min(r.left+window.scrollX,window.scrollX+window.innerWidth-ask.offsetWidth-8))+'px';
      ask.style.top=(r.bottom+window.scrollY+10)+'px';
    }
    var askT=null;
    document.addEventListener('selectionchange',function(){clearTimeout(askT);askT=setTimeout(place,350);});
    ask.addEventListener('mousedown',function(ev){ev.preventDefault();});
  }
})();
"""


def main():
    OUT.mkdir(exist_ok=True)
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    (OUT / "style.css").write_text(CSS, encoding="utf-8")
    (OUT / "app.js").write_text(JS, encoding="utf-8")
    (OUT / "index.html").write_text(index_html(), encoding="utf-8")
    (OUT / "abbreviations.html").write_text(abbreviations_html(), encoding="utf-8")
    (OUT / "names.html").write_text(names_html(), encoding="utf-8")
    (OUT / "hebrew.html").write_text(hebrew_html(), encoding="utf-8")
    (OUT / "passages.html").write_text(passages_html(), encoding="utf-8")
    (OUT / "search.html").write_text(search_html(), encoding="utf-8")
    for d in CONTENTS + DOCS:
        if d["kind"] == "entry" and not (DATA / "entries" / d["entry"] / "en.json").exists():
            print(f"skip docs/{d['slug']}.html (no translation yet)")
            continue
        (OUT / f"{d['slug']}.html").write_text(doc_html(d), encoding="utf-8")
        print(f"wrote docs/{d['slug']}.html")
    import concordance  # the same rows as CSV, for a spreadsheet
    concordance.main()
    print("wrote docs/index.html, docs/abbreviations.html, docs/names.html, docs/hebrew.html")


if __name__ == "__main__":
    main()
