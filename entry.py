"""Join the pages of one chapter into continuous text and translate it as a whole.

  uv run entry.py shafan --no-translate     # the joined Latin text: data/entries/shafan/la.json, la.md
  uv run entry.py shafan                    # and the English (translate.py), chunk by chunk, resumable
  uv run entry.py shafan --finish-only      # redo the fixed steps after translation (no model call)

Ported from lewysohn-zoologie. Per page the source is the gold text if it exists, else the voted
OCR (vote.py). Furniture (running heads, signatures, catchwords) is dropped. A paragraph that runs
over a page break is joined, and "[II, 410]" marks where p. 410 of vol. 2 begins. The margin
column numbers of 1663 (⟦p. 1001⟧) become "[col. 1001]". Notes (Bochart's a), b) ...; Rosenmüller's
(1), (2) ...) are kept when their mark is in the chapter's own text on that page; a note without a
mark at the top of a page continues the last note of the page before.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DATA = Path(__file__).parent / "data"
SOURCE = os.environ.get("ENTRY_SOURCE", "or-claude-opus-5.5@low+vote")  # ENTRY_SOURCE: a dry run on another OCR
CHUNK_CHARS = 5000

# start / end: regexes for the first block of the chapter and the first block after it.
# Page joins checked by eye on the scans (logs/qa_v2-408-429.csv), 01-Nov-2026.
# the fixed bird names of tranche 7 (vol. 3, pp. 1-124: the rest of the unclean birds), for every chapter of it
_T7 = '"accipiter" -> "hawk"; "aquila" -> "eagle"; "vultur" -> "vulture"; "milvus" -> "kite"; "falco" -> "falcon"; "bubo" -> "eagle owl"; "noctua" -> "little owl"; "ulula" -> "owl"; "nycticorax" -> "night raven"; "onocrotalus", "porphyrio", "cepphus", "catarrhactes", "charadrius" -> the name is kept; "larus" -> "gull"; "pelicanus"/"pelecanus" -> "pelican"; "ardea" -> "heron"; "ciconia" -> "stork"; "upupa" -> "hoopoe"; "struthio" -> "ostrich"; "corvus" -> "raven"; "ibis" -> "ibis"; '
# the fixed serpent names of tranche 8 (vol. 3, pp. 125-193: Book 3, the serpents, chs. 1-10), for every chapter of it
_T8 = '"serpens" -> "serpent"; "anguis" -> "snake"; "coluber" -> "snake"; "vipera"/"echidna" -> "viper"; "aspis" -> "asp"; "basiliscus" -> "basilisk"; "regulus" -> "regulus" (the name is kept: Bochart gives it beside basiliscus); "draco" -> "dragon"; "cerastes", "dipsas", "amphisbaena", "hydrus", "chersydrus", "haemorrhous", "acontias", "dryinus", "seps", "prester" -> the name is kept; "venenum"/"virus" -> "poison" (never "venom" for one and "poison" for the other in one passage); "theriaca" -> "theriac"; '
# the fixed terms of Book 4 (the insects), from tranche 9 (vol. 3, p. 251 on), for every chapter of it
_T9 = '"insectum" -> "insect"; "volatilia" -> "flying creatures"; "repere" -> "to creep"; '
ENTRIES = {
    "shafan": {"vol": 2, "pages": list(range(409, 430)),
               "title": "Book 3, chapter 33: Saphan is not the rabbit but a kind of larger mouse (vol. 2, pp. 409–429)",
               "start": r"^CAP\.\s*XXXIII\.", "end": r"^CAP\.\s*XXXIV\.",
               "first_col": 1001},  # the mark p. 1001 stands in the last lines of ch. 32
    # 08-Nov-2026, the first chapter run with the Batch API (COST_TEST.md); the mark p. 1021 stands in
    # the heading line; ch. 36 begins at the top of p. 454
    "choled": {"vol": 2, "pages": list(range(435, 455)),
               "title": "Book 3, chapter 35: Choled is not the weasel but the mole; other names of the mole (vol. 2, pp. 435–453)",
               "start": r"^CAP\.\s*XXXV\.", "end": r"^CAP\.\s*XXXVI\.",
               "about": "the chapter arguing that the Hebrew חלד (choled) is not the weasel but the mole, "
                        "with the other names of the mole",
               "terms": '"mustela" -> "weasel"; "talpa" -> "mole"; "choled" stays "choled" (never "weasel" '
                        'or "mole": the identity of the animal is what the chapter argues about);'},
    # Tranche 1, 09-Nov-2026: ch. 34, ch. 36 and Book 4 (chs. 1-8). Chapter heads from the MDZ hOCR
    # (logs/find_caps.py); first_col = the last margin column before the chapter head.
    "achbar": {"vol": 2, "pages": list(range(429, 436)),
               "title": "Book 3, chapter 34: The common mouse (vol. 2, pp. 429–435)",
               "start": r"^CAP\.\s*XXXIV\.", "end": r"^CAP\.\s*XXXV\.", "first_col": 1017,
               "about": "the chapter on the common mouse, Hebrew עכבר (achbar)",
               "terms": '"mus" -> "mouse"; "achbar" stays "achbar";'},
    "kippod": {"vol": 2, "pages": list(range(454, 464)),
               "title": "Book 3, chapter 36: Kippod is the hedgehog and the porcupine (vol. 2, pp. 454–462)",
               "start": r"^CAP\.\s*XXXVI\.", "end": r"LIBER QUARTUS", "first_col": 1035,
               "about": "the chapter arguing that the Hebrew קפוד (kippod) is the hedgehog and the porcupine, "
                        "against those who take it for a bird",
               "terms": '"ericius"/"hericius"/"erinaceus" -> "hedgehog"; "hystrix" -> "porcupine"; '
                        '"kippod" stays "kippod" (never "hedgehog": the identity is what the chapter argues);'},
    "tsab": {"vol": 2, "pages": list(range(463, 488)),
             "title": "Book 4, chapter 1: Tsab (Lev 11:29) is the land crocodile (vol. 2, pp. 463–487)",
             "start": r"LIBER QUARTUS", "end": r"^CAP\.\s*II\.",
             "about": "the first chapter of the book on the oviparous quadrupeds, arguing that the Hebrew צב "
                      "(tsab) of Lev 11:29 is the land crocodile, with Arabic sources",
             "terms": '"crocodilus terrestris" -> "land crocodile"; "lacerta" -> "lizard"; "stellio" -> '
                      '"stellio" (the Latin name is kept); "scincus" -> "skink"; "tsab" stays "tsab" '
                      '(never "tortoise" or "crocodile": the identity is what the chapter argues);'},
    "anaqah": {"vol": 2, "pages": list(range(487, 494)),
               "title": "Book 4, chapter 2: Anaka is a kind of stellio, named from its harsh cry (vol. 2, pp. 487–493)",
               "start": r"^CAP\.\s*II\.", "end": r"^CAP\.\s*III\.", "first_col": 1063,
               "about": "the chapter arguing that the Hebrew אנקה (anaka) of Lev 11:30 is a kind of stellio, "
                        "named from its harsh cry",
               "terms": '"stellio" -> "stellio" (the Latin name is kept); "lacerta" -> "lizard"; '
                        '"anaka" stays "anaka";'},
    "koach": {"vol": 2, "pages": list(range(493, 498)),
              "title": "Book 4, chapter 3: Coach is the waral, the largest lizard of Arabia (vol. 2, pp. 493–497)",
              "start": r"^CAP\.\s*III\.", "end": r"^CAP\.\s*IV\.",
              "about": "the chapter arguing that the Hebrew כח (coach) of Lev 11:30 is the Arabic ورل (waral), "
                       "the largest and strongest lizard of Arabia",
              "terms": '"lacerta" -> "lizard"; "coach" stays "coach"; ورل is transliterated "waral";'},
    "letaah": {"vol": 2, "pages": list(range(497, 501)),
               "title": "Book 4, chapter 4: Leta is a venomous lizard like the stellio (vol. 2, pp. 497–500)",
               "start": r"^CAP\.\s*IV\.", "end": r"^CAP\.\s*V\.",
               "about": "the chapter arguing that the Hebrew לטאה (leta) of Lev 11:30 is a lizard like the "
                        "stellio, very venomous",
               "terms": '"lacerta" -> "lizard"; "stellio" -> "stellio" (the Latin name is kept); '
                        '"leta" stays "leta";'},
    "chomet": {"vol": 2, "pages": list(range(500, 504)),
               "title": "Book 4, chapter 5: Chomet is a lizard that lives in the sand (vol. 2, pp. 500–503)",
               "start": r"^CAP\.\s*V\.", "end": r"^CAP\.\s*VI\.", "first_col": 1075,
               "about": "the chapter arguing that the Hebrew חומט (chomet) of Lev 11:30 is a lizard that lives "
                        "in the sand",
               "terms": '"lacerta" -> "lizard"; "chomet" stays "chomet";'},
    "tinshemet": {"vol": 2, "pages": list(range(503, 511)),
                  "title": "Book 4, chapter 6: Tinshemeth (Lev 11:30) is the chameleon (vol. 2, pp. 503–510)",
                  "start": r"^CAP\.\s*VI\.", "end": r"^CAP\.\s*VII\.", "first_col": 1078,
                  "about": "the chapter arguing that the Hebrew תנשמת (tinshemeth) of Lev 11:30 is the chameleon",
                  "terms": '"chamaeleon" -> "chameleon"; "lacerta" -> "lizard"; "tinshemeth" stays "tinshemeth";'},
    "semamit": {"vol": 2, "pages": list(range(510, 521)),
                "title": "Book 4, chapter 7: Semamith (Prov 30:28) is not the ape nor the spider but the stellio "
                         "(vol. 2, pp. 510–520)",
                "start": r"^CAP\.\s*VII\.", "end": r"^CAP\.\s*VIII\.", "first_col": 1083,
                "about": "the chapter arguing that the Hebrew שממית (semamith) of Prov 30:28 is not the ape nor "
                         "the spider but the stellio",
                "terms": '"stellio" -> "stellio" (the Latin name is kept); "simia" -> "ape"; "aranea" -> '
                         '"spider"; "semamith" stays "semamith";'},
    "chelonai": {"vol": 2, "pages": list(range(520, 525)),
                 "title": "Book 4, chapter 8: Why the altars of the idols are said to be ὡς χελῶναι, like "
                          "tortoises, in the Greek version of Hosea (vol. 2, pp. 520–523)",
                 "start": r"^CAP\.\s*VIII\.", "end": r"PARS SECUNDA", "first_col": 1090,
                 "about": "the chapter on why the Greek version (the Septuagint) of Hosea says that the altars "
                          "of the idols are ὡς χελῶναι, like tortoises",
                 "terms": '"testudo" -> "tortoise" (or "tortoise shell" where the shell is meant);'},
    # Tranche 2, 10-Nov-2026: Pars II (the birds), Book 1 (the clean birds), chs. 1-7: the dove. Chapter
    # heads from the MDZ hOCR (logs/find_chapters_t2.log). The margin columns of 1663 start again at 1.
    "jonah": {"vol": 2, "pages": list(range(524, 534)),
              "title": "Part 2, Book 1, chapter 1: The Hebrew name of the dove (vol. 2, pp. 524–532)",
              "start": r"PARS SECUNDA", "end": r"^CAP\.\s*II\.",
              "about": "the first chapter of Part 2 (the birds), Book 1 (the clean birds): the Hebrew name of "
                       "the dove, יונה (jonah), and its etymology",
              "terms": '"columba" -> "dove" (never "pigeon"); "turtur" -> "turtledove"; "palumbes" -> "wood '
                       'pigeon"; "jonah"/"jona" (Bochart\'s romanized Hebrew) stays as printed;'},
    "columba-pennae": {"vol": 2, "pages": list(range(533, 546)),
                       "title": "Part 2, Book 1, chapter 2: The dove's feathers, neck, eyes, moaning and flight "
                                "(vol. 2, pp. 533–544)",
                       "start": r"^CAP\.\s*II\.", "end": r"^CAP\.\s*III\.",
                       "about": "the chapter on the dove's feathers, neck, eyes, moaning and flight in the Bible",
                       "terms": '"columba" -> "dove" (never "pigeon"); "turtur" -> "turtledove"; "gemitus" -> '
                                '"moaning"; "pennae" -> "feathers" (or "wings" where the flight is meant);'},
    "columbaria": {"vol": 2, "pages": list(range(545, 550)),
                   "title": "Part 2, Book 1, chapter 3: The dwellings of doves (vol. 2, pp. 545–548)",
                   "start": r"^CAP\.\s*III\.", "end": r"^CAP\.\s*IV\.",
                   "about": "the chapter on where doves dwell: dovecotes, rocks and clefts",
                   "terms": '"columba" -> "dove" (never "pigeon"); "columbarium" -> "dovecote";'},
    "columba-mores": {"vol": 2, "pages": list(range(549, 558)),
                      "title": "Part 2, Book 1, chapter 4: The dove's simplicity, gentleness, chastity and "
                               "timidity (vol. 2, pp. 549–556)",
                      "start": r"^CAP\.\s*IV\.", "end": r"^CAP\.\s*V\.",
                      "about": "the chapter on the dove's simplicity, gentleness, chastity and timidity",
                      "terms": '"columba" -> "dove" (never "pigeon"); "simplicitas" -> "simplicity"; '
                               '"mansuetudo" -> "gentleness"; "castitas" -> "chastity";'},
    "columba-sacrificia": {"vol": 2, "pages": list(range(557, 561)),
                           "title": "Part 2, Book 1, chapter 5: The sacrifices of doves and turtledoves "
                                    "(vol. 2, pp. 557–559)",
                           "start": r"^CAP\.\s*V\.", "end": r"^CAP\.\s*VI\.",
                           "about": "the chapter on the sacrifices of doves and turtledoves in the Law",
                           "terms": '"columba" -> "dove" (never "pigeon"); "turtur" -> "turtledove"; '
                                    '"pullus columbae" -> "young dove";'},
    "columba-noachi": {"vol": 2, "pages": list(range(560, 573)),
                       "title": "Part 2, Book 1, chapter 6: Noah's dove, and the form of a dove at the baptism "
                                "of Christ (vol. 2, pp. 560–571)",
                       "start": r"^CAP\.\s*VI\.", "end": r"^CAP\.\s*VII\.",
                       "about": "the chapter on Noah's dove (Gen 8) and on the form of a dove in which the Spirit "
                                "appeared at the baptism of Christ",
                       "terms": '"columba" -> "dove" (never "pigeon"); "ramus olivae" -> "olive branch";'},
    "chiryonim": {"vol": 2, "pages": list(range(572, 591)),
                  "title": "Part 2, Book 1, chapter 7: Chiryonim or dibyonim (2 Kgs 6:25) is a kind of chickpea, "
                           "not dove's dung (vol. 2, pp. 572–589)",
                  "start": r"^CAP\.\s*VII\.", "end": r"^CAP\.\s*VIII\.",
                  "about": "the chapter arguing that חריונים (chiryonim) or דביונים (dibyonim) of 2 Kgs 6:25, "
                           "sold at a high price in the siege of Samaria, is a kind of chickpea, not dove's dung",
                  "terms": '"columba" -> "dove" (never "pigeon"); "cicer" -> "chickpea"; "stercus columbarum"/'
                           '"fimus columbinus" -> "dove\'s dung"; Bochart\'s romanized Hebrew names stay as printed;'},
    # Tranche 3, 11-Nov-2026: Pars II, Book I, chs. 8-13. Chapter heads from the MDZ hOCR
    # (logs/find_chapters_t3_*.log).
    "deror": {"vol": 2, "pages": list(range(590, 597)),
              "title": "Part 2, Book 1, chapter 8: Deror is not the swallow but a kind of wild dove, the turtledove "
                       "or the wood pigeon (vol. 2, pp. 590–596)",
              "start": r"^CAP\.\s*VIII\.", "end": r"^CAP\.\s*IX\.",
              "about": "the chapter arguing that the Hebrew דרור (deror) is not the swallow, as is held, but a kind "
                       "of wild dove, the turtledove or the wood pigeon",
              "terms": '"hirundo" -> "swallow"; "columba" -> "dove" (never "pigeon"); "turtur" -> "turtledove"; '
                       '"palumbes"/"palumbus" -> "wood pigeon"; "passer" -> "sparrow"; "deror" stays "deror" '
                       '(never "swallow" or "sparrow": the identity of the bird is what the chapter argues about);'},
    "turtur": {"vol": 2, "pages": list(range(596, 603)),
               "title": "Part 2, Book 1, chapter 9: The turtledove (vol. 2, pp. 596–602)",
               "start": r"^CAP\.\s*IX\.", "end": r"^CAP\.\s*X\.", "first_col": 54,
               "about": "the chapter on the turtledove, Hebrew תור (thor), Greek τρυγών: its names, its moaning, "
                        "its chastity and its migration",
               "terms": '"turtur" -> "turtledove"; "columba" -> "dove" (never "pigeon"); "gemere"/"gemitus" -> '
                        '"moan"/"moaning"; "thor" (Bochart\'s romanized Hebrew) stays as printed;'},
    "sis": {"vol": 2, "pages": list(range(602, 615)),
            "title": "Part 2, Book 1, chapter 10: The swallow (vol. 2, pp. 602–613)",
            "start": r"^CAP\.\s*X\.", "end": r"^CAP\.\s*XI\.", "first_col": 59,
            "about": "the chapter arguing that the Hebrew סיס (sis) of Jer 8:7 and Isa 38:14 is the swallow, with "
                     "the swallow's names, migration and chirping in the ancient authors",
            "terms": '"hirundo" -> "swallow"; "grus" -> "crane"; "sis", "sus" and "agur"/"agor" (Bochart\'s '
                     'romanized Hebrew) stay as printed; "sis" stays "sis" (never "swallow": the identity of the '
                     'bird is what the chapter argues about);'},
    "agur": {"vol": 2, "pages": list(range(614, 633)),
             "title": "Part 2, Book 1, chapter 11: The crane (vol. 2, pp. 614–631)",
             "start": r"^CAP\.\s*XI\.", "end": r"^CAP\.\s*XII\.", "first_col": 68,
             "about": "the chapter arguing that the Hebrew עגור (agur) of Isa 38:14 and Jer 8:7 is the crane, with "
                      "the crane's voice, migration, order of flight and the ancient accounts of it",
             "terms": '"grus" -> "crane"; "hirundo" -> "swallow"; "agur"/"agor" (Bochart\'s romanized Hebrew) stays '
                      'as printed (never "crane": the identity of the bird is what the chapter argues about);'},
    "kore": {"vol": 2, "pages": list(range(632, 646)),
             "title": "Part 2, Book 1, chapter 12: Kore is not the partridge but a kind of woodcock "
                      "(vol. 2, pp. 632–644)",
             "start": r"^CAP\.\s*XII\.", "end": r"^CAP\.\s*XIII\.", "first_col": 80,
             "about": "the chapter arguing that the Hebrew קורא (kore) of 1 Sam 26:20 and Jer 17:11 is not the "
                      "partridge, as has been believed, but a kind of woodcock (rusticula, gallinago)",
             "terms": '"perdix" -> "partridge"; "rusticula" -> "woodcock" (with "<i>rusticula</i>" in brackets at '
                      'the first use); "gallinago" -> "<i>gallinago</i>" (kept in Latin); "kore" stays "kore" '
                      '(never "partridge": the identity of the bird is what the chapter argues about);'},
    "perdix-cavea": {"vol": 2, "pages": list(range(645, 649)),
                     "title": "Part 2, Book 1, chapter 13: The hunter partridge in a cage (Sirach 11) "
                              "(vol. 2, pp. 645–647)",
                     "start": r"^CAP\.\s*XIII\.", "end": r"^CAP\.\s*XIV\.", "first_col": 89,
                     "about": "the chapter on the πέρδιξ θηρευτὴς ἐν καρτάλλῳ, the hunter partridge in a cage, of "
                              "Sirach 11, and on the true partridge, its tameness and its use as a decoy",
                     "terms": '"perdix" -> "partridge"; "perdix venator" -> "hunter partridge" (Bochart\'s rendering '
                              'of θηρευτής; not "decoy"); "cavea" -> "cage"; "cicur" -> "tame"; "laqueus" -> "snare";'},
    # Tranche 4, 12-Nov-2026: Pars II, Book I, chs. 14-20 (uv run find_chapters.py 648 760).
    "selav": {"vol": 2, "pages": list(range(648, 657)),
              "title": "Part 2, Book 1, chapter 14: The names of the quail, and its kinds according to the "
                       "Hebrews (vol. 2, pp. 648–655)",
              "start": r"^CAP\.\s*XIV\.", "end": r"^CAP\.\s*XV\.", "first_col": 91,
              "about": "the chapter on the names of the quail, Hebrew שלו (selau), Arabic سلوي and سماني, and on "
                       "the four kinds that the Talmud counts: sichli (συκαλίς), kichli (κίχλη), pasyoni (the "
                       "pheasant) and selav",
              "terms": '"coturnix" -> "quail"; "ortygometra" -> "ortygometra" (the Latin name is kept); '
                       '"phasianus" -> "pheasant"; "turdus" -> "thrush"; "ficedula" -> "fig-pecker"; "locusta" -> '
                       '"locust"; "selau"/"selav" (Bochart\'s romanized Hebrew) stays as printed;'},
    "selav-quaestiones": {"vol": 2, "pages": list(range(656, 677)),
                          "title": "Part 2, Book 1, chapter 15: Five questions about the quails of Moses "
                                   "(vol. 2, pp. 656–675)",
                          "start": r"^CAP\.\s*XV\.", "end": r"^CAP\.\s*XVI\.", "first_col": 96,
                          "about": "the chapter that answers five questions about the quails of Exod 16 and Num 11: "
                                   "how many times God gave quails to the Israelites, whether the quail is "
                                   "wholesome food, from where the quails came, how many came, and what the "
                                   "punishment of those who ate them was",
                          "terms": '"coturnix" -> "quail"; "ortygometra" -> "ortygometra"; "auster" -> "south wind"; '
                                   '"eurus" -> "east wind"; "chomer"/"corus" -> "homer"/"cor" (the measures); '
                                   '"cubitus" -> "cubit"; "selau"/"selav" stays as printed;'},
    "gallinaceum": {"vol": 2, "pages": list(range(676, 689)),
                    "title": "Part 2, Book 1, chapter 16: Twelve passages of Scripture that some interpreters refer "
                             "to the cock and the hen (vol. 2, pp. 676–687)",
                    "start": r"^CAP\.\s*XVI\.", "end": r"^CAP\.\s*XVII\.", "first_col": 109,
                    "about": "the chapter that examines twelve passages of the Old Testament which some interpreters "
                             "refer to the gallinaceous kind (Lev 14:4; 1 Kgs 4:23; 2 Kgs 17:30; Job 3:7; 38:32; "
                             "38:36; 39:13; Ps 50:11; 80:14; Prov 30:31; Eccl 12:4; Isa 22:17)",
                    "terms": '"gallus"/"gallus gallinaceus" -> "cock"; "gallina" -> "hen"; "gallinaceum genus" -> '
                             '"the gallinaceous kind"; "capo" -> "capon"; Bochart\'s romanized Hebrew and Aramaic '
                             '(sechvi, zarzir, tarnegol, abacha, achaba, geber) stays as printed;'},
    "galli-cantus": {"vol": 2, "pages": list(range(688, 696)),
                     "title": "Part 2, Book 1, chapter 17: The crowing of the cock (vol. 2, pp. 688–694)",
                     "start": r"^CAP\.\s*XVII\.", "end": r"^CAP\.\s*XVIII\.", "first_col": 119,
                     "about": "the chapter on the crowing of the cock in the New Testament (the denial of Peter), "
                              "the times of cockcrow, and the Jewish and Arabic accounts of the cock",
                     "terms": '"gallus" -> "cock"; "galli cantus" -> "the crowing of the cock"; "gallicinium" -> '
                              '"cockcrow"; "canere" (of the cock) -> "crow"; "vigilia" -> "watch" (of the night);'},
    "gallina-pulli": {"vol": 2, "pages": list(range(695, 699)),
                      "title": "Part 2, Book 1, chapter 18: The hen's love for her chicks (vol. 2, pp. 695–697)",
                      "start": r"^CAP\.\s*XVIII\.", "end": r"^CAP\.\s*XIX\.", "first_col": 124,
                      "about": "the chapter on the hen's love for her chicks (Matt 23:37; Luke 13:34)",
                      "terms": '"gallina" -> "hen"; "pulli" -> "chicks"; "gallus" -> "cock"; "alae" -> "wings";'},
    "barburim": {"vol": 2, "pages": list(range(698, 710)),
                 "title": "Part 2, Book 1, chapter 19: What the barburim abusim on the table of Solomon were "
                          "(1 Kgs 4:23) (vol. 2, pp. 698–708)",
                 "start": r"^CAP\.\s*XIX\.", "end": r"^CAP\.\s*XX\.", "first_col": 126,
                 "about": "the chapter on the ברבורים אבוסים (barburim abusim, 'fattened barburim') of the table of "
                          "Solomon, 1 Kgs 4:23 (5:3): the interpretations (cocks, capons, birds of the vivarium, "
                          "birds from Barbary) and Bochart's own, the choicest fattened fowl",
                 "terms": '"barburim"/"barbur" stay as printed (never "fowl", "swans" or "geese" for the Hebrew '
                          'word: the identity of the bird is what the chapter argues about); "saginatus" -> '
                          '"fattened"; "altilia"/"altiles" -> "fattened fowl"; "capo" -> "capon"; "gallus" -> '
                          '"cock"; "vivarium" -> "vivarium"; "bibar" stays as printed;'},
    "tukkiyim": {"vol": 2, "pages": list(range(709, 722)),
                 "title": "Part 2, Book 1, chapter 20: The peacocks (vol. 2, pp. 709–720)",
                 "start": r"^CAP\.\s*XX\.", "end": r"^CAP\.\s*XXI\.", "first_col": 135,
                 "about": "the chapter on the תכיים (thuccijim) that the ships of Solomon brought (1 Kgs 10:22; "
                          "2 Chr 9:21), which Bochart takes as peacocks, with the peacock in the ancient authors, "
                          "and on ivory and ebony (hobnim, Ezek 27:15)",
                 "terms": '"pavo" -> "peacock"; "psittacus" -> "parrot"; "simia" -> "ape"; "cercopithecus" -> '
                          '"long-tailed monkey"; "ebur" -> "ivory"; "ebenus"/"hebenus" -> "ebony"; "thuccijim", '
                          '"hobnim", "algumim" (Bochart\'s romanized Hebrew) stay as printed;'},
    # Tranche 5, 13-Nov-2026: Part 2, Book 1, chs. 21-23 (tsippor and the sparrow: the end of the clean
    # birds) and Book 2 (the unclean birds), chs. 1-9: the eagle and the birds of prey of Lev 11:13-14 and
    # Deut 14:12-13. Chapter heads: uv run find_chapters.py 737 850 (the MDZ OCR does not have the heads
    # of chs. 22 and 23, pp. 727 and 735: they were found in the Opus OCR, logs/cols_t5.py). No first_col
    # where the column mark stands in the chapter head itself (Book 2 chs. 1, 4 and 7).
    "tsippor": {"vol": 2, "pages": list(range(721, 728)),
                "title": "Part 2, Book 1, chapter 21: The word tsippor, which means any bird and specially the "
                         "sparrow (vol. 2, pp. 721–727)",
                "start": r"^CAP\.\s*XXI\.", "end": r"^CAP\.\s*XXII\.", "first_col": 145,
                "about": "the chapter on the Hebrew צפור (tsippor), which means any bird and specially the "
                         "sparrow: its kinds according to the Arabs, the house sparrow and its chirping",
                "terms": '"passer" -> "sparrow"; "avis"/"avicula" -> "bird"/"little bird"; "pipitus"/"pipire" -> '
                         '"chirping"/"chirp"; "tsippor" (Bochart\'s romanized Hebrew) stays as printed;'},
    "passer-prophetae": {"vol": 2, "pages": list(range(727, 736)),
                         "title": "Part 2, Book 1, chapter 22: Nine passages of the Prophets that some "
                                  "interpreters refer to sparrows, most of them not certain (vol. 2, pp. 727–735)",
                         "start": r"^CAP\.\s*XXII\.", "end": r"^CAP\.\s*XXIII\.", "first_col": 150,
                         "about": "the chapter that examines nine passages of the Old Testament in which some "
                                  "interpreters take צפור (tsippor) as the sparrow (Lev 14; Job 40:24; Ps 11:1; "
                                  "84:4; 102:8; 104:17; 124:7; Eccl 12:4; Lam 3:52)",
                         "terms": '"passer" -> "sparrow"; "avis"/"avicula" -> "bird"/"little bird"; "tsippor" and '
                                  '"tsipporim" (Bochart\'s romanized Hebrew) stay as printed;'},
    "passer-providentia": {"vol": 2, "pages": list(range(735, 740)),
                           "title": "Part 2, Book 1, chapter 23: The providence of God for sparrows and little "
                                    "birds, in Matt 10:29 and Luke 12:6 (vol. 2, pp. 735–738)",
                           "start": r"^CAP\.\s*XXIII\.", "end": r"PARS SECUNDA", "first_col": 157,
                           "about": "the chapter on the sparrows sold for an assarion (Matt 10:29; Luke 12:6): "
                                    "the price, and the providence of God for the smallest birds",
                           "terms": '"passer" -> "sparrow"; "avicula" -> "little bird"; "assarium" -> "assarion"; '
                                    '"as" (the coin) -> "as"; "semissis" -> "half an as"; "providentia" -> '
                                    '"providence";'},
    "aquila": {"vol": 2, "pages": list(range(739, 751)),
               "title": "Part 2, Book 2, chapter 1: The eagle, king of the birds: its name, beak, talons, "
                        "plumage, baldness, renewal and colour (vol. 2, pp. 739–749)",
               "start": r"PARS SECUNDA", "end": r"^CAP\.\s*II\.",
               "about": "the first chapter of Book 2 (the unclean birds, in the order of Lev 11:13 and Deut "
                        "14:12): the eagle, נשר (nesher), king of the birds; its name, beak, talons, plumage, "
                        "baldness (Mic 1:16), renewal (Ps 103:5) and colour",
               "terms": '"aquila" -> "eagle"; "vultur" -> "vulture"; "accipiter" -> "hawk"; "milvus" -> "kite"; "ossifraga" -> "ossifrage"; "haliaeetus" -> "haliaeetus" (the name is kept; "aquila marina" -> "sea eagle"); "pullus" -> "chick" (of the eagle: "eaglet" is allowed); "nesher" (Bochart\'s romanized Hebrew) stays as printed;'},
    "aquila-volatus": {"no_id": {"Jonathan": 1}, "vol": 2, "pages": list(range(750, 760)),
                       "title": "Part 2, Book 2, chapter 2: The eagle's wings, flight, nest, sight and food "
                                "(vol. 2, pp. 750–758)",
                       "start": r"^CAP\.\s*II\.", "end": r"^CAP\.\s*III\.", "first_col": 169,
                       "about": "the chapter on the eagle's wings, flight, nest, sight and food in Scripture and "
                                "in the ancient authors",
                       "terms": '"aquila" -> "eagle"; "vultur" -> "vulture"; "accipiter" -> "hawk"; "milvus" -> "kite"; "ossifraga" -> "ossifrage"; "haliaeetus" -> "haliaeetus" (the name is kept; "aquila marina" -> "sea eagle"); "pullus" -> "chick" (of the eagle: "eaglet" is allowed); "nesher" (Bochart\'s romanized Hebrew) stays as printed;'},
    "aquila-pulli": {"vol": 2, "pages": list(range(759, 767)),
                     "title": "Part 2, Book 2, chapter 3: The eagle's love for its young, from Deut 32:11 "
                              "(vol. 2, pp. 759–766)",
                     "start": r"^CAP\.\s*III\.", "end": r"^CAP\.\s*IV\.", "first_col": 176,
                     "about": "the chapter on the eagle's love for its young (Deut 32:11: the eagle stirs up "
                              "its nest, hovers over its young and carries them on its wings), and on the trial "
                              "of the young by the sun",
                     "terms": '"aquila" -> "eagle"; "vultur" -> "vulture"; "accipiter" -> "hawk"; "milvus" -> "kite"; "ossifraga" -> "ossifrage"; "haliaeetus" -> "haliaeetus" (the name is kept; "aquila marina" -> "sea eagle"); "pullus" -> "chick" (of the eagle: "eaglet" is allowed); "nesher" (Bochart\'s romanized Hebrew) stays as printed; "nidus" -> "nest" (also where Bochart says it means the brood);'},
    "aquila-mystica": {"vol": 2, "pages": list(range(766, 771)),
                       "title": "Part 2, Book 2, chapter 4: Mystical eagles: God, the angels, the faithful, the "
                                "great kings, above all the Assyrian (vol. 2, pp. 766–770)",
                       "start": r"^CAP\.\s*IV\.", "end": r"^CAP\.\s*V\.",
                       "about": "the chapter on what Scripture compares with the eagle: God (Exod 19:4), the "
                                "angels, the faithful, empires and great kings, above all the king of Assyria "
                                "and Babylon (Ezek 17; Dan 7:4)",
                       "terms": '"aquila" -> "eagle"; "vultur" -> "vulture"; "accipiter" -> "hawk"; "milvus" -> "kite"; "ossifraga" -> "ossifrage"; "haliaeetus" -> "haliaeetus" (the name is kept; "aquila marina" -> "sea eagle"); "pullus" -> "chick" (of the eagle: "eaglet" is allowed); "nesher" (Bochart\'s romanized Hebrew) stays as printed;'},
    "peres": {"vol": 2, "pages": list(range(770, 775)),
              "title": "Part 2, Book 2, chapter 5: Peres is the ossifrage (vol. 2, pp. 770–773)",
              "start": r"^CAP\.\s*V\.", "end": r"^CAP\.\s*VI\.", "first_col": 185,
              "about": "the chapter arguing that the Hebrew פרס (peres) of Lev 11:13 and Deut 14:12, which the "
                       "Greek renders γρύψ, is the ossifrage, the bird that breaks bones",
              "terms": '"aquila" -> "eagle"; "vultur" -> "vulture"; "accipiter" -> "hawk"; "milvus" -> "kite"; "falco" -> "falcon"; "ossifraga" -> "ossifrage"; "gryps"/"gryphus" -> "griffin"; "haliaeetus", "melanaeetus", "aesalon" -> the name is kept; "peres" stays "peres" (the identity of the bird is what the chapter argues);'},
    "oznija": {"vol": 2, "pages": list(range(774, 778)),
               "title": "Part 2, Book 2, chapter 6: Oznija is not the haliaeetus, as most hold, but the "
                        "melanaeetus or Valerian eagle (vol. 2, pp. 774–776)",
               "start": r"^CAP\.\s*VI\.", "end": r"^CAP\.\s*VII\.", "first_col": 188,
               "about": "the chapter arguing that the Hebrew עזניה (oznija) of Lev 11:13 and Deut 14:12 is not "
                        "the haliaeetus (sea eagle, osprey), as most interpreters hold, but the melanaeetus "
                        "(black eagle) or Valerian eagle",
               "terms": '"aquila" -> "eagle"; "vultur" -> "vulture"; "accipiter" -> "hawk"; "milvus" -> "kite"; "falco" -> "falcon"; "ossifraga" -> "ossifrage"; "gryps"/"gryphus" -> "griffin"; "haliaeetus", "melanaeetus", "aesalon" -> the name is kept; "aquila Valeria" -> "Valerian eagle"; "oznija" stays "oznija";'},
    "daah": {"vol": 2, "pages": list(range(777, 780)),
             "title": "Part 2, Book 2, chapter 7: The kite is better called daa, from its flight, as in "
                      "Leviticus, than raa, from its sight, as in Deuteronomy (vol. 2, pp. 777–778)",
             "start": r"^CAP\.\s*VII\.", "end": r"^CAP\.\s*VIII\.",
             "about": "the chapter on the bird written דאה (daa) in Lev 11:14 and ראה (raa) in Deut 14:13, "
                      "the kite: the scribes confuse ד and ר, and the name from flying (daa) is the better "
                      "one",
             "terms": '"aquila" -> "eagle"; "vultur" -> "vulture"; "accipiter" -> "hawk"; "milvus" -> "kite"; "falco" -> "falcon"; "ossifraga" -> "ossifrage"; "gryps"/"gryphus" -> "griffin"; "haliaeetus", "melanaeetus", "aesalon" -> the name is kept; "daa" and "raa" stay as printed (the difference of ד and ר is the subject: copy '
                      'each Hebrew word exactly as the source has it);'},
    "ajah": {"vol": 2, "pages": list(range(779, 783)),
             "title": "Part 2, Book 2, chapter 8: Aja is a kind of hawk, which the ancients call aesalon, "
                      "the Germans Smirle, the French esmerillon (vol. 2, pp. 779–782)",
             "start": r"^CAP\.\s*VIII\.", "end": r"^CAP\.\s*IX\.", "first_col": 192,
             "about": "the chapter arguing that the Hebrew איה (aja) of Lev 11:14, Deut 14:13 and Job 28:7 is "
                      "a kind of hawk, the aesalon of the ancients, the merlin (German Smirle, French "
                      "esmerillon)",
             "terms": '"aquila" -> "eagle"; "vultur" -> "vulture"; "accipiter" -> "hawk"; "milvus" -> "kite"; "falco" -> "falcon"; "ossifraga" -> "ossifrage"; "gryps"/"gryphus" -> "griffin"; "haliaeetus", "melanaeetus", "aesalon" -> the name is kept; "esmerillon"/"Smirle" stay as printed ("merlin" may follow in brackets once); '
                      '"aja" stays "aja";'},
    "dajah": {"vol": 2, "pages": list(range(782, 788)),
              "title": "Part 2, Book 2, chapter 9: Daja is the black vulture (vol. 2, pp. 782–786)",
              "start": r"^CAP\.\s*IX\.", "end": r"^CAP\.\s*X\.", "first_col": 195,
              "about": "the chapter arguing that the Hebrew דיה (daja) of Deut 14:13 and Isa 34:15 is not the "
                       "kite but the black vulture",
              "terms": '"aquila" -> "eagle"; "vultur" -> "vulture"; "accipiter" -> "hawk"; "milvus" -> "kite"; "falco" -> "falcon"; "ossifraga" -> "ossifrage"; "gryps"/"gryphus" -> "griffin"; "haliaeetus", "melanaeetus", "aesalon" -> the name is kept; "vultur niger" -> "black vulture"; "daja" stays "daja";'},
    # Tranche 6, 14-Nov-2026: Part 2, Book 2, chs. 10-17 (the raven, chs. 10-13; the ostrich, chs. 14-17), to
    # the end of vol. 2 (p. 870: the colophon ends the last chapter). Chapter heads: uv run
    # find_chapters.py 800 886 (the same eight heads are in the Opus OCR). No first_col where the column
    # mark stands in the chapter head itself (chs. 12, 13 and 16).
    "corvus": {"vol": 2, "pages": list(range(787, 795)),
               "title": "Part 2, Book 2, chapter 10: The raven: its names, voice, colour, haunts, food and kinds "
                        "(vol. 2, pp. 787–794)",
               "start": r"^CAP\.\s*X\.", "end": r"^CAP\.\s*XI\.", "first_col": 197,
               "about": "the chapter on the raven, Hebrew ערב (oreb): its names, its croaking and blackness, "
                        "where it lives, what it eats, and its kinds",
               "terms": '"corvus" -> "raven"; "cornix" -> "crow"; "monedula" -> "jackdaw"; "pica" -> "magpie"; "pullus" -> "chick" (of the raven: "young raven" is allowed); "crocitare"/"crocitatio" -> "croak"/"croaking"; "oreb" and "orebim" (Bochart\'s romanized Hebrew) stay as printed;'},
    "corvus-providentia": {"no_id": {"Elias": 99}, "vol": 2, "pages": list(range(794, 801)),
                           "title": "Part 2, Book 2, chapter 11: The providence of God for ravens "
                                    "(vol. 2, pp. 794–800)",
                           "start": r"^CAP\.\s*XI\.", "end": r"^CAP\.\s*XII\.", "first_col": 203,
                           "about": "the chapter on the passages that say God feeds the ravens and their young "
                                    "(Job 38:41; Ps 147:9; Luke 12:24), and on the old belief that the raven "
                                    "leaves its chicks",
                           "terms": '"corvus" -> "raven"; "cornix" -> "crow"; "monedula" -> "jackdaw"; "pica" -> "magpie"; "pullus" -> "chick" (of the raven: "young raven" is allowed); "crocitare"/"crocitatio" -> "croak"/"croaking"; "oreb" and "orebim" (Bochart\'s romanized Hebrew) stay as printed;'},
    "corvus-noachi": {"no_id": {"Elias": 99}, "vol": 2, "pages": list(range(800, 807)),
                      "title": "Part 2, Book 2, chapter 12: The raven that Noah sent out of the ark "
                               "(vol. 2, pp. 800–806)",
                      "start": r"^CAP\.\s*XII\.", "end": r"^CAP\.\s*XIII\.",
                      "about": "the chapter on the raven that Noah sent out of the ark (Gen 8:7): whether it "
                               "came back, and why the Greek and the Latin say that it did not",
                      "terms": '"corvus" -> "raven"; "cornix" -> "crow"; "monedula" -> "jackdaw"; "pica" -> "magpie"; "pullus" -> "chick" (of the raven: "young raven" is allowed); "crocitare"/"crocitatio" -> "croak"/"croaking"; "oreb" and "orebim" (Bochart\'s romanized Hebrew) stay as printed; "columba" -> "dove"; "arca" -> "ark";'},
    "corvus-eliae": {"no_id": {"Elias": 99}, "vol": 2, "pages": list(range(806, 812)),
                     "title": "Part 2, Book 2, chapter 13: The ravens that brought bread and meat to Elijah at "
                              "the brook Cherith, 1 Kgs 17 (vol. 2, pp. 806–811)",
                     "start": r"^CAP\.\s*XIII\.", "end": r"^CAP\.\s*XIV\.",
                     "about": "the chapter on the ערבים (orebim) that fed Elijah at the brook Cherith (1 Kgs "
                              "17:4-6): Bochart defends the ravens against those who read merchants, Arabs or "
                              "the men of a town Orbo",
                     "terms": '"corvus" -> "raven"; "cornix" -> "crow"; "monedula" -> "jackdaw"; "pica" -> "magpie"; "pullus" -> "chick" (of the raven: "young raven" is allowed); "crocitare"/"crocitatio" -> "croak"/"croaking"; "oreb" and "orebim" (Bochart\'s romanized Hebrew) stay as printed; "mercatores" -> "merchants"; "Arabes" -> "Arabs";'},
    "bath-jaana": {"no_id": {"Paulus": 1}, "vol": 2, "pages": list(range(811, 831)),
                   "title": "Part 2, Book 2, chapter 14: Bath jaana is the female ostrich (vol. 2, pp. 811–830)",
                   "start": r"^CAP\.\s*XIV\.", "end": r"^CAP\.\s*XV\.", "first_col": 217,
                   "about": "the chapter arguing that the Hebrew בת יענה (bath jaana) of Lev 11:16, Deut 14:15 "
                            "and the Prophets is not the owl but the female ostrich",
                   "terms": '"struthio", "struthiocamelus", "struthio-camelus" -> "ostrich"; "ulula" -> "owl"; "noctua" -> "little owl"; "bubo" -> "eagle owl"; "siren" -> "siren"; "draco" -> "dragon"; "ciconia" -> "stork"; "accipiter" -> "hawk"; "ardea" -> "heron"; "pavo" -> "peacock"; "bath jaana", "jaana", "jeenim", "thachmas", "renanim", "chasida", "notsa" (Bochart\'s romanized Hebrew) stay as printed;'},
    "thachmas": {"vol": 2, "pages": list(range(830, 839)),
                 "title": "Part 2, Book 2, chapter 15: Thachmas is the male ostrich (vol. 2, pp. 830–838)",
                 "start": r"^CAP\.\s*XV\.", "end": r"^CAP\.\s*XVI\.", "first_col": 231,
                 "about": "the chapter arguing that the Hebrew תחמס (thachmas) of Lev 11:16 and Deut 14:15 is "
                          "not a bird of prey (the night hawk, the owl, the swallow) but the male ostrich",
                 "terms": '"struthio", "struthiocamelus", "struthio-camelus" -> "ostrich"; "ulula" -> "owl"; "noctua" -> "little owl"; "bubo" -> "eagle owl"; "siren" -> "siren"; "draco" -> "dragon"; "ciconia" -> "stork"; "accipiter" -> "hawk"; "ardea" -> "heron"; "pavo" -> "peacock"; "bath jaana", "jaana", "jeenim", "thachmas", "renanim", "chasida", "notsa" (Bochart\'s romanized Hebrew) stay as printed; "falco" -> "falcon"; "hirundo" -> "swallow";'},
    "struthio-iob": {"vol": 2, "pages": list(range(838, 855)),
                     "title": "Part 2, Book 2, chapter 16: The most obscure passage on the ostrich, Job 39:13 "
                              "(vol. 2, pp. 838–854)",
                     "start": r"^CAP\.\s*XVI\.", "end": r"^CAP\.\s*XVII\.",
                     "about": "the chapter on the first verse of the description of the ostrich in Job 39 (v. 13 "
                              "in the modern count, 16 in Bochart's): כנף רננים נעלסה אם אברה חסידה ונצה, with "
                              "the ancient versions and Bochart's own interpretation",
                     "terms": '"struthio", "struthiocamelus", "struthio-camelus" -> "ostrich"; "ulula" -> "owl"; "noctua" -> "little owl"; "bubo" -> "eagle owl"; "siren" -> "siren"; "draco" -> "dragon"; "ciconia" -> "stork"; "accipiter" -> "hawk"; "ardea" -> "heron"; "pavo" -> "peacock"; "bath jaana", "jaana", "jeenim", "thachmas", "renanim", "chasida", "notsa" (Bochart\'s romanized Hebrew) stay as printed; "ala" -> "wing"; "penna" -> "feather" (or "wing" where the sense needs it); '
                              '"pluma" -> "plumage";'},
    "struthio-iob-reliqua": {"vol": 2, "pages": list(range(854, 871)),
                             "title": "Part 2, Book 2, chapter 17: The rest of Job on the ostrich, Job 39:14-18 "
                                      "(vol. 2, pp. 854–870)",
                             "start": r"^CAP\.\s*XVII\.", "end": r"LIPSIAE", "first_col": 249,
                             "about": "the chapter on the rest of the description of the ostrich in Job 39 "
                                      "(vv. 14-18 in the modern count): the eggs left on the ground, the "
                                      "hardness to its young, its want of wisdom, and its speed, which laughs "
                                      "at the horse and its rider",
                             "terms": '"struthio", "struthiocamelus", "struthio-camelus" -> "ostrich"; "ulula" -> "owl"; "noctua" -> "little owl"; "bubo" -> "eagle owl"; "siren" -> "siren"; "draco" -> "dragon"; "ciconia" -> "stork"; "accipiter" -> "hawk"; "ardea" -> "heron"; "pavo" -> "peacock"; "bath jaana", "jaana", "jeenim", "thachmas", "renanim", "chasida", "notsa" (Bochart\'s romanized Hebrew) stay as printed; "ovum" -> "egg"; "pullus" -> "chick";'},
    # Tranche 7, 15-Nov-2026: vol. 3 begins. Part 2, Book 2, chs. 18-33 (the rest of the unclean birds of Lev 11,
    # pp. 1-124; Book 3, the serpents, begins on p. 125). Drafted by draft_entries.py from the heads in the Opus
    # OCR (the MDZ OCR has no head for ch. 29). The last chapter ends with its pages (the end pattern is not met).
    "sachaph": {"vol": 3, "pages": list(range(1, 6)),
        "title": 'Part 2, Book 2, chapter 18: Sachaph is the gull, or the cepphus (vol. 3, pp. 1–5)',
        "start": r"^CAP\.\s*XVIII\.", "end": r"^CAP\.\s*XIX\.",
        "about": 'the chapter arguing that the Hebrew שחף (sachaph) of Lev 11:16 and Deut 14:15 is the gull (larus) or the cepphus, a very light sea bird, and explaining from it the Greek κεπφωθείς of Prov 7:22',
        "terms": _T7 + '"sachaph" stays as printed;'},
    "nets": {"vol": 3, "pages": list(range(5, 15)),
        "title": 'Part 2, Book 2, chapter 19: The hawk, nets in Hebrew (vol. 3, pp. 5–14)',
        "start": r"^CAP\.\s*XIX\.", "end": r"^CAP\.\s*XX\.", "first_col": 265,
        "about": 'the chapter on the hawk, Hebrew נץ (nets): the agreement of the versions, the kinds of hawk, and its flight toward the south in Job 39:26',
        "terms": _T7 + '"nets" stays as printed;'},
    "chos": {"vol": 3, "pages": list(range(14, 21)),
        "title": 'Part 2, Book 2, chapter 20: Whether chos is a night bird (eagle owl, little owl, owl, night raven) or the onocrotalus (vol. 3, pp. 14–20)',
        "start": r"^CAP\.\s*XX\.", "end": r"^CAP\.\s*XXI\.", "first_col": 272,
        "about": 'the chapter on the bird כוס (chos) of Lev 11:17, Deut 14:16 and Ps 102:7: whether it is a kind of night bird (eagle owl, little owl, owl, night raven) or, very differently, the onocrotalus',
        "terms": _T7 + '"chos" stays as printed;'},
    "salach": {"vol": 3, "pages": list(range(20, 25)),
        "title": 'Part 2, Book 2, chapter 21: Salach is rightly rendered catarrhactes by the Greeks (vol. 3, pp. 20–24)',
        "start": r"^CAP\.\s*XXI\.", "end": r"^CAP\.\s*XXII\.", "first_col": 277,
        "about": 'the chapter arguing that the Greek version is right to render the Hebrew שלך (salach) of Lev 11:17 and Deut 14:17 by καταρράκτης (catarrhactes), a sea bird that throws itself down on fish',
        "terms": _T7 + '"salach" stays as printed; "mergus" -> "diver";'},
    "jansuph": {"vol": 3, "pages": list(range(24, 32)),
        "title": 'Part 2, Book 2, chapter 22: Jansuph is the eagle owl (vol. 3, pp. 24–31)',
        "start": r"^CAP\.\s*XXII\.", "end": r"^CAP\.\s*XXIII\.",
        "about": 'the chapter arguing that the Hebrew ינשוף (jansuph, jansoph) of Lev 11:17, Deut 14:16 and Isa 34:11 is the eagle owl (bubo), against the ibis of the Greek and Latin versions',
        "terms": _T7 + '"jansuph" and "jansoph" stay as printed; "ibis" -> "ibis";'},
    "thinsemeth": {"vol": 3, "pages": list(range(31, 41)),
        "title": 'Part 2, Book 2, chapter 23: Thinsemeth is the little owl (vol. 3, pp. 31–40)',
        "start": r"^CAP\.\s*XXIII\.", "end": r"^CAP\.\s*XXIV\.", "first_col": 285,
        "about": 'the chapter arguing that the bird תנשמת (thinsemeth) of Lev 11:18 and Deut 14:16 (the same word is a lizard in Lev 11:30) is the little owl (noctua), against the porphyrio, the swan, the ibis and the bat of the versions',
        "terms": _T7 + '"thinsemeth" stays as printed; "cygnus"/"olor" -> "swan"; "vespertilio" -> "bat"; "talpa" -> "mole"; "chamaeleon" -> "chameleon";'},
    "kaath": {"vol": 3, "pages": list(range(40, 49)),
        "title": 'Part 2, Book 2, chapter 24: Kaath is the pelican, and the heron, above all the bittern (vol. 3, pp. 40–48)',
        "start": r"^CAP\.\s*XXIV\.", "end": r"^CAP\.\s*XXV\.", "first_col": 292,
        "about": 'the chapter arguing that the Hebrew קאת (kaath) of Lev 11:18, Ps 102:7, Isa 34:11 and Zeph 2:14 is the pelican and also the heron, above all the ardea stellaris or butaurus (the bittern), named from its vomiting (קוא)',
        "terms": _T7 + '"kaath" stays as printed; "ardea stellaris"/"butaurus"/"botaurus" -> "bittern";'},
    "racham-interpretationes": {"vol": 3, "pages": list(range(48, 57)),
        "title": 'Part 2, Book 2, chapter 25: The interpretations of the word racham; on the birds serakrak, the swan, the pelican and the bee-eater (vol. 3, pp. 48–56)',
        "start": r"^CAP\.\s*XXV\.", "end": r"^CAP\.\s*XXVI\.", "first_col": 297,
        "about": 'the chapter that reviews the many interpretations of the bird רחם (racham, rachama) of Lev 11:18 and Deut 14:17, with much on the birds שרקרק (serakrak), the swan, the pelican and the merops (bee-eater)',
        "terms": _T7 + '"racham", "rachama" and "serakrak" stay as printed; "cygnus"/"olor" -> "swan"; "merops" -> "bee-eater"; "pica" -> "magpie";'},
    "racham": {"vol": 3, "pages": list(range(56, 66)),
        "title": 'Part 2, Book 2, chapter 26: From the Arabic it is proved that racham is a kind of vulture (vol. 3, pp. 56–65)',
        "start": r"^CAP\.\s*XXVI\.", "end": r"^CAP\.\s*XXVII\.",
        "about": 'the chapter proving from Arabic, where رخم (racham, rachama) is still the name of a bird, that the Hebrew רחם is a kind of vulture; long quotations from Damir and other Arabic writers',
        "terms": _T7 + '"racham" and "rachama" stay as printed;'},
    "racham-objectiones": {"vol": 3, "pages": list(range(65, 79)),
        "title": 'Part 2, Book 2, chapter 27: Answers to what can be objected to the chapter before (vol. 3, pp. 65–78)',
        "start": r"^CAP\.\s*XXVII\.", "end": r"^CAP\.\s*XXVIII\.", "first_col": 311,
        "about": 'the chapter answering the objections that can be made to the chapter before, where the racham was shown to be a vulture: what the Arabs say of its form, colour, food and habits',
        "terms": _T7 + '"racham" and "rachama" stay as printed;'},
    "chasida-interpretationes": {"vol": 3, "pages": list(range(78, 86)),
        "title": 'Part 2, Book 2, chapter 28: The interpretations of the word chasida, or asida (vol. 3, pp. 78–85)',
        "start": r"^CAP\.\s*XXVIII\.", "end": r"^CAP\.\s*XXIX\.", "first_col": 321,
        "about": 'the chapter that reviews the interpretations of the bird חסידה (chasida, hasida, asida), named from piety (חסד), of Lev 11:19, Deut 14:18, Ps 104:17, Jer 8:7, Zech 5:9 and Job 39:13',
        "terms": _T7 + '"chasida", "hasida" and "asida" stay as printed (each as the print has it);'},
    "chasida": {"vol": 3, "pages": list(range(85, 98)),
        "title": 'Part 2, Book 2, chapter 29: Chasida is the stork (vol. 3, pp. 85–97)',
        "start": r"^CAP\.\s*XXIX\.", "end": r"^CAP\.\s*XXX\.", "first_col": 326,
        "about": 'the chapter proving that חסידה (hasida) is the stork: from its name (the pious bird), its care for its parents, its passage at fixed times (Jer 8:7), its nest in the fir trees (Ps 104:17) and its wings (Zech 5:9)',
        "terms": _T7 + '"chasida", "hasida" and "asida" stay as printed (each as the print has it); "abies" -> "fir"; "grus" -> "crane"; "hirundo" -> "swallow"; "turtur" -> "turtledove";'},
    "anapha": {"vol": 3, "pages": list(range(97, 108)),
        "title": 'Part 2, Book 2, chapter 30: The Hebrew word anapha means some very angry bird; perhaps the zummag of the Arabs, a kind of eagle named from anger (vol. 3, pp. 97–107)',
        "start": r"^CAP\.\s*XXX\.", "end": r"^CAP\.\s*XXXI\.",
        "about": 'the chapter arguing that the Hebrew אנפה (anapha) of Lev 11:19 and Deut 14:18 means a very angry bird (from אנף, to be angry): perhaps the زمج (zummag) of the Arabs, a kind of eagle that has its name from anger; the charadrius of the Greek and the heron of other versions are examined',
        "terms": _T7 + '"anapha" and "zummag" stay as printed; "charadrius" -> the name is kept;'},
    "dukiphath": {"vol": 3, "pages": list(range(107, 116)),
        "title": 'Part 2, Book 2, chapter 31: Dukiphath is the hoopoe (vol. 3, pp. 107–115)',
        "start": r"^CAP\.\s*XXXI\.", "end": r"^CAP\.\s*XXXII\.", "join_notes": [109],
        "about": 'the chapter proving that the Hebrew דוכיפת (dukiphath) of Lev 11:19 and Deut 14:18 is the hoopoe, as the Greek and Latin versions have it, against the wild cock (the tarnegol bara of the rabbis, with the story of the shamir) and other birds; the composition of the name',
        "terms": _T7 + '"dukiphath" stays as printed; "gallus montanus"/"gallus silvestris" -> "mountain cock"/"wild cock"; "urogallus" -> the name is kept; "tarnegol bara", "nagar tura", "samir" (Bochart\'s romanized words) stay as printed;'},
    "atalleph": {"vol": 3, "pages": list(range(115, 120)),
        "title": 'Part 2, Book 2, chapter 32: Atalleph is the bat (vol. 3, pp. 115–119)',
        "start": r"^CAP\.\s*XXXII\.", "end": r"^CAP\.\s*XXXIII\.", "first_col": 349,
        "about": 'the chapter proving that the Hebrew עטלף (atalleph) of Lev 11:19, Deut 14:18 and Isa 2:20 is the bat, with which Moses ends the list of the unclean birds as he began it with the eagle; the name explained',
        "terms": _T7 + '"atalleph" stays as printed; "vespertilio" -> "bat"; "talpa" -> "mole";'},
    "aves-immundae": {"vol": 3, "pages": list(range(119, 125)),
        "title": 'Part 2, Book 2, chapter 33: The number of the unclean birds and their general marks; how their prohibition bore on morals (vol. 3, pp. 119–124)',
        "start": r"^CAP\.\s*XXXIII\.", "end": r"^CAP\.\s*XXXIV\.", "first_col": 352,
        "about": 'the chapter that closes the book of the unclean birds: their number and their general marks, from Maimonides, On Forbidden Foods, and the Talmud, and how the fathers and others referred the prohibition to morals',
        "terms": _T7 + '"immundus" -> "unclean"; "mundus" -> "clean"; "ingluvies" -> "crop"; "ventriculus" -> "gizzard" (where it is the bird\'s second stomach); "digitus" -> "toe" (of a bird);'},
    # Tranche 8, 16-Nov-2026: Part 2, Book 3 (the serpents), chs. 1-10, vol. 3, pp. 125-193 (ch. 11, the kippoz, begins
    # on p. 194). Drafted by draft_entries.py from the heads in the voted OCR. All steps ran synchronously.
    "ephe": {"no_id": {"Schultens": 99}, "vol": 3, "pages": list(range(125, 139)),
        "title": 'Part 2, Book 3, chapter 1: Ephe is the viper (vol. 3, pp. 125–138)',
        "start": r"^CAP\.\s*I\.", "end": r"^CAP\.\s*II\.", "first_col": 357,
        "about": 'the chapter that opens the book of the serpents with the list of their Hebrew names and argues that אפעה (ephe) of Job 20:16, Isa 30:6 and Isa 59:5 is the viper, the Arabic افعي; long quotations from Avicenna and Damir',
        "terms": _T8 + '"ephe" and "alephe"/"alaphai" stay as printed;'},
    "vipera-pauli": {"no_id": {"Erasmus": 1}, "vol": 3, "pages": list(range(138, 150)),
        "title": 'Part 2, Book 3, chapter 2: On the viper of Paul, and why the Pharisees are called a brood of vipers (vol. 3, pp. 138–149)',
        "start": r"^CAP\.\s*II\.", "end": r"^CAP\.\s*III\.", "first_col": 367,
        "about": 'the chapter on the viper that fastened on the hand of Paul in Malta (Acts 28:3-6) and on why John and Christ call the Pharisees γεννήματα ἐχιδνῶν, a brood of vipers (Matt 3:7, 12:34, 23:33)',
        "terms": _T8 + '"progenies viperarum" -> "brood of vipers"; "sarmenta" -> "brushwood";'},
    "chephir-sachal": {"vol": 3, "join_notes": [151], "pages": list(range(149, 155)),
        "title": 'Part 2, Book 3, chapter 3: Chephir and sachal are names not only of lions, as is commonly held, but also of serpents (vol. 3, pp. 149–154)',
        "start": r"^CAP\.\s*III\.", "end": r"^CAP\.\s*IV\.", "first_col": 375,
        "about": 'the chapter arguing that כפיר (chephir) and שחל (sachal), commonly names of the lion, are in Ps 91:13 (and sachal in Job 4:10, 28:8) also names of serpents',
        "terms": _T8 + '"chephir" and "sachal" stay as printed; "leo" -> "lion";'},
    "achsub": {"vol": 3, "pages": list(range(154, 157)),
        "title": 'Part 2, Book 3, chapter 4: Achsub is the asp (vol. 3, pp. 154–156)',
        "start": r"^CAP\.\s*IV\.", "end": r"^CAP\.\s*V\.", "first_col": 379,
        "about": 'the short chapter arguing that עכשוב (achsub) of Ps 140:4 is the asp, against the spider of the Chaldee',
        "terms": _T8 + '"achsub" stays as printed; "aranea" -> "spider";'},
    "pethen": {"no_id": {"Pococke": 1}, "vol": 3, "pages": list(range(156, 162)),
        "title": 'Part 2, Book 3, chapter 5: Pethen is the asp (vol. 3, pp. 156–161)',
        "start": r"^CAP\.\s*V\.", "end": r"^CAP\.\s*VI\.", "first_col": 380,
        "about": 'the chapter arguing that פתן (pethen) of Deut 32:33, Job 20:14.16, Ps 58:5, Ps 91:13 and Isa 11:8 is the asp, from its incurable poison and its size, with the Greek name Python',
        "terms": _T8 + '"pethen" and "pethanim" stay as printed;'},
    "aspis-surda": {"vol": 3, "pages": list(range(161, 178)),
        "title": 'Part 2, Book 3, chapter 6: On the deaf asp, which is said to stop its ear so as not to hear the voice of the charmers (Ps 58:5–6) (vol. 3, pp. 161–177)',
        "start": r"^CAP\.\s*VI\.", "end": r"^CAP\.\s*VII\.", "first_col": 384,
        "about": 'the chapter on the deaf asp of Ps 58:5-6 that stops its ear against the voice of the charmers: the charming of serpents in Greek, Latin, Hebrew and Arabic writers, and the senses in which the asp is called deaf',
        "terms": _T8 + '"incantator" -> "charmer"; "incantare" -> "to charm"; "incantatio" -> "charm" or "incantation"; "surdus" -> "deaf"; "Psylli" and "Marsi" stay;'},
    "tseboa-serpens": {"vol": 3, "pages": list(range(177, 181)),
        "title": 'Part 2, Book 3, chapter 7: Tseboa is the varied serpent that the Greeks and the Egyptians called hyaena (vol. 3, pp. 177–180)',
        "start": r"^CAP\.\s*VII\.", "end": r"^CAP\.\s*VIII\.",
        "about": 'the chapter arguing that the valley of Tseboim of 1 Sam 13:18 is named from צבוע (tseboa), a spotted serpent that the Greeks and the Egyptians called hyaena',
        "terms": _T8 + '"tseboa", "bardales", "nephriza" and "nephreza" stay as printed; "hyaena" -> "hyaena"; "varius" -> "varied" or "spotted";'},
    "tsimmaon": {"vol": 3, "pages": list(range(180, 183)),
        "title": 'Part 2, Book 3, chapter 8: Tsimmaon is not the dipsas, as some render after Jerome, but a thirsty place (Deut 8:15) (vol. 3, pp. 180–182)',
        "start": r"^CAP\.\s*VIII\.", "end": r"^CAP\.\s*IX\.", "first_col": 397,
        "about": 'the chapter arguing that צמאון (tsimmaon) of Deut 8:15 is not the serpent dipsas, as Jerome has it, but a thirsty place',
        "terms": _T8 + '"tsimmaon" stays as printed; "siticulosus locus" -> "thirsty place";'},
    "tsepha": {"no_id": {"Schultens": 99}, "vol": 3, "pages": list(range(182, 188)),
        "title": 'Part 2, Book 3, chapter 9: Tsepha, or tsiphoni, is the regulus, or basilisk (vol. 3, pp. 182–187)',
        "start": r"^CAP\.\s*IX\.", "end": r"^CAP\.\s*X\.",
        "about": 'the chapter arguing that צפע (tsepha) and צפעני (tsiphoni) of Prov 23:32, Isa 11:8, 14:29, 59:5 and Jer 8:17 are the regulus or basilisk, from the hiss and the burning poison that the name means',
        "terms": _T8 + '"tsepha", "tsiphoni" and "hurman"/"harmene" stay as printed;'},
    "basilisci-loca": {"no_id": {"Michaelis": 1}, "vol": 3, "join_notes": [192], "pages": list(range(187, 195)),
        "title": 'Part 2, Book 3, chapter 10: Five passages of Scripture on the basilisk are explained (vol. 3, pp. 187–193)',
        "start": r"^CAP\.\s*X\.", "end": r"^CAP\.\s*XI\.", "first_col": 402,
        "about": 'the chapter that explains the five passages of Scripture on the basilisk (צפעני): Prov 23:32, Isa 11:8, Isa 14:29, Isa 59:5 and Jer 8:17',
        "terms": _T8 + '"tsepha" and "tsiphoni" stay as printed; "caverna" -> "den";'},
    # Tranche 9, 17-Nov-2026: Part 2, Book 3 (the serpents), chs. 11-14, and Book 4 (the insects), ch. 1, vol. 3,
    # pp. 194-271. Drafted by draft_entries.py from the heads in the voted OCR. All steps ran synchronously.
    "kippoz": {"no_id": {"Paulus": 99}, "vol": 3, "pages": list(range(194, 206)),
        "title": 'Part 2, Book 3, chapter 11: It is shown that the word קפוז kippoz (Isa 34:15) means neither the hedgehog, as the ancients held, nor a kind of bird, as more recent writers held, but the serpent acontias, or iaculus (vol. 3, pp. 194–205)',
        "start": r"^CAP\.\s*XI\.", "end": r"^CAP\.\s*XII\.",
        "about": 'the chapter arguing that קפוז (kippoz) of Isa 34:15 is not the hedgehog of the old versions nor a bird of the newer interpreters, but the serpent acontias or iaculus, named from its leap (Arabic قفازة)',
        "terms": _T8 + '"kippoz" and "kippod" stay as printed; "acontias" and "iaculus" stay; "ericius"/"hericius"/"erinaceus" -> "hedgehog"; "nidus" -> "nest"; "nidulari" -> "to nest";'},
    "sephiphon": {"vol": 3, "pages": list(range(205, 212)),
        "title": 'Part 2, Book 3, chapter 12: It is shown that שפיפון sephiphon (Gen 49:17) is the cerastes and the haemorrhous (vol. 3, pp. 205–211)',
        "start": r"^CAP\.\s*XII\.", "end": r"^CAP\.\s*XIII\.",
        "about": "the chapter arguing that שפיפון (sephiphon) of Gen 49:17, which Jacob says lies by the path and bites the horse's heels, is the cerastes, and with it the haemorrhous",
        "terms": _T8 + '"sephiphon" stays as printed; "cerastes" and "haemorrhous" stay; "cornutus" -> "horned"; "cornicula" -> "little horns";'},
    "saraph": {"no_id": {"Paulus": 99}, "vol": 3, "pages": list(range(211, 223)),
        "title": 'Part 2, Book 3, chapter 13: It is shown that שרף saraph is the hydrus and the chersydrus; the Israelites bitten by them were healed by the sight of the bronze serpent (vol. 3, pp. 211–222)',
        "start": r"^CAP\.\s*XIII\.", "end": r"^CAP\.\s*XIV\.",
        "about": 'the chapter arguing that the שרף (saraph) of Num 21:6 and Deut 8:15 is the hydrus or chersydrus, and on the bronze serpent at the sight of which the bitten Israelites were healed, a type of Christ (John 3:14)',
        "terms": _T8 + '"saraph" and "seraphim" stay as printed; "hydrus" and "chersydrus" stay; "serpens aeneus" -> "bronze serpent"; "aes" -> "bronze"; "ignitus"/"ardens" -> "burning";'},
    "dracones": {"no_id": {"Paulus": 99}, "vol": 3, "pages": list(range(222, 252)),
        "title": 'Part 2, Book 3, chapter 14: On dragons (vol. 3, pp. 222–250)',
        "start": r"^CAP\.\s*XIV\.", "end": r"LIBER QUARTUS", "first_col": 428,
        "about": 'the chapter that closes the book of the serpents: תנין (thannin) as dragon and as sea monster, the dragons of the ancients (their size, crests, wings and poison), the תנים and תנות of the prophets, and the prudence of the serpent (Matt 10:16)',
        "terms": _T8 + '"thannin", "thannim" and "thannoth" stay as printed; "draco" -> "dragon"; "cetus" -> "sea monster"; "prudens" -> "prudent";'},
    "locustae-nomina": {"no_id": {"Aldrovandus": 99}, "vol": 3, "pages": list(range(251, 272)),
        "title": 'Part 2, Book 4, chapter 1: The names and kinds of the locusts (vol. 3, pp. 251–271)',
        "start": r"^CAP\.\s*I\.", "end": r"^CAP\.\s*II\.", "first_col": 441,
        "about": 'the chapter that opens the book of the insects with the Hebrew names of the locust: ארבה arbe, סלעם solam, חרגל chargol, חגב chagab, גזם gazam, ילק jelek, חסיל chasil, צלצל tselatsal, גוב gob and גבי geba, and the kinds that the Talmud, the Greek versions and the Arabs give for them',
        "terms": _T9 + '"locusta" -> "locust"; "arbe", "solam", "chargol", "chagab", "gazam", "jelek", "chasil", "tselatsal", "gob", "geba" stay as printed; "bruchus", "attelabus", "attacus", "asiracus" -> the name is kept; "eruca" -> "caterpillar"; "gryllus" -> "cricket"; "rubigo" -> "blight";'},
    # Tranche 10, 18-Nov-2026: Part 2, Book 4 (the insects), chs. 2-6 (the locusts in Scripture), vol. 3, pp. 271-326.
    # Drafted by draft_entries.py from the heads in the voted OCR. All steps ran synchronously.
    "locustae-loca": {"vol": 3, "pages": list(range(271, 283)),
        "title": 'Part 2, Book 4, chapter 2: Some obscure passages of Scripture on the locusts are explained (vol. 3, pp. 271–282)',
        "start": r"^CAP\.\s*II\.", "end": r"^CAP\.\s*III\.",
        "about": 'the chapter that explains obscure passages of Scripture on the locusts: the ילק סמר of Jer 51:27, the התכבד כילק of Nah 3:15-17, the locusts without a king that go out in bands (Prov 30:27), and the gathering of the חסיל (Isa 33:4)',
        "terms": _T9 + '"locusta" -> "locust"; "bruchus" -> "bruchus"; "arbe", "gazam", "jelek", "chasil", "gob", "chagab" stay as printed; "rubigo" -> "blight"; "uredo" -> "mildew"; "samar" stays as printed; "horrens" -> "bristling"; "turmae" -> "bands";'},
    "locustae-aegyptiae": {"join_notes": [284], "vol": 3, "pages": list(range(282, 290)),
        "title": 'Part 2, Book 4, chapter 3: On the locusts of Egypt (Exod 10:4) (vol. 3, pp. 282–289)',
        "start": r"^CAP\.\s*III\.", "end": r"^CAP\.\s*IV\.", "first_col": 460,
        "about": 'the chapter on the locusts of the eighth plague of Egypt (Exod 10:4-19), brought by the east wind (קדים kadim) and carried into the Red Sea by the west wind, with later plagues of locusts in Syria and Egypt from the chronicles and the travellers',
        "terms": _T9 + '"locusta" -> "locust"; "bruchus" -> "bruchus"; "arbe", "gazam", "jelek", "chasil", "gob", "chagab" stay as printed; "rubigo" -> "blight"; "uredo" -> "mildew"; "ventus kadim" -> "the kadim wind" or "the east wind"; "plaga" -> "plague";'},
    "locustae-ioel1": {"vol": 3, "pages": list(range(289, 306)),
        "title": 'Part 2, Book 4, chapter 4: What Joel has on the locusts in his first chapter (vol. 3, pp. 289–305)',
        "start": r"^CAP\.\s*IV\.", "end": r"^CAP\.\s*V\.", "first_col": 464,
        "about": 'the chapter on the locusts of Joel 1: the four names of verse 4 (גזם, ארבה, ילק, חסיל), the nation with the teeth of a lion, the vine and fig tree laid bare, and the seeds that shrivel under their clods (עבשו, v. 17)',
        "terms": _T9 + '"locusta" -> "locust"; "bruchus" -> "bruchus"; "arbe", "gazam", "jelek", "chasil", "gob", "chagab" stay as printed; "rubigo" -> "blight"; "uredo" -> "mildew"; "vitis" -> "vine"; "ficus" -> "fig tree"; "gleba" -> "clod";'},
    "locustae-ioel2": {"join_notes": [306], "no_id": {"Elias": 99}, "vol": 3, "pages": list(range(305, 321)),
        "title": 'Part 2, Book 4, chapter 5: What Joel has on the locusts in his second chapter (vol. 3, pp. 305–320)',
        "start": r"^CAP\.\s*V\.", "end": r"^CAP\.\s*VI\.", "first_col": 472,
        "about": 'the chapter on the locusts of Joel 2: the day of darkness, the people spread on the mountains like the dawn, their look like horses and their noise like chariots, the fire before them, and the northern army driven into the eastern and western seas, whose stench goes up (v. 20)',
        "terms": _T9 + '"locusta" -> "locust"; "bruchus" -> "bruchus"; "arbe", "gazam", "jelek", "chasil", "gob", "chagab" stay as printed; "rubigo" -> "blight"; "uredo" -> "mildew"; "aurora" -> "dawn"; "exercitus" -> "army"; "foetor" -> "stench";'},
    "locustae-amos": {"vol": 3, "pages": list(range(320, 327)),
        "title": 'Part 2, Book 4, chapter 6: What the prophet Amos has on the locusts (vol. 3, pp. 320–326)',
        "start": r"^CAP\.\s*VI\.", "end": r"^CAP\.\s*VII\.", "first_col": 483,
        "about": "the chapter on the locusts in Amos: the gazam that ate the gardens, vineyards, figs and olives with blight and mildew (Amos 4:9), and the גוב gob formed at the late growth after the king's mowings (Amos 7:1)",
        "terms": _T9 + '"locusta" -> "locust"; "bruchus" -> "bruchus"; "arbe", "gazam", "jelek", "chasil", "gob", "chagab" stay as printed; "rubigo" -> "blight"; "uredo" -> "mildew"; "gob" stays as printed; "serotinum" -> "the late growth"; "tonsiones regis" -> "the king\'s mowings";'},
    # Tranche 11, 20-Nov-2026: Part 2, Book 4 (the insects), chs. 7-12 (John's locusts, the mystical locusts, the fly,
    # the bees, honey and wax), vol. 3, pp. 326-402. Drafted by draft_entries.py. All steps ran synchronously.
    "locustae-ioannis": {"vol": 3, "pages": list(range(326, 335)),
        "title": 'Part 2, Book 4, chapter 7: That John the Baptist ate real locusts (vol. 3, pp. 326–334)',
        "start": r"^CAP\.\s*VII\.", "end": r"^CAP\.\s*VIII\.",
        "about": 'the chapter that shows that the ἀκρίδες eaten by John the Baptist (Matt 3:4, Mark 1:6) were real locusts and not buds, wild pears or a kind of fish, with the evidence of the Law (Lev 11:22), the Greek and Latin authors, the Talmud and the Arabs on the peoples who eat locusts',
        "terms": _T9 + '"locusta" -> "locust"; "bruchus" -> "bruchus"; "arbe", "gazam", "jelek", "chasil", "gob", "chagab" stay as printed; "akrides" stays as printed; "mel sylvestre" -> "wild honey"; "acridophagi" -> "Acridophagi" (locust-eaters);'},
    "locustae-mysticae": {"no_id": {"Gesner": 99}, "vol": 3, "pages": list(range(334, 342)),
        "title": 'Part 2, Book 4, chapter 8: On the mystical locusts (vol. 3, pp. 334–341)',
        "start": r"^CAP\.\s*VIII\.", "end": r"^CAP\.\s*IX\.", "first_col": 493,
        "about": 'the chapter on the two passages where the locusts are taken in a mystical sense: Eccl 12:5 (ויסתבל החגב, the grasshopper becomes a burden, of old age) and the locusts that come up from the abyss in Rev 9:1-11, with their faces of men, hair of women, teeth of lions and breastplates of iron, and their king Abaddon, Apollyon',
        "terms": _T9 + '"locusta" -> "locust"; "bruchus" -> "bruchus"; "arbe", "gazam", "jelek", "chasil", "gob", "chagab" stay as printed; "abyssus" -> "the abyss"; "Abaddon", "Apollyon" stay as printed; "lorica" -> "breastplate";'},
    "musca": {"vol": 3, "pages": list(range(341, 353)),
        "title": 'Part 2, Book 4, chapter 9: On the fly (vol. 3, pp. 341–352)',
        "start": r"^CAP\.\s*IX\.", "end": r"^CAP\.\s*X\.", "first_col": 496,
        "about": "the chapter on the fly: the seven kinds of fly named in Scripture and its old versions, זבוב zebub, the dead flies that make the perfumer's ointment stink (Eccl 10:1), the fly from the rivers of Egypt (Isa 7:18), and Baal-zebub, the god of Ekron (2 Kgs 1:2), with the fly-gods and fly-chasers of the Greeks",
        "terms": _T9 + '"musca" -> "fly"; "zebub" stays as printed; "culex" -> "gnat"; "Baal-zebub", "Beel-zebub" stay as printed; "myiagrus", "apomyius" stay as printed;'},
    "apes-leo": {"no_id": {"Aldrovandi": 99}, "vol": 3, "pages": list(range(352, 366)),
        "title": "Part 2, Book 4, chapter 10: The name and origin of the bees; how they are found in the lion's carcass; that they hear, are frightened by the sound of brass, driven out by smoke, and are brave (vol. 3, pp. 352–365)",
        "start": r"^CAP\.\s*X\.", "end": r"^CAP\.\s*XI\.",
        "about": "the chapter on the name of the bee, דבורה debora (from דבר), and the passages on bees in Scripture: the swarm and honey in the carcass of Samson's lion (Judg 14:8), the bees that pursue the Israelites (Deut 1:44) and surround the Psalmist (Ps 118:12), how they hear, are frightened by the ringing of brass, driven out by smoke, and are brave, and the old story of bees born from a carcass (bugonia)",
        "terms": _T9 + '"apis" -> "bee"; "examen" -> "swarm"; "favus" -> "honeycomb"; "alveare" -> "hive"; "debora" stays as printed; "fucus" -> "drone"; "bugonia" stays as printed; "cadaver" -> "carcass";'},
    "apes-patres": {"no_id": {"Jonathan": 99}, "vol": 3, "pages": list(range(365, 375)),
        "title": 'Part 2, Book 4, chapter 11: Some passages on the honey-making of the bees that the Greek Fathers cite as if from Scripture (vol. 3, pp. 365–374)',
        "start": r"^CAP\.\s*XI\.", "end": r"^CAP\.\s*XII\.", "first_col": 510,
        "about": 'the chapter on the bee in the Greek Bible: the verse that the Septuagint adds to Prov 6:8 (ἢ πορεύθητι πρὸς τὴν μέλισσαν, go to the bee and learn how she works), which the Greek Fathers cite as Scripture, and Sir 11:3 (the bee is small among flying creatures, but her fruit is the chief of sweet things)',
        "terms": _T9 + '"apis" -> "bee"; "examen" -> "swarm"; "favus" -> "honeycomb"; "alveare" -> "hive"; "debora" stays as printed; "fucus" -> "drone"; "operaria" -> "worker";'},
    "mel-cera": {"no_id": {"Jonathan": 2}, "vol": 3, "pages": list(range(374, 403)),
        "title": 'Part 2, Book 4, chapter 12: On honey and wax (vol. 3, pp. 374–402)',
        "start": r"^CAP\.\s*XII\.", "end": r"^CAP\.\s*XIII\.",
        "about": "the chapter on honey and wax: דבש debas, the name of bees' honey and of the syrup of dates and grapes, the honey from the rock (Deut 32:13, Ps 81:17), wild honey, the honey of the first fruits (2 Chr 31:5) and its exclusion from the offerings by fire (Lev 2:11), the honeycomb נפת nopheth, and wax (דונג), with the Arabic and Greek names",
        "terms": _T9 + '"apis" -> "bee"; "examen" -> "swarm"; "favus" -> "honeycomb"; "alveare" -> "hive"; "debora" stays as printed; "fucus" -> "drone"; "mel" -> "honey"; "cera" -> "wax"; "debas", "nopheth", "tsuph" stay as printed; "dactyli" -> "dates"; "sapa", "defrutum" -> "boiled-down must";'},
}
SENTENCE_END = re.compile(r"[.!?:;)\]]\s*$")
# Corrections to the voted OCR of pages without gold text, each checked on the scan.
# Catchwords read into the body text (the next page begins with the same word); applied to the
# gold text too (p. 410).
FIXES = {
    410: [("מעלה\nגרה,", "מעלה")],
    # Ethiopic and Samaritan, read by Claude at 4-6x (02-Nov-2026; not by a reader of these scripts):
    # ለጊሔ፡ fits Bochart's "legiche"; the Samaritan, Bochart's "taphsa", read ט פ ס ה (the ה not sure)
    412: [("ሰጊሔ፡", "ለጊሔ፡"), ("<i>Samaritano</i> [?] <i>taphsa", "<i>Samaritano</i> ࠈࠐࠎࠄ <i>taphsa")],
    414: [("con-\nstanter", "con-")],
    # the catchword "rias" (printer's error for "riae", p. 419's first word)
    # ኮሮገሬሊወን፡ (choerogryllion): seven signs before the colon, Opus had six; 3rd and 4th not sure
    418: [("<i>Histo-\nriae</i> ⟦p. 1009⟧", "<i>Histo-</i> ⟦p. 1009⟧"), ("ኮርገሊሎን፡", "ኮሮገሬሊወን፡")],
    421: [("يناقده\nاليه", "يناقده")],
    # ch. 35 (08-Nov-2026): catchwords read into the body text
    439: [("caeci de-\ngunt</i>,", "caeci de-</i>")],
    440: [("meta-\nphoram-", "meta-")],
    # tranche 1 (09-Nov-2026): superscript letters as note marks; the margin mark of p. 495 is printed
    # 1071 (read on the scan; Opus and MDZ read 1971)
    479: [("^{ᵉ)}", "^{e)}"), ('qui non', 'qui nou')],
    495: [("⟦p. 1971⟧", "⟦p. 1071⟧"), ('τȣ̃', 'τοῦ')],
    510: [("^{ᵃ)}", "^{a)}")],
    # tranche 1: catchwords read into the body text (the next page begins with the same word)
    456: [("الافاع\nولا", "الافاع")],
    464: [("وان كان\nيشبهه", "وان كان"), ('פרויט.', 'פויוט.')],
    466: [("يخرج من\nحاجره", "يخرج من")],
    471: [("aluntur.</i>\nوكذلك", "aluntur.</i>")],
    473: [("ut de\neo", "ut de")],
    480: [("فلا\nياكلونها", "فلا")],
    482: [("οἱ\nχερσαῖοι,", "οἱ"), ('talibus crocodilis accipiendum,', 'talibus crccodilis accipiendum,')],
    492: [("<i>Gal-\nlica.</i>", "<i>Gal-</i>")],
    497: [("quod id\nipsum", "quod id")],
    502: [("العظاة\nعند", "العظاة")],
    503: [("aspi-\nratio,", "aspi-")],
    514: [("sam-\nmabras,", "sam-")],
    # tranche 1, scan check (09-Nov-2026): the print differs from the vote's proposal
    455: [('Poniarius</i> ריצ"ו', 'Poniarius</i> ריצ"יו'), ('Selomo</i> הריצון', 'Selomo</i> הריצ"ון')],
    461: [('ὄπω', 'οὔπω')],
    475: [('ܚܪܕܘܢܐ', 'ܚܕܪܘܢܐ')],
    484: [('ἁρμόζει', 'ἁρμώζει')],
    486: [('ΧΑΡΟΥΚΙ,', 'ΧΑΡΟΥΚῚ,')],
    490: [('à', 'á')],
    498: [('عشّة', 'عشه')],
    501: [('Damir, اللحكا دويبة', 'Damir, لحلكا دويبة'), ('بالعظاة', 'بالعغناة')],
    511: [('Εἱλίσσετε', 'Εἰλίσσετε')],
    512: [('στάχυς (lege', 'στάχους (lege')],
    517: [('ἐκδύνηται·', 'ἐκδύηται·')],
    # tranche 2 (10-Nov-2026): margin column numbers read on the scan (qa.py found the gaps in the
    # sequence); col. 34 is not printed on pp. 567-568
    535: [("⟦p. 19⟧", "⟦p. 10⟧"), ('והחורים', 'והתורים')],  # the Hebrew: group A scan check
    557: [("⟦p. 24⟧", "⟦p. 26⟧")],
    567: [("⟦p. 39⟧", "⟦p. 33⟧")],
    # tranche 2, group A, scan check (10-Nov-2026): the print differs from the vote's text (misprints kept)
    525: [('περιστερὰν δε,', 'περιστεράν δε,')],
    528: [('albis', 'aleis')],
    529: [('παλαιοῦ', 'παλαίου')],
    531: [('cum حمام', 'eum حمام')],
    537: [('فراف <i>riphraph</i>', 'رفراف <i>riphraph</i>')],
    542: [('ὀυκ', 'οὐκ')],
    # tranche 2, group B, scan check (10-Nov-2026): the print differs from the vote's text (misprints kept);
    # p. 560: the Hebrew words of Ezek 22:24 were read in visual order and without the ו of גושמה
    546: [('Ἅ ῥά θ᾽ ὑφ᾽', 'Ἥ ῥάθ᾽ ὑφ᾽')],
    548: [('ἀγροὺς,', 'ἄγρους,')],
    551: [('مثل', 'مشل'), ('ἀπλούστατοι', 'ἁπλούστατοι')],
    559: [('למקדשין', 'למקדשי')],
    # the owner's review of the Hebrew concordance, 13-Nov-2026: ו read for ז (pp. 443, 561, 684), איותי for אייתו (p. 679)
    443: [('חרוא', 'חרזא')],
    561: [('דויתהא', 'דזיתהא')],
    560: [('ועם ביום גשמה ולא היא,', 'היא ולא גושמה ביום זעם,')],
    562: [('Ἄλλα', 'Ἀλλὰ')],
    563: [('σεγαστὰς', 'στεγαστὰς')],
    565: [('ὑῶν', 'ὑὼν'), ('مملولة', 'مبلولة')],
    # tranche 2, group C, scan check (10-Nov-2026): the print differs from the vote's text (misprints kept);
    # p. 568 Syriac as in the Peshitta of Luke 3:22; p. 589 the Greek article was read as Hebrew דא
    568: [('ܦܓܪܐ ܕܝܘܢܐ,', 'ܓܘܫܡܐ ܕܝܘܢܐ,')],
    576: [('מחראות^{d)}', 'טחוראות^{d)}')],
    578: [('ܢܩܒܐ', 'ܚܪܘܪܐ')],
    579: [('Φοινικηίου', 'Φοινικηΐου')],
    589: [('חרי דא,', 'τοῦ חרי,')],
    590: [('ሞሆኒቅ፡', 'መዐንቅ፡')],
    # tranche 3 (11-Nov-2026): the note mark *) of p. 611 was read plain, not as ^{*)}; the margin number
    # of p. 611 is 66 (Opus and MDZ read 661; qa.py found the gap)
    611: [('hirundo</i> *). Et apud', 'hirundo</i>^{*)}. Et apud'), ('⟦p. 661⟧', '⟦p. 66⟧')],
    # tranche 3, scan check (11-Nov-2026): the print differs from the vote's text (misprints kept)
    594: [('ἁλυσιδωτοὺς,', 'ἀλυσιδωτοὺς,'), ('ἁλυσιδωτὰς,', 'ἀλυσιδωτὰς,')],
    597: [('צרצירלחא', 'צרצילתא'), ('ἀναισθησίᾳ', 'ἀναιθησίᾳ'), ('πραττόν-\nτων,', 'πρατ-\nτων,'), ('[?]αύσοιο', 'Ναύσοιο'), ('[?]idquam', 'quidquam'), ('[?]κναίειν', 'Ἐκκναίειν'), ('[?]s.</i> Quod', 'dens.</i> Quod'), ('[?], δήπου', 'δίᾳ, δήπου'), ('[?]m ineptiis', 'enim ineptiis'), ('[?]ur de', 'igitur de'), ('[?]<i>rtures', '<i>Turtures')],
    613: [('tae [?]montium', 'tae montium'), ('ta [?]imis', 'ta nimis'), ('κρ[?]πτουσιν', 'κρύπτουσιν'), ('mo[?]i', 'modi'), ('val[?]bus', 'vallibus'), ('lib[?]', 'libri'), ('dia[?]us', 'dianus'), ('Sed [?] cum', 'Sed cum'), ('risq[?]e', 'risque'), ('u[?]us', 'unus'), ('temp[?]us', 'tempus'), ('dinu[?]n', 'dinum')],
    615: [('ἐπακούσῃς,', 'ἐπακούσης,')],
    619: [('πόλεως σαδίους δισχιλίους,', 'πόλεως σταδίους δισχιλίους,')],
    628: [('ἐπακούσῃς,', 'ἐπακούσης,'), ('Ἥτ᾽', 'Ἡτ᾽'), ('ὡρα-\nθέρους', 'ὥρα-\nθέρους')],
    629: [('Βιστονίαν', 'Βιστόνιαν'), ('</i> Pygmaeo <i>sanguine', '</i> Pygmaëo <i>sanguine')],
    630: [('ἄνϑρωπους,', 'ἀνθρώπους,')],
    631: [('στρουθία,', 'στρουθια,'), ('Syriaco [?],', 'Syriaco ܥܓܘܪܐ,')],
    633: [('זיל חהא מלגלג', 'זיל תהא מלגלג'), ('ﺩﺟﺮ,', 'دجر,')],
    638: [('פרדי״ו', 'פרד״יז')],
    639: [('α.', 'ά.')],
    645: [('ἐπικορρίζουσι)', 'ἐπικοῤῥίζουσι)'), ('ܩܠܘܒܐ', 'ܩܠܘܒܝܐ'), ('קורא esse', 'קֹרֵא esse')],
    595: [('[?]<i>quadringenta', '<i>quadringenta'), ('[?]<i>, et aves', '<i>bula, et aves'), ('[?]<i>um laquearibus', '<i>ticuum laquearibus'), ('[?] <i>Regum</i>', 'mo <i>Regum</i>'), ('[?]ue in <i>Iosepho', 'neque in <i>Iosepho'), ('[?] lib. 6. cap. 6.', '<i>Iudaico</i> lib. 6. cap. 6.'), ('[?]ινι', 'μή τινι'), ('[?]<i>ebat', '<i>horrebat'), ('[?] כלה,', 'כלה עורב,'), ('[?]emplum', 'nis templum'), ('[?]mo,', 'summo,')],
    598: [('Arab. [?],', 'Arab. سمرمر,')],
    627: [('ca[?]rae', 'caprae'), ('q[?]ales', 'quales')],
    634: [('קר[?]', 'קר')],
    # (the pairs with [?] above: a smear over the left margin of pp. 595, 597 and 613 in the scan hides one to
    # six letters at the line start; restored from the letters that show and the sense, 11-Nov-2026)
    # tranche 4 (scan check 12-Nov-2026, apply_review.py): the print differs from the vote's text
    650: [('ፈረፈረት:', 'ፈርፈርት፡')],
    651: [('ἐστί·', 'ἐστὶ·'), ('ἡλίκη τρυγὼν,', 'ἡ λίκη τρυγὼν,')],  # the second: a reader's APPLY that vote.ACCEPT does not apply
    655: [('φοινικέους', 'φοινικέου')],
    662: [('ἀλλήλοιιν·', 'ἀλλήλοιϊν·')],
    675: [('לעז', 'לע״ז')],
    676: [('Ἀνίβα', 'Ἀννίβα')],
    679: [('رمّون', 'ܪܡܘܢ'), ('איותי', 'אייתו')],  # אייתו: the owner's review, 13-Nov-2026
    681: [('ὄσα.', 'οὖσα.'), ('بنو', 'بنى')],
    684: [('דמודרז', 'דמזדרז'), ('ܬܪܢܓܠܐ', 'ܬܪܢܓܘܠ'), ('ܕܡܬܪܘܪܒ', 'ܕܡܙܕܪܟܠ'), ('rescribendum אבכא דמודרכל', 'rescribendum אבכא דמזדרכל')],
    685: [('rescribendum דמודרכל,', 'rescribendum דמזדרכל,'), ('lud דמודרכל', 'lud דמזדרכל'), ('ܕܡܙܪܙܠ in', 'ܕܡܙܕܪܟܠ in'), ('דמזורכיל.', 'דמזדרכיל.'), ('דמזרזו,', 'דמזרז,'), ('ܕܡܙܪܙܠ ܒܝܢܬ', 'ܕܡܙܕܪܟܠ ܒܝܢܬ'), ('ܙܪܙܠ,', 'ܕܪܟܠ,')],
    696: [('ዶሮ፡', 'ዶርሆ፡')],
    715: [('⟦p. 140⟧', '⟦p. 141⟧'), ('Ὀρ-', 'Ὁρ-')],
    716: [('φορους', 'φόρους')],
    718: [('εὐχροιν,', 'εὔχρουν,')],
    719: [('بادم', 'بادر')],
    # tranche 4 (12-Nov-2026): words the OCR left open or misread, read on the scan at 4x to 6x.
    # p. 648 the Ethiopic word of the chapter head; p. 649 the [?] was the row of vowel signs over the
    # Arabic word; p. 680 the Greek article was read as Hebrew; pp. 684-685 the Aramaic of Prov 30:31
    # (the narrow letter after מ is ז by the Syriac ܕܡܙܕܪܟܠ; ו and ז hardly differ in this type);
    # p. 699 the four Syriac words (the second and third letters of words 3 and 4 are not certain);
    # p. 709 Reland's Arabic word (Tedac); p. 715 the margin number: the last digit is damaged, 141 by
    # the sequence (p. 714 has 140, p. 717 has 142)
    648: [('سماني, [?]', 'سماني, ፈርፈርት')],
    649: [('Ar.\n[?]\nسمرمر', 'Ar.\nسمرمر')],
    # p. 661: note (3) has no mark in the text of the print; put after the verses it refers to, so that the note is kept
    661: [('LXXVIII, 26. 27.</i>', 'LXXVIII, 26. 27.</i>^{(3)}')],
    680: [('quum זגתא עם', 'quum τῷ זגתא')],
    698: [('דמשתכחאביני', 'דמשתכחא ביני'), ('recense-\nri ברבו׳', 'recense-\nri ברבורי׳'), ('pro ברבו׳', 'pro ברבר׳')],
    699: [('vocibus [?], et [?], et [?], et [?].', 'vocibus ܓܓܘܠܬܐ, et ܩܝܩܘܠܬܐ, et ܨܘܨܠܬܐ, et ܫܘܫܠܬܐ.')],
    # p. 709, Reland's note: the Hebrew word is תך (the left leg has a foot), read as חך three times; found in
    # the English after the translation. p. 684: the Syriac word, as on p. 685
    709: [('alii [?],', 'alii تدك,'), ('hoc a חך:', 'hoc a תך:'), ('a חך geminata', 'a תך geminata'), ('natum sit חך', 'natum sit תך')],
    # tranche 5 (scan check 13-Nov-2026): the print differs from the vote's text
    726: [('الذكر.', 'الذكرة.')],
    731: [('والنفر', 'والتفرد')],
    740: [('עז', 'ע״ז')],
    742: [('وينتغله', 'ويقتلعه'), ('הצפורות,', 'העופות,')],
    750: [('εὐκλὴϊς', 'εὐκληῒς')],
    751: [('αἴσσειν,', 'ἀΐσσειν,')],
    756: [('ὀξυωπέστε-', 'ὀξυωπήστε-')],
    767: [('αγκάλους.', 'αγκαλίους.')],
    775: [('עזוא', 'עוזא'), ('ἔτος', 'οὗτος'), ('</i> [?] <i>uza', '</i> ࠏࠅࠆࠀ <i>uza'), ('pro [?] <i>oznija', 'pro ࠏࠆࠍࠉࠄ <i>oznija')],
    780: [('المغص', 'المقص')],
    781: [('τῆς', 'τοῦ')],
    783: [('ἐλαφοι.', 'ἐλάφους.')],
    # the Samaritan words (13-Nov-2026): pp. 770 and 778 read from the letter count and Bochart's romanization
    # (bezaa; 'per Daleth', 'per Res'), p. 775 by Flash and the judge; not by a reader of the script
    770: [('בלאבֿו', 'בלאבֿוז'), ('est [?] <i>bezaa', 'est ࠁࠆࠀࠄ <i>bezaa')],
    777: [('דדה,', 'רחף,')],
    778: [('legi [?] per', 'legi ࠃࠀࠄ per'), ('nusquam [?] per', 'nusquam ࠓࠀࠄ per')],
    773: [('الغبنة', 'الفينة'), ('فانا خاف', 'فاذا خاف')],  # ذ/ن: "cum timet"
    # listed by spotcheck.py against Bochart's romanization (tsophtsoph, tsaphtsapha: ف/غ have one shape) and
    # the verse of Plautus (milvinis; Flash read it so)
    725: [('صغصف', 'صفصف')],
    744: [('nilvinis', 'milvinis')],
    # tranche 6 (scan check 14-Nov-2026): the print differs from the vote's text
    797: [('متقلواتا', 'متفواتا')],
    811: [('καὶ εὔστομεῖν εἰωθότα,', 'καὶ εὐστομεῖν εἰωθότα,')],
    819: [('Alanania', 'Alanama')],
    821: [('ἐπαίκλα,', 'ἐπάϊκλα,')],
    830: [('τυτώ vocabula', 'τυτὼ vocabula')],
    836: [('Ἅρπυιαι·', 'Ἁρπυία·')],
    # the last Syriac word from the Latin beside it (nidificat) and the shapes; the line is not certain
    838: [('ונציצתא,', 'ונוציציתא,'), ('ܘܡܥܫܫܐ,', 'ܘܡܩܢܢܐ,')],
    847: [('συνιδρουσῶν τῶν πτερύγων', 'συνιδρουσῶν τοῦ πτερύγων'), ('h)', 'b)')],  # the print has τȣ̃
    848: [('οἶδοῦν', 'οἰδοῦν'), ('ἀπερ οὖν', 'ἅπερ οὖν')],
    859: [('ܐܣܓܝ ܠܐ,', 'ܐܣܓܝܬ,')],
    869: [('يصبغها', 'يصبقها')],
    # tranche 6: found by hand (a Latin p in a Greek word; changes the vote could not apply; four letters
    # in تفرس; the two תעזוב of p. 854; two dots in نتل)
    # Samaritan (Gen 8:7), read by Claude from the letter count, the shapes (the first two words end in the
    # same three letters, the third in ࠁ) and Bochart's Latin: ונפק מפוק ותב. The second word is not certain.
    802: [('interpres, [?]\n[?] <i>Et egressus', 'interpres, ࠅࠍࠐࠒ ࠌࠐࠅࠒ\nࠅࠕࠁ <i>Et egressus')],
    805: [('πεpαχναῦσαι', 'περαχναῦσαι')],
    # tranche 6: three accepted proposals that vote.ACCEPT does not apply (kind "not similar"), and the ȣ
    # ligature read as ε (found by spotcheck.py; φιλομȣ́σῳ on the scan)
    803: [('فخرج يخرج', 'فجعل يخرج')],
    812: [('φιλομέσῳ', 'φιλομούσῳ')],
    858: [('ܕܨܦܪܐ ܐܝܬ\nܠܗ ܐܝܬ,', 'ܕܦܪܚܬܐ ܐܝܬ\nܠܗ̇,')],
    860: [('חסמם,', 'תחמס,')],
    806: [('submitto (*).', 'submitto ^{(0)}.')],  # see MARKERS
    837: [('كانها تفترس', 'كانها تفرس')],
    842: [('σπάνιος ὤν,', 'σπάνιος ὢν,'), ('κυκλοτέ-\nρῶς,', 'κυκλοτέ-\nρως,')],
    852: [('περιείληφασι', 'περιειλήφασι')],
    854: [('<i>sed Deus. Relinquit</i>, תעזב,', '<i>sed Deus. Relinquit</i>, תעזוב,'),
          ('Idem verbum תעזב,', 'Idem verbum תעזוב,')],
    856: [('Et نثل nethel', 'Et نتل nethel')],
    # tranche 7 (vol. 3; scan check 15-Nov-2026): the print differs from the vote's text. Keys of vol. 3 are (3, page).
    # The Samaritan words were left as [?] by the readers; read by Claude from the letter count, the shapes and
    # Bochart's romanization, not by a reader of the script (pp. 1, 33: the letters follow the romanization; p. 101:
    # the second letter is not sure).
    (3, 1): [('<i>Samaritano</i> [?] <i>sopha', '<i>Samaritano</i> ࠔࠅࠐࠀ <i>sopha')],
    (3, 5): [('<i>Samaritanis</i> [?] <i>netsatsah', '<i>Samaritanis</i> ࠍࠑࠑࠄ <i>netsatsah')],
    (3, 6): [('ἱερουται', 'ἱεροῦται')],
    (3, 7): [('κτείνῃ,', 'κτένῃ,'), ('الغذاء', 'القاء')],
    (3, 9): [('πτερῶτε', 'πτεροῦτε')],
    # p. 15: the Syriac auda begins with e, not with kaph or alaph (the alaph is the last letter)
    (3, 15): [('Syrus ܟܘܕܐ', 'Syrus ܥܘܕܐ'), ('</i> ܟܘܕܐ ^{(1)}', '</i> ܥܘܕܐ ^{(1)}'), ('ܟܘܕܐ esse', 'ܥܘܕܐ esse'),
              ('Samaritanus [?] <i>tsadja', 'Samaritanus ࠑࠃࠉࠀ <i>tsadja'), ('<i>Samaritanum</i>\n[?] <i>tsadja', '<i>Samaritanum</i>\nࠑࠃࠉࠀ <i>tsadja')],
    (3, 16): [('bet, [?] ponit', 'bet, بوم ponit')],
    (3, 23): [('IO.\nGOTTL.', 'Io.\nGOTTL.')],
    (3, 24): [('عرس', 'زمج'), ('qui [?] <i>barbari', 'qui ࠁࠓࠁࠓࠉ <i>barbari')],
    (3, 30): [('τουτον,', 'τοῦτον,'), ('ἄγγελον τουτον εὐθὺς', 'ἄγγελον τοῦτον εὐθὺς')],
    (3, 33): [('κουκουβαῖαι,', 'κουκουβαΐαι,'), ('κουκουβαῖαι.', 'κουκουβαΐαι.'),
              ('<i>Samaritanum</i>\n[?] <i>kaphupha', '<i>Samaritanum</i>\nࠒࠐࠅࠐࠄ <i>kaphupha')],
    (3, 35): [('קלב״א', 'קל״בא')],
    # p. 42: the grave mark of KIKI` read as a note letter; the note of the page is (3) and its mark was read (2)
    (3, 42): [('KIKI^{l)}', 'KIKI`)'), ('^{(2)}. Sed haec', '^{(3)}. Sed haec')],
    (3, 44): [('φοροῦσας', 'φορούσας'), ('ἐρωδιοὺς', 'ἐρωδίους'), ('διέστη ὥσπερ οὖν', 'διέστη ὡσπεροῦν'),
              ('στερρότης,', 'στεῤῥότης,')],
    (3, 52): [('est [?] <i>naamitha', 'est ࠍࠏࠌࠉࠕࠀ <i>naamitha')],
    (3, 59): [('المعغون', 'المعقود')],
    (3, 81): [('morphoseos', 'morphoseως')],
    (3, 84): [('est [?] <i>hirundo', 'est ࠔࠍࠅࠍࠉࠕࠀ <i>hirundo')],
    (3, 99): [('ἀετῶδους', 'ἀετώδους')],
    (3, 101): [('est\n[?], <i>hirundo', 'est\nࠏࠎࠍࠉࠕࠀ, <i>hirundo')],
    (3, 103): [('אגפיה גרותיה כדכתיב', 'אגפיה גדותיה כדכתיב'), ('גרותיו', 'גדותיו')],
    (3, 108): [('דמונטייא,', 'דמונ״טייא,')],
    (3, 109): [('quibus רוכיפת est', 'quibus דוכיפת est'), ('nomine רוכיפת', 'nomine דוכיפת')],
    (3, 111): [('Ἄστη', 'Ἀστῆ')],
    # GitHub issues 2 and 3 (the owner, 15-Nov-2026): ת״ר (Tradiderunt magistri nostri) at the end of p. 120, read
    # as ה״ר and put after הנץ; ה״ז (הרי זה) twice and בדיקה on p. 122
    (3, 120): [('ubi supra, הנץ ה״ר', 'ubi supra, ת״ר הנץ')],
    (3, 121): [('לרעתם', 'לדעתם')],
    (3, 122): [('ובשמותיהן הז״ אוכל', 'ובשמותיהן ה״ז אוכל'), ('צריך\nבריקה', 'צריך\nבדיקה'), ('אלו הז״ עוף', 'אלו ה״ז עוף')],
    # tranche 8 (vol. 3, pp. 126-194; scan check 16-Nov-2026): the print differs from the vote's text. Not certain: the
    # Syriac of pp. 127, 167 and 181, the Arabic themes of p. 186 (سفع, as on p. 184) and the two words of p. 185.
    (3, 127): [('ܚܘܝܐ', 'ܚܘܝܘܢܐ'), ('متمعط', 'متعط')],
    (3, 128): [('Arabum افعي haud', 'Arabum أفعي haud')],
    (3, 135): [('λεῖαι,', 'λείαι,')],
    (3, 143): [('τοῦτου', 'τούτου')],
    (3, 146): [('Πίμπρατα,', 'Πίμπραται,')],
    # p. 150: the Syriac of Ps 91:13 has garsa (the same word, with "amphisbaena", stands on p. 182)
    (3, 150): [('ܥܠ ܐܦܥܐ ܘܥܠ', 'ܥܠ ܓܪܣܐ ܘܥܠ'), ('Syro ܐܦܥܐ,', 'Syro ܓܪܣܐ,')],
    (3, 155): [('facit *).', 'facit ^{*)}.')],
    (3, 156): [('pethen</i> *).', 'pethen</i> ^{*)}.')],
    (3, 158): [('ἐστιν,', 'ἔστιν,')],
    # p. 159: two phrases stood in the order of the eye (left to right), not of the script
    (3, 159): [('θώ,', 'θὼ,'), ('ܕܬܢܝܢܐ ܡܪܪܬܐ,', 'ܡܪܪܬܐ ܕܬܢܝܢܐ,'), ('علي الثنانين اصناف اصغر', 'اصغر اصناف الثنانين علي')],
    (3, 162): [('189.[?]:', '189.:')],
    (3, 164): [('ἐπῳδοῖς', 'ἐπῳδοὺς')],
    (3, 166): [('171 – 175.', '171 - 175.')],
    (3, 167): [('ܡܚܒܪܐ', 'ܝܕܘܥܐ')],
    (3, 169): [('שה׳', 'שח׳')],
    (3, 171): [('אוזנו', 'אזנו')],
    (3, 172): [('ὄν,', 'οὖν,')],
    (3, 173): [('الا صلة', 'الاصله')],
    (3, 178): [('נפריזא <i>nephriza,</i> vel', 'נפרזא <i>nephriza,</i> vel'), ('et נפריזא', 'et נפרזא')],
    (3, 179): [('scribunt *).', 'scribunt ^{*)}.')],
    (3, 181): [('Syrus, ܒܝܬ ܨܗܘܬܐ,', 'Syrus, ܒܝܬ ܨܗܘܢܐ,'), ('<i>Syro</i>, ܒܝܬ ܨܗܘܬܐ,', '<i>Syro</i>, ܒܝܬ ܨܗܘܢܐ,')],
    (3, 182): [('ܦܬܢܐ,', 'ܐܣܦܣ,'), ('ܥܩܪܒܐ,', 'ܓܪܣܐ,')],
    (3, 185): [('سمرط vel صمرط,', 'مسمرط vel مصمرط,'), ('تصفقها', 'تصفعها'), ('Thema\nصقع, atque cum سقع', 'Thema\nصفع, atque cum سفع')],
    (3, 186): [('سمغ et صمغ', 'سفع et صفع')],
    (3, 187): [('ארם', 'אדם')],
    (3, 191): [('σόματι', 'στόματι'), ('ρπης', 'ρπηστ')],
    (3, 192): [('βασιλισκοι,', 'βασιλίσκου,')],
    # tranche 9 (vol. 3, pp. 195-271; scan check 17-Nov-2026): the print differs from the vote's text. Not certain: the
    # Syriac of p. 205 (as the Arabic معرون), the Arabic of p. 256, the Ethiopic of p. 269, the Samaritan of p. 205.
    (3, 197): [('κοῦφους ἢ γοῦφους', 'κούφους ἢ γούφους'), ('σκω-\nπτειν', 'σκώ-\nπτειν')],
    (3, 201): [('هلاشبالة', 'هلاشباله')],
    # p. 203: the mark is the letter l) of the note, not the digit
    (3, 203): [('supra ^{¹)}', 'supra ^{l)}')],
    # p. 205: the Samaritan word (Samaritan Targum, "insidiantem"), read by Claude from the shapes: four letters, the
    # first three alike, as כמין; not certain
    (3, 205): [('פתנא,', 'פתנה,'), ('ܫܦܝܦܘܢܐ,', 'ܡܥܪܘܢܐ,'), ('صفرون,', 'معرون,'), ('Samaritani\n[?] ·', 'Samaritani\nࠊࠌࠉࠍ ·')],
    (3, 206): [('معرفة.', 'مقرنة.')],
    # GitHub issue 4 (20-Nov-2026): Koph and Ajin change places (ארקא/ארעא, קטר/עטר, קסם/עצמון); the readers gave ܦܣ for ܛܪ
    # and ר for ק. The fourth Syriac word begins with ܥ and ends with ܐ; its middle letters are not certain.
    (3, 207): [('meraste cornu-', 'ceraste cornu-'), ('et ܐܬܢܢ:', 'et ܐܪܩܐ:'), ('ܩܘܦܣ et ܟܦܣ:', 'ܩܛܪ et ܥܛܪ:'),
               ('ܩܘܦܣܐ et ܟܦܣܐ.', 'ܩܘܪܐ et ܥ[?]ܐ.'), ('Ionathani</i>\nרקם', 'Ionathani</i>\nקסם')],
    (3, 208): [('نلك', 'ذلك')],
    (3, 218): [('15. ܛܒ ܓܝܪ ܙܩܦ ܠܡܠܘܗܝ ܠܡܠܝܢ', '15. ܛܒ ܓܝܪ ܙܩܦ ܢܦܫܗ ܠܘܩܒܠ ܡܠܝܢ')],
    # p. 221: the margin prints "p. 248.", a printer's error for 428 (p. 222 has 429)
    (3, 221): [('⟦p. 248⟧', '⟦p. 428⟧')],
    (3, 222): [('تِبنان', 'تِينان')],
    (3, 223): [('فصع,', 'قصع,')],
    (3, 225): [('τρια-\nοντάπηχυ', 'τρια-\nκοντάπηχυ')],
    (3, 226): [('ὥστ᾽', 'ὥς τ᾽'), ('ὥσθ᾽', 'ὥς θ᾽')],
    (3, 227): [('Metamorphoseos', 'Metamorphoseωs')],
    (3, 229): [('ὑπόδραξ', 'ὑποδρὰξ')],
    (3, 230): [('Ἀθή-\nνας', 'Ἀθῆ-\nνας')],
    (3, 234): [('Ἴυγξι', 'Ἴϋγξι')],
    (3, 237): [('τεῖς.', 'τοὺς.')],
    # p. 241: note e) (Sirach 25:15) has no mark in the text of the print; put after the name, so that the note is kept
    (3, 241): [('ειλήσας', 'ἐνειλήσας'), ('scribit <i>Sirachides</i>,', 'scribit <i>Sirachides</i> ^{e)},')],
    (3, 242): [('ἴυγγας', 'ἴϋγγας')],
    (3, 249): [('لاتخطيه\n', 'لاتحظيه\n')],
    (3, 253): [('النخل,', 'النحل,')],
    (3, 256): [('خُنَن', 'حُنَن')],
    (3, 259): [('ad Ioel I,', 'ad Iocl I,')],
    (3, 260): [('Dsjerâd\nâchmar', 'Dsjerâd\náchmar'), ('[جران احمر]', '[جراد احمر]')],
    # spot-check of tranche 9: medial ف looks like غ in this type; flavae (p. 233) and Niebuhr's asfur (p. 261) decide
    (3, 233): [('صغر وسود', 'صفر وسود')],
    (3, 261): [('جراد عصغور', 'جراد عصفور')],
    (3, 265): [('περιιοῦσα', 'περιϊοῦσα')],
    (3, 269): [('አድርመጠቶት:', 'አድሩመጠቂት፡'), ('<i>thamar Adrumatavith', '<i>chamar Adrumatavith')],
    # tranche 10 (vol. 3, pp. 272-326; scan check 18-Nov-2026): the print differs from the vote's text. Not certain: the
    # year on p. 279 (middle digit faint). P. 283: two long Syriac quotations (Barhebraeus and his
    # continuator) are not transcribed: Opus left them as [?], and the readings of Opus and Flash on a re-read differ from
    # the scan in most words; Rosenmüller's Latin translation follows each.
    (3, 274): [('appellatur ܡܣܡܪܐ', 'appellatur مسمار')],
    (3, 275): [("Χρυσοειδῆ δ' ἐν ἰνδάλματα", 'Χρυσοειδῆ οὖν ἰνδάλματα'), ('רמצלהב,', 'דמצלהב,')],
    (3, 277): [('est כבר. Et', 'est כבד. Et'), ('התכברי', 'התכבדי'), ('כבר,', 'כבד,'), ('התכבר כילק', 'התכבד כילק'), ('התכבר\nin', 'התכבד\nin'), ('verbum התכבר.', 'verbum התכבד.'), ('כבר מאד', 'כבד מאד')],
    (3, 278): [('(^{9})', '^{(9)}')],
    (3, 279): [('17[?]9.', '1709.')],
    (3, 280): [('ܒܥܣܟܪܗ', 'بعسكره'), ('ܐܡܪܗ', 'امره'), ('ܘܐܚܕܗ', 'واخذه'), ('ܒܬܚܣܝܢ', 'بحسن'), ('ܬܪܬܝܒ', 'ترتيب')],
    (3, 281): [('طلبا', 'ظاعنا')],
    # 20-Nov-2026: the left block (Barhebraeus, Chronicon, ed. Bruns and Kirsch 1789, p. 134), read with Kraken and the
    # Qoruyo Serto model on this scan and on the 1789 print, reconciled word by word with Rosenmüller's Latin and read on
    # both scans where they differ (SYRIAC.md). Not certain: ܘܡܫܬܟܚ (line 3) and ܓܪ̈ܒܐ (hydriae, line 6).
    (3, 283): [('[?]\n[?]\n[?]\n[?]\n[?]\n[?]\n[?]\n[?]\n[?]\n[?]\n[?]\n[?]\n[?]\n[?]',
                'ܒܫܢܬ ܐܨܗ ܕܝ̈ܘܢܝܐ ܐܬܐ ܩܡܨܐ\nܦܪܚܐ ܘܚܒܠ ܙܪ̈ܥܐ ܘܐܪܡܝ\nܙܪܥܐ ܘܢܦܩ. ܘܡܫܬܟܚ ܗܘܐ\n'
                'ܘܣܠܩ ܒܫܘܪ̈ܐ ܘܐܣ̈ܐ. ܘܥܐܠ\nܡܢ ܟܘ̈ܐ ܘܬܪ̈ܥܐ ܠܒ̈ܬܐ.\nܘܐܬܡܠܝܘ ܡܢܗ ܐܦ ܓܪ̈ܒܐ\n'
                'ܕܡ̈ܝܐ ܘܬܫܘܝ̈ܬܐ ܘܦܬܘܪ̈ܐ ܘܠܓ̈ܢܐ.\nܘܟܕ ܡܢ ܦܢܝܬ ܬܝܡܢܐ\nܥܐܠ ܗܘܐ ܠܒܝܬܐ ܡܢ ܓܒܐ\n'
                'ܓܪܒܝܝܐ ܢܦܩ ܗܘܐ. ܘܐܟܠ\nܥܡ ܥܣܒܐ ܘܐܝܠ̈ܢܐ. ܐܦ\nܡܐ̈ܢܐ ܕܥܡܪܐ ܘܢܚ̈ܬܐ ܕܒ̈ܢܝܢܫܐ.\n'
                'ܘܟܕ ܓܡܪ ܠܟܠܗ ܦܢܝܬܐ\nܕܐܘܪܗܝ ܘܣܪܘܓ ܥܒܪ ܠܡܥܪܒܐ.'), ('seq. [?]\n[?]\n[?]\n[?]\n[?]\n[?]\n[?]\n[?]\n[?]\n[?]', 'seq. [Syriaca, versus X, hic non transcripta]'),
               ('ܗܘܐ ܐܝܬܝܗܘܢ ܘܕܒܒܐ,', 'ܘܕܒܒܐ ܐܝܬܝܗܘܢ ܗܘܐ,')],
    (3, 299): [('ܥܓܠܐ,', 'ܥܓ̈ܠܐ,')],
    (3, 300): [('ܥܓܠܬܐ ܒܠ', 'ܥܓܠܬܐ ܥܠ'), ('ܐܘܪܝܘܬܗܘܢ,', 'ܐܘܪܝܘܬܗܝܢ,')],
    (3, 301): [('re[?]itam', 'redditam')],
    (3, 304): [('Σειρίȣ', 'Σειρίου')],
    # p. 295: the στ ligature (ςέ) dropped by the readers; Bochart's Latin has truncum
    (3, 295): [('Περὶ τὸ σέ-\nλεχος', 'Περὶ τὸ στέ-\nλεχος')],
    # p. 305: the margin's 3 is broken and looks like a 5 (pp. 304 and 306 have 472 and 474)
    (3, 305): [('⟦p. 475⟧', '⟦p. 473⟧')],
    (3, 306): [('<i>Plinio</i>^{a})', '<i>Plinio</i> ^{a)}')],
    (3, 308): [('πȣ', 'που')],
    (3, 317): [('צחנתו:', 'צחנהו:')],
    (3, 321): [('^{a})', '^{a)}')],
    # tranche 11 (vol. 3, pp. 327-402; scan check 20-Nov-2026): the print differs from the vote's text. Printer's errors kept:
    # שרה for שדה (p. 340), sadinh (p. 391), morra (p. 396). Not certain: the Syriac words of pp. 360 (ܡܬܬܢܢܢ), 380 and 399.
    (3, 330): [('ούτοσὶ', 'οὑτοσὶ')],
    (3, 331): [('اكل\nالجران', 'اكل\nالجراد')],
    (3, 335): [('ﺷﺒﻞ,', 'شبل,')],
    (3, 340): [('שדה,', 'שרה,'), ('ἀγρου.', 'ἀγροῦ.')],
    (3, 343): [('אורעי רזני\nזובורי', 'אורעי וזני\nזובורי')],
    (3, 348): [('ὁπότε οὖν δειπνοιεν', 'ὁπότε ἂν δειπνοιεν')],
    (3, 353): [('ܟܘܒܪܐ', 'ܕܒܘܪܐ')],
    (3, 362): [('π[?]τρης', 'πέτρης')],
    (3, 364): [('desere e coacti', 'deserere coacti')],
    (3, 365): [('(6)', '(5)')],
    (3, 366): [('قوتها فهي [?]', 'قوتها قدمت لانها اكرمت')],
    (3, 372): [('πού', 'που')],
    (3, 378): [('εἰς ῎Αμι-', 'εἰς Ἄμι-')],
    (3, 384): [('προσακτικὸν\nτοῦ', 'προστακτικὸν\nτοῦ')],
    (3, 391): [('ܥܡܛܐ', 'عليه')],
    (3, 400): [('πρoῦχον', 'προῦχον')],
    # p. 345 (note): Rosenmüller's Syriac of Eccl 10:1, five lines left as [?] by the OCR. Read by Claude on the scan with
    # the Peshitta (ETCBC) as a guide, consonants only; the print has ܡܣܪܚܝܢ and ܠܡܐܢܐ where the ETCBC text has ܡܣܪܝܢ
    # ܡܐܢܐ, and ܗܝ before ܡܢ. Not certain in the details. p. 399: the Peshitta's word for נכאת (Gen 37:25) and the
    # Samaritan Targum's קטף (ࠒࠈࠐ), both read on the scan.
    (3, 345): [('παράδοξα', 'παραδόξου'), ('δυνά-', ''), ('vertit: [?]\n[?]\n[?]\n[?]\n[?]\n<i>Sicut',
                'vertit: ܐܝܟ ܕܒ̈ܒܐ\nܕܡܝܬܝܢ ܡܣܪܚܝܢ ܠܡܐܢܐ\nܕܡܫܚܐ ܒܣܝܡܐ. ܝܩܝܪܐ\nܗܝ ܡܢ ܚܟܡܬܐ ܘܡܢ ܣܘܓܐܐ\nܕܬܫܒܘܚܬܐ ܣܟܠܘܬܐ ܩܠܝܠܐ\n<i>Sicut')],
    (3, 399): [('Syrus ܢܘܬܐ', 'Syrus ܪ̈ܗܛܢܐ'), ('Samaritanus [?] <i>balsamum', 'Samaritanus ࠒࠈࠐ <i>balsamum')],
    # spot-check of tranche 8: salich (the print has يسلخ two lines above; the word itself was not read again on the
    # scan); the themes of the note are those of p. 184 (سفع); the στ ligature
    (3, 153): [('اسود شالخ', 'اسود سالخ')],
    # spot-check of tranche 7: medial ف/ق read غ (the same shape in this type); Bochart's alchopphas, Alkik and flavo decide
    (3, 40): [('الغيق طاير', 'القيق طاير')],
    (3, 50): [('يكون\nاصغر عدو', 'يكون\nاصفر عدو')],
    (3, 116): [('vocant\nالخغاش', 'vocant\nالخفاش'), ('</i>, الخغاش الوطواط', '</i>, الخفاش الوطواط')],
    (3, 118): [('يخلق الخغاش', 'يخلق الخفاش'), ('</i>, الخغاش هو', '</i>, الخفاش هو'), ('السلامّ الخغاش', 'السلامّ الخفاش')],
}
# A page number written twice in the FIXES literal: Python keeps only the second list, without a word
# (tranche 4 lost two pairs that way until a check found it). Stop at import.
_src = Path(__file__).read_text(encoding="utf-8")
_keys = re.findall(r"^    (\d+|\(\d+, \d+\)): \[", _src[_src.index("\nFIXES = {"):_src.index("\n# A page number written twice")], re.M)
if len(_keys) != len(set(_keys)):
    sys.exit(f"entry.FIXES: page(s) listed twice: {sorted({k for k in _keys if _keys.count(k) > 1})}")
# Hebrew words corrected after the owner's review of the concordance (13-Nov-2026): ו/ז, ד/ר and ח/ת look
# alike in this type and the readers agreed on the wrong letter, so nothing was flagged. Each was listed by
# spotcheck.py (the word does not fit Bochart's romanization or Latin next to it) and read again on the scan,
# except p. 590, which is from the sense alone (Rashi: שדרה בבית כבשדה; "versatur in domo, quam in agro").
FIXES_HEBREW_QA = {
    476: [('ועיע את הימים', 'וזיע את הימים')],  # "Movit (Deus) maria"
    489: [('ונה <i>zana', 'זנה <i>zana')],
    519: [('in quo חפש est', 'in quo תפש est'), ('<i>Hebraeis</i> חפש, <i>capere', '<i>Hebraeis</i> תפש, <i>capere')],
    584: [('חרי מיני שתיתאה', 'תרי מיני שתיתאה')],  # "duas species"
    590: [('שחרה בבית כבשרה', 'שדרה בבית כבשדה')],
    600: [('permutatis, pro בחורים,', 'permutatis, pro בתורים,')],  # Song 1:10
    614: [('וצווח דל ככורכיא', 'וצווח ר״ל ככורכיא')],  # "dominus Lakis": the print has the abbreviation marks
    637: [('ubi pro קריא per <i>Daleth', 'ubi pro קדיא per <i>Daleth')],
}
for _p, _pairs in FIXES_HEBREW_QA.items():
    FIXES.setdefault(_p, []).extend(_pairs)

# the same foreign-script corrections, for an English translation made before them (translate.finish)
SCRIPT_SYNC = [("ሰጊሔ፡", "ለጊሔ፡"), ("ኮርገሊሎን፡", "ኮሮገሬሊወን፡"), ("[?] <i>taphsa", "ࠈࠐࠎࠄ <i>taphsa")]
NOTE_MARK = re.compile(r"\^\{(\(\d+\)|[a-z]\))\}")
MARGIN = re.compile(r"⟦p\. (\d+)⟧")
FOOTNOTE = re.compile(r"^(\(\d+\)|[a-z]\))\s")


def page_key(vol: int, page: int) -> str:
    return f"v{vol}-{page:04d}"


def gold_blocks(path: Path, ocr: dict) -> list[dict]:
    """Gold text -> blocks; block types from the OCR page (the gold pages keep its block count)."""
    texts = [t.strip("\n") for t in path.read_text(encoding="utf-8").split("\n\n") if t.strip()]
    if len(texts) != len(ocr["blocks"]):
        sys.exit(f"{path.name}: {len(texts)} gold blocks, {len(ocr['blocks'])} OCR blocks")
    out = []
    for t, b in zip(texts, ocr["blocks"]):
        m = FOOTNOTE.match(t) if b["type"] == "footnote" else None
        out.append({"type": b["type"], "marker": m.group(1) if m else "", "text": t[m.end():] if m else t})
    return out


# The letter or number of a footnote, where the OCR read it wrong (14-Nov-2026; FIXES changes only the text).
# p. 806: Rosenmüller's one note with an asterisk, at the end of ch. 12, is given the number 0 (shown as R0).
MARKERS = {(847, "h)"): "b)", (868, "c)"): "e)", (869, "d)"): "f)", (806, "(*)"): "(0)", ((3, 184), "1)"): "(1)"}


def page_blocks(vol: int, page: int) -> list[dict]:
    key = page_key(vol, page)
    ocr = json.loads((DATA / "ocr" / SOURCE / f"{key}.json").read_text(encoding="utf-8"))
    gold = DATA / "gold" / f"{key}.txt"
    blocks = gold_blocks(gold, ocr) if gold.exists() else ocr["blocks"]
    vp = page if vol == 2 else (vol, page)  # FIXES and MARKERS: a page of vol. 2 is 787, of another volume (3, 12)
    for old, new in FIXES.get(vp, []):
        hits = [b for b in blocks if old in b["text"]]
        if len(hits) != 1:
            sys.exit(f"p. {page}: correction {old!r} found {len(hits)} times, not once")
        hits[0]["text"] = hits[0]["text"].replace(old, new)
    for b in blocks:
        if (vp, b.get("marker")) in MARKERS:
            b["marker"] = MARKERS[(vp, b["marker"])]
        b["text"] = re.sub(r"\^\{([a-z])\}\)", r"^{\1)}", b["text"])  # p. 419: ^{a}) for ^{a)}
        b["text"] = re.sub(r"\(\^\{(\d+)\}\)", r"^{(\1)}", b["text"])  # p. 541: (^{6}) for ^{(6)}
        b["text"] = MARGIN.sub(r"[col. \1]", b["text"])
    return blocks


CATCHWORD_KEY = re.compile(r"</?i>|[^\w\s֐-ۿ܀-ݏͰ-Ͽἀ-῿-]")


def drop_catchwords(vol: int, pages: list[int], blocks: dict[int, list[dict]]) -> None:
    """The catchword at the foot of a page is often read into the body text, as the last line of the
    page's last body block (tranche 1: 12 of 74 pages). It is dropped where that last line (1-3 words)
    is the same as the first words of the next page's first body block. In place; prints each drop.
    A closing </i> in the dropped line is kept ("caeci de-\\ngunt</i>," -> "caeci de-</i>")."""
    for page in pages:
        nxt = blocks.get(page + 1) or page_blocks_or_none(vol, page + 1)
        if nxt is None:
            continue
        body = [b for b in blocks[page] if b["type"] == "body"]
        first = next((b for b in nxt if b["type"] == "body"), None)
        if not body or first is None or "\n" not in body[-1]["text"]:
            continue
        head, last = body[-1]["text"].rsplit("\n", 1)
        words = CATCHWORD_KEY.sub("", last).split()
        if not words or len(last.split()) > 3:
            continue
        first_words = CATCHWORD_KEY.sub("", first["text"].split("\n", 1)[0]).split()[:len(words)]
        if words == first_words:
            body[-1]["text"] = head + ("</i>" if "</i>" in last and last.count("</i>") > last.count("<i>") else "")
            print(f"catchword on p. {page} dropped: {last!r}")


def page_blocks_or_none(vol: int, page: int) -> list[dict] | None:
    return page_blocks(vol, page) if (DATA / "ocr" / SOURCE / f"{page_key(vol, page)}.json").exists() else None


def build(cfg: dict) -> tuple[list[dict], list[dict]]:
    """-> (main blocks, note blocks); each block has a "page"."""
    vol = cfg["vol"]
    main, notes, started, ended = [], [], False, False
    page_text, other_text = {}, {}
    blocks = {page: page_blocks(vol, page) for page in cfg["pages"]}
    drop_catchwords(vol, cfg["pages"], blocks)
    for page in cfg["pages"]:
        first_on_page = True
        for b in blocks[page]:
            text = b["text"].strip()
            if b["type"] == "furniture":
                continue
            if b["type"] == "footnote":
                notes.append({"type": "footnote", "marker": b.get("marker", ""), "text": text, "page": page})
                continue
            if not started:
                if not re.search(cfg["start"], text):
                    other_text[page] = other_text.get(page, "") + "\n" + text
                    continue
                started = True
            elif re.search(cfg["end"], text):
                ended = True
            if ended:
                other_text[page] = other_text.get(page, "") + "\n" + text
                continue
            page_text[page] = page_text.get(page, "") + "\n" + text
            prev = main[-1] if main else None
            prev_end = re.sub(r"(?:\s*\[col\. \d+\])+$", "", prev["text"]) if prev else ""
            continues = (page in cfg.get("continue", []) or not SENTENCE_END.search(prev_end)) \
                and page not in cfg.get("break", [])
            mark = f"[{'I' * vol}, {page}]"
            if first_on_page and prev and prev["type"] == "body" and b["type"] == "body" and continues:
                # a word broken over the page ("Histo-</i> [col. 1009]" | "<i>riae"): the marks after the word
                hy = re.search(r"-((?:</i>)?)((?:\s*\[col\. \d+\])*)$", prev["text"])
                if hy:
                    word, _, rest = text.partition(" ")
                    prev["text"] = f"{prev['text'][:hy.start()]}{hy.group(1)}{word}{hy.group(2)} {mark} {rest}"
                else:
                    prev["text"] += f" {mark} {text}"
            else:
                lead = f"{mark} " if first_on_page and main else ""
                if not main:  # the chapter's first block: its page and the column it starts in
                    lead = f"{mark} " + (f"[col. {cfg['first_col']}] " if cfg.get("first_col") else "")
                main.append({"type": b["type"], "marker": "", "text": lead + text, "page": page})
            first_on_page = False
        if ended:
            break
    if not started:
        sys.exit(f"start pattern {cfg['start']!r} not found")
    kept, seen = [], {}
    for n in notes:
        mark = f"^{{{n['marker']}}}" if n["marker"] else ""
        if mark and mark in page_text.get(n["page"], ""):
            seen[n["page"]] = True
            kept.append(n)
        elif mark and mark in other_text.get(n["page"], ""):
            continue  # a note of the chapter before or after, on a shared page
        elif not n["marker"] and kept and (
                (not seen.get(n["page"]) and kept[-1]["page"] != n["page"])
                or (n["page"] in cfg.get("join_notes", []) and any(k["page"] < n["page"] for k in kept))):
            # a note continued from the page before ("signi-|ficet"). "join_notes": [109] in an entry: the
            # continuation is printed after a note of its own page (15-Nov-2026), so the last note is not the one
            prev = [k for k in kept if k["page"] < n["page"]][-1]
            mark = f"[{'I' * vol}, {n['page']}]"
            if prev["text"].endswith("-"):
                word, _, rest = n["text"].partition(" ")
                prev["text"] = f"{prev['text'][:-1]}{word} {mark} {rest}"
            else:
                prev["text"] += f" {mark} {n['text']}"
            print(f"note on p. {n['page']} (no mark) joined to {prev['marker']} of p. {prev['page']}")
        else:
            print(f"note on p. {n['page']} {n['marker'] or '(no mark)'} left out: mark not in the chapter's text")
    return main, kept


def chunks(blocks: list[dict]) -> list[list[dict]]:
    out, cur = [], []
    for b in blocks:
        if cur and sum(len(x["text"]) for x in cur) + len(b["text"]) > CHUNK_CHARS:
            out.append(cur)
            cur = []
        cur.append(b)
    return out + [cur] if cur else out


LRM = "‎"  # keeps a paragraph that starts with Hebrew or Arabic left-to-right on GitHub


def md_inline(text: str) -> str:
    return re.sub(r"_\{(.+?)\}", r"<sub>\1</sub>", re.sub(r"\^\{(.+?)\}", r"<sup>\1</sup>", text))


def render(title: str, main: list[dict], notes: list[dict]) -> str:
    out = [f"# {title}", ""]
    for b in main:
        text = LRM + md_inline(b["text"]).replace("\n", " ")
        out += [f"### {text}" if b["type"] == "heading" else text, ""]
    if notes:
        out += ["---", "", "**Notes**", ""]
        for n in notes:
            label = n.get("label") or n["marker"]
            out += [f"{LRM}{label} *(p. {n['page']})* {md_inline(n['text']).replace(chr(10), ' ')}", ""]
    return "\n".join(out)


def pending(name: str, model: str, effort: str, main_blocks: list[dict], notes: list[dict]) -> tuple[dict, dict]:
    """The translation chunks of a chapter that are not cached yet -> (request bodies, {id: (chunk, cache)})."""
    import translate as T
    cfg = ENTRIES[name]
    T.CHAPTER = {"about": cfg["about"], "terms": cfg.get("terms", "")} if cfg.get("about") else None
    bodies, todo = {}, {}
    for kind, blocks in (("text", main_blocks), ("notes", notes)):
        for i, ch in enumerate(chunks(blocks), 1):
            src_key = hashlib.sha1(json.dumps([T.RULES_VERSION, model, effort, ch], ensure_ascii=False)
                                   .encode("utf-8")).hexdigest()[:16]
            cache = DATA / "entries" / name / "chunks" / f"{kind}-{i:03d}-{src_key}.json"
            if not cache.exists():
                bodies[f"{kind}-{i:03d}"] = T.request_body(ch, effort, notes=kind == "notes")
                todo[f"{kind}-{i:03d}"] = (ch, cache)
    return bodies, todo


def save_batch(res: dict, todo: dict, model: str, effort: str, seconds: float, prefix: str = "") -> None:
    import translate as T
    for cid, (ch, cache) in todo.items():
        try:
            r = T.parse(res.get(prefix + cid, {"error": "no result"}), len(ch), model, effort, seconds)
        except Exception as e:
            print(f"{prefix}{cid}: FAILED {type(e).__name__}: {e} (the sync loop of entry.py retries it)", flush=True)
            continue
        cache.parent.mkdir(exist_ok=True)
        cache.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")


def batch_all(names: list[str], model: str, effort: str, tag: str) -> None:
    """One OpenRouter batch for the chunks of several chapters (tranche.py translate, 12-Nov-2026); then
    `entry.py NAME --batch` finds every chunk cached and only does the fixed steps."""
    import orbatch
    bodies, todos = {}, {}
    for name in names:
        main_blocks, notes = build(ENTRIES[name])
        b, todos[name] = pending(name, model, effort, main_blocks, notes)
        # the batch's custom_id takes only [A-Za-z0-9_-]
        bodies.update({f"{name}__{cid}": body for cid, body in b.items()})
        print(f"{name}: {len(b)} chunks to translate", flush=True)
    if not bodies:
        return
    t = time.monotonic()
    res = orbatch.run_batch(model, bodies, log_name=f"translate_{tag}_{effort}_{len(bodies)}")
    for name in names:
        save_batch(res, todos[name], model, effort, time.monotonic() - t, prefix=f"{name}__")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("entry", choices=ENTRIES)
    p.add_argument("--model", default="anthropic/claude-opus-5.5")
    p.add_argument("--effort", default="medium")
    p.add_argument("--no-translate", action="store_true")
    p.add_argument("--batch", action="store_true", help="translate through the OpenRouter Batch API (half price)")
    p.add_argument("--finish-only", action="store_true", help="redo the fixed steps from en.raw.json")
    a = p.parse_args()
    cfg = ENTRIES[a.entry]
    out = DATA / "entries" / a.entry
    out.mkdir(parents=True, exist_ok=True)
    if a.finish_only:
        import translate as T
        T.finish(cfg, out)
        return
    main_blocks, notes = build(cfg)
    (out / "la.json").write_text(json.dumps({"main": main_blocks, "notes": notes}, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
    (out / "la.md").write_text(render(cfg["title"], main_blocks, notes), encoding="utf-8")
    print(f"{len(main_blocks)} paragraphs, {len(notes)} notes, "
          f"{sum(len(b['text']) for b in main_blocks)} characters of main text")
    if a.no_translate:
        return
    import translate as T  # here, so that --no-translate needs no model code
    if cfg.get("about"):
        T.CHAPTER = {"about": cfg["about"], "terms": cfg.get("terms", "")}
    en_main, en_notes, cost = [], [], 0.0
    if a.batch:  # all chunks not cached yet in one OpenRouter batch (half price); then the loop reads the cache
        import orbatch
        bodies, todo = pending(a.entry, a.model, a.effort, main_blocks, notes)
        if bodies:
            t = time.monotonic()
            res = orbatch.run_batch(a.model, bodies, log_name=f"translate_{a.entry}_{a.effort}_{len(bodies)}")
            save_batch(res, todo, a.model, a.effort, time.monotonic() - t)
    for kind, blocks, target in (("text", main_blocks, en_main), ("notes", notes, en_notes)):
        for i, ch in enumerate(chunks(blocks), 1):
            # each chunk is saved when done, keyed by its source and the rules: a stopped run resumes
            src_key = hashlib.sha1(json.dumps([T.RULES_VERSION, a.model, a.effort, ch], ensure_ascii=False)
                                   .encode("utf-8")).hexdigest()[:16]
            cache = out / "chunks" / f"{kind}-{i:03d}-{src_key}.json"
            if cache.exists():
                res = json.loads(cache.read_text(encoding="utf-8"))
                print(f"{kind} chunk {i}: done already", flush=True)
            else:
                for attempt in range(3):
                    try:
                        res = T.translate(ch, a.model, a.effort, notes=kind == "notes")
                        break
                    except Exception as e:
                        print(f"{kind} chunk {i}: attempt {attempt + 1} FAILED {type(e).__name__}: {e}", flush=True)
                        if attempt == 2 or "credit" in str(e).lower() or "402" in str(e):
                            sys.exit(f"stopped at {kind} chunk {i}; the chunks done so far are saved")
                        time.sleep(20 * (attempt + 1))
                cache.parent.mkdir(exist_ok=True)
                cache.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
                cost += res["meta"]["cost_usd"]
                print(f"{kind} chunk {i}: {len(ch)} blocks, {res['meta']['seconds']} s, "
                      f"${res['meta']['cost_usd']:.4f}", flush=True)
            for src, b in zip(ch, res["blocks"]):
                target.append({**b, "page": src["page"]})
    meta = {"model": a.model, "effort": a.effort, "rules": T.RULES_VERSION, "cost_usd": round(cost, 4)}
    (out / "en.raw.json").write_text(json.dumps({"main": en_main, "notes": en_notes, "meta": meta},
                                                ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"translation cost ${cost:.4f}")
    T.finish(cfg, out)


if __name__ == "__main__":
    main()
