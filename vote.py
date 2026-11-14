"""Vote on the flags of check.py and write the corrected main OCR as an engine of its own.

  uv run vote.py 408 429      # reads data/fix/v2-408-429.judge.jsonl; writes data/fix/v2-408-429.decisions.json,
                              # logs/vote_v2-408-429.csv and data/ocr/or-claude-opus-5.5@low+vote/

Ported from lewysohn-zoologie's hebvote.py. The voters are the two second readers (Flash, MDZ)
and the image judge. Rule: the main OCR is changed only where the image judge read the same as
Flash or as MDZ (2 of 3 against the main OCR, and the judge always one of the two). Flash and MDZ
alone never change it: on the gold pages both read Δίπες and "Patrae" where Opus was right.
A judge reading that matches no engine is "review" (listed, not applied). A change of a whole
different word (not a letter or two) is "review" too (an alignment error of check.py).
The new text is the reading of the engine the judge agreed with (Flash's text if both agree: MDZ's
has the long s as f). Writes the changed pages into data/ocr/{main}+vote/ (all pages, changed or
not), so eval.py and qa.py can score the voted text like any engine.
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz
from rapidfuzz.distance import Levenshtein

import eval as ev
from check import PUNCT, key

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
DATA = ROOT / "data"


def similar(old: str, new: str) -> bool:
    o, n = old.split(), new.split()
    if len(o) != len(n):
        return False
    return all(Levenshtein.distance(key(a), key(b)) <= max(2, len(key(a)) // 3) for a, b in zip(o, n))


# Changes of the vote that are wrong, each read on the scan (01-Nov-2026). Nearly all had only MDZ
# with the judge: an MDZ-only change needs a look (pilot: about 6 right, 9 wrong).
REJECT = {
    # tranche 6 (scan check 14-Nov-2026)
    ('v2-0793', 'BOS'): 'small capitals, as LAMB.',
    ('v2-0805', 'Ἰξευτικῶν,'): 'breathing before the capital: same letter',
    ('v2-0805', 'Ἀπόλλωνι·'): 'breathing before the capital: same letter',
    ('v2-0807', 'ערבויים'): 'two yods, as MDZ and the romanization Arabojim',
    ('v2-0837', 'تفترس'): 'print تفرس (four letters; medial ف)',
    ('v2-0837', 'חטפיתא'): 'ח by the sense (chatphitha); ה and ח look alike',
    ('v2-0856', 'نثل'): 'print نتل',
    ('v2-0856', 'البيضة'): 'البيضة is printed',
    ('v2-0858', 'calefit;'): 'calefit with f',
    ('v2-0867', 'نغض'): 'نغض (nagada); the dot is faint',
    # tranche 3 (scan check 11-Nov-2026, apply_review.py; group C finished in the main session)
    ('v2-0591', 'καρπήσιον·'): 'π is clear, no descender; not χ',
    ('v2-0602', 'סיס'): 'middle letter short (yod); the following סוס has a longer vav',
    ('v2-0607', 'οὔρεα,'): 'ȣ ligature with breathing and acute: οὔρεα',
    ('v2-0609', 'ἤ'): 'acute on the second ἤ (the first ἢ has the grave)',
    ('v2-0627', 'ὑποστρέφουσιν'): "vowel after φ is the ȣ ligature (MDZ's ε confirms), not ω",
    ('v2-0631', 'عجر,'): 'the stroke before ج is the lead-in of the letter (half the height of an alif; same in السخي p. 634), not ا',
    ('v2-0633', 'חהא'): 'print תהא (first letter has the left foot of ת, middle letter is ה (open left leg); neither חהא nor חזא)',
    ('v2-0634', 'السخي'): 'three teeth of س, then the lead-in of خ (not as tall as the ا and ل of the article)',
    ('v2-0636', 'قارية'): 'print قارية: two dots under the ي [first reader]',
    ('v2-0636', 'شُقِرّاق,'): 'letters ش-kashida-ق-ر-ا-ق (no second ر); vowel marks not resolvable [first reader]',
    ('v2-0640', 'Αὑτὸν'): 'the mark over υ is c-shaped (rough breathing)',
    ('v2-0645', 'ܩܠܘܒܐ'): 'print ܩܠܘܒܝܐ (six letters with yod (klubja); first letter a closed loop (qoph), unlike the open beth)',
    ('v2-0645', 'קורא'): 'print קֹרֵא (three letters, pointed: holem after ק, tsere under ר)',
    # tranche 2, group A (scan check 10-Nov-2026, apply_review.py)
    ('v2-0525', 'πολλοῦ.'): 'footnote a) prints πολλȣ̃ = ȣ ligature with circumflex = πολλοῦ; not ῷ',
    ('v2-0532', 'Ὅσα'): 'final letter is α, not οι; Ὅσα printed',
    ('v2-0537', 'e)'): 'superscript e) in print, like b) c) elsewhere kept plain; format only',
    ('v2-0539', 'φιλέρημος,'): 'Φ-shaped glyph is the ordinary lower-case φ (same as φησιν, ὀφθαλμῶν)',
    ('v2-0539', 'φωναὶ,'): 'same lower-case φ glyph; no capital',
    ('v2-0542', 'ὀυκ'): 'print οὐκ (ȣ ligature with smooth breathing + κ = οὐκ; models read ȣ as ε)',
    # tranche 2, group B (scan check 10-Nov-2026, apply_review.py)
    ('v2-0547', 'φάσσαν,'): 'the Φ-form glyph is the lower-case φ of this type (same glyph in ἐφίσδει below); mid-verse',
    ('v2-0549', 'φρόνιμοι'): 'Φ-form glyph = lower-case φ of this type, same size as in φρόνιμον/φρόνησις elsewhere',
    ('v2-0550', 'φημὶ'): 'Φ-form glyph = lower-case φ of this type; follows a high dot, not a sentence start',
    ('v2-0551', 'ἀπλούστατοι'): 'print ἁπλούστατοι (rough breathing; ȣ́ ligature = ου, then στ ligature; ἁπλέστατοι misreads ȣ as ε)',
    ('v2-0559', 'הדא'): 'second letter has a head wider than the stem: ד, not ו',
    ('v2-0562', 'οὐκ'): 'ȣ ligature with breathing + κ = οὐκ; ἐκ misreads ȣ as ε',
    # tranche 2, group C (scan check 10-Nov-2026, apply_review.py)
    ('v2-0568', 'شبه'): 'final letter is ه with no dots above',
    ('v2-0576', 'שכב,'): 'three letters ש כ ב, no initial yod',
    ('v2-0581', 'قلي'): 'two dots under the final letter = ي (twice on the page)',
    ('v2-0584', 'قلي'): 'two dots under the final letter = ي',
    ('v2-0588', 'אותר'): 'final letter has a top bar and a long stem = ר, not ו; misprint kept',
    ('v2-0589', 'δέ'): 'accent over ε rises to the right = acute (δέ before enclitic τι)',
    # tranche 1 (scan check 09-Nov-2026, logs/apply_review.py)
    ('v2-0478', 'حليه'): 'print ح, not ع (scan check 09-Nov-2026)',
    ('v2-0483', 'οὐκ'): 'ου ligature',
    ('v2-0484', 'φαρμάκοις,'): 'the lower-case φ of this type',
    ('v2-0484', 'φάρμακα'): 'the lower-case φ of this type',
    ('v2-0498', 'ووسواسه'): 'final ه without dots',
    ('v2-0502', 'تسيها'): 'no mim in the print',
    ('v2-0504', 'ἐστιν.'): 'στ ligature',
    ('v2-0504', 'ܟܒܟܘܫܬܐ,'): 'no dot on the second letter',
    ('v2-0505', 'Bellonius,'): 'a broken o, not a c',
    ('v2-0507', 'hae'): "print hae (a printer's error for hac)",
    ('v2-0513', 'αὐτοὺς,'): 'ου ligature',
    ('v2-0513', 'οὕτως'): 'ου ligature',
    ('v2-0515', 'cum'): 'print cum',
    ('v2-0517', 'φυ-'): 'the lower-case φ of this type',
    ("v2-0410", "טפז"): "print טפז (5x; Bochart: taphza)",
    ("v2-0412", "טווזא"): "print not clear (Bochart: tauza); judge read ז as ו before",
    ("v2-0414", "שפן"): "print שפן",
    ("v2-0414", "et-"): "print et- (a broken t)",
    ("v2-0415", "תרדמה"): "print תרדמה (Gen 2:21)",
    ("v2-0415", "האדם"): "print האדם",
    ("v2-0418", "riae"): "catchword 'rias' read into the body text: for the page join",
    ("v2-0421", "commune"): "print commune",
    ("v2-0425", "plerumque"): "print plerumque",
    ("v2-0429", "עכלבר"): "print עכלבר (achalbar); the line has both עכבר and עכלבר",
    ("v2-0411", "κένικλον."): "print κένικλον",
    ("v2-0411", "κένικλος,"): "print κένικλος (as κένικλον two lines before)",
    # ch. 35 (read on the scan 08-Nov-2026)
    ("v2-0440", "nuper"): "the r is in the smeared right edge of the scan",
    ("v2-0442", "fol. 6."): "spacing only",
    ("v2-0447", "כפל"): "print כפל (Ps 58:9 has נפל: a printer's error, kept as printed)",
    ("v2-0452", "scribit"): "print scribit (long s, then c)",
    ("v2-0454", "kipp[?]d"): "smeared right edge of the scan",
    ("v2-0437", "στον"): "print στ ligature (δυσανταγωνι-|στον)",
    ("v2-0441", "metalla"): "print metalla (the m looks like in)",
    # tranche 4 (scan check 12-Nov-2026)
    ('v2-0656', 'X'): 'scan check',
    ('v2-0661', 'κατασκεύαζον.'): 'scan check',
    ('v2-0673', 'ἐσθίομεν'): 'scan check',
    ('v2-0681', 'ערש'): 'scan check',
    ('v2-0690', 'ᾀδόντων.'): 'scan check',
    ('v2-0710', 'οὐκ'): 'scan check',
    # tranche 5 (scan check 13-Nov-2026)
    ('v2-0722', 'pharmacum'): 'scan check',
    ('v2-0725', 'الغمران'): 'scan check',
    ('v2-0726', 'οὖν'): 'scan check',
    ('v2-0731', 'يقفر'): 'scan check',
    ('v2-0731', 'قفرانا'): 'scan check',
    ('v2-0732', 'صدي'): 'scan check',
    ('v2-0733', 'LXX.'): 'scan check',
    ('v2-0735', 'pauxillo'): 'scan check',
    ('v2-0736', 'CCCIↃↃↃ'): 'scan check',
    ('v2-0737', 'ἐπιλησθήσεται,'): 'scan check',
    ('v2-0740', 'Clandianus'): 'scan check',
    ('v2-0741', 'שבמפג'): 'scan check',
    ('v2-0748', 'οὗτος'): 'scan check',
    ('v2-0759', 'Ensir,'): 'scan check',
    ('v2-0770', 'בלאבֿו'): 'print בלאבֿוז',
    ('v2-0773', 'ὀστοκόραξ,'): 'scan check',
    ('v2-0773', 'الغبنة'): 'print الفينة',
    ('v2-0780', 'صادها'): 'scan check',
    ('v2-0780', 'واصطاد'): 'scan check',
    ('v2-0784', 'πολλοὺς,'): 'scan check',
    ('v2-0787', 'Ὦπται'): 'scan check',
}

# Since 08-Nov-2026 a change that only MDZ supports (with the judge) is not applied but listed as
# "review (MDZ only)": in ch. 35 about 20 of 22 were wrong, most of them ד read as ר (חולד -> חולר).
# A change in this list was read on the scan and is right, so it is applied.
ACCEPT = {
    # tranche 6 (scan check 14-Nov-2026)
    ('v2-0801', 'يعود'),
    ('v2-0803', 'فخرج'),
    ('v2-0806', 'nutriant.'),
    ('v2-0807', '161 165.'),
    ('v2-0814', 'τῷ'),
    ('v2-0824', 'cele-'),
    ('v2-0835', 'انا'),
    ('v2-0847', 'προτερή-'),
    ('v2-0858', 'oblivi scitur'),
    ('v2-0858', 'ܘܛܥܝܐ ܕܪܓܠܐ ܕܨܦܪܐ ܐܝܬ ܠܗ ܐܝܬ,'),
    ('v2-0860', 'חסמם,'),
    ('v2-0863', 'وتحضن'),
    # tranche 3 (scan check 11-Nov-2026, apply_review.py; group C finished in the main session)
    ('v2-0593', 'ἀρκεύθω'),
    ('v2-0595', '[?]mo,'),
    ('v2-0597', '[?]s.'),
    ('v2-0597', '[?]ur'),
    ('v2-0598', 'τῷ'),
    ('v2-0601', 'חדעך,'),
    ('v2-0606', 'ἶβις,'),
    ('v2-0607', 'ὀλολυγὼν'),
    ('v2-0611', "Φ'."),
    ('v2-0613', 'risq[?]e'),
    ('v2-0613', 'u[?]us'),
    ('v2-0613', 'dinu[?]n'),
    ('v2-0613', 'mo[?]i'),
    ('v2-0613', 'dia[?]us'),
    ('v2-0615', 'ὥς, Ἠΰτε περ'),
    ('v2-0616', 'حارس'),
    ('v2-0621', 'καθορᾷν'),
    ('v2-0622', 'ἵπταται'),
    ('v2-0622', 'ὁρμαθὸν'),
    ('v2-0622', 'a)'),
    ('v2-0625', 'نوبته'),
    ('v2-0627', 'ca[?]rae,'),
    ('v2-0627', 'q[?]ales'),
    ('v2-0628', 'ἀρότοιό'),
    ('v2-0630', 'ܕܡܨܦܪܐ,'),
    ('v2-0631', 'عبر'),
    ('v2-0634', 'وتتيمن'),
    ('v2-0636', 'ptera'),
    ('v2-0637', 'עופות'),
    ('v2-0637', 'ילד'),
    ('v2-0638', 'verisimile'),
    ('v2-0644', 'קפרה'),
    ('v2-0646', 'ܡܨܝܕܬܐ'),
    ('v2-0648', 'Petentibus'),
    # pilot, ch. 33 (read on the scan 01-Nov-2026)
    ("v2-0410", "וחתול"), ("v2-0428", "τῷ"), ("v2-0428", "Scholia-"), ("v2-0428", "caussa"),
    ("v2-0416", "Viggeio"), ("v2-0416", "alphenec,"), ("v2-0429", "σθαι"),
    ("v2-0421", "لانت"), ("v2-0421", "انا"),  # ذ/ن changes of the pilot, right (لاذت, اذا)
    # ch. 35 (read on the scan 08-Nov-2026)
    ("v2-0436", "„estae."),  # ho-|nestae.
    # tranche 1 (scan check 09-Nov-2026, logs/apply_review.py)
    ('v2-0456', 'والجواميس'),
    ('v2-0456', 'χελωνίῳ,'),
    ('v2-0460', 'ὕστριξ'),
    ('v2-0461', 'بنحو'),
    ('v2-0469', 'بالارزاق'),
    ('v2-0469', 'رويت'),
    ('v2-0469', 'رازقي'),
    ('v2-0470', 'لنفسه'),
    ('v2-0472', 'animal,'),
    ('v2-0473', 'quaevis'),
    ('v2-0474', 'ضحك'),
    ('v2-0476', 'verisimile'),
    ('v2-0478', 'فيصاد'),
    ('v2-0482', 'Historiae'),
    ('v2-0489', 'זנה'),
    ('v2-0492', 'τάχ᾽'),
    ('v2-0494', 'ويغتصب'),
    ('v2-0497', 'ἶβις·'),
    ('v2-0500', 'Hebraeis'),
    ('v2-0501', 'חומטון'),
    ('v2-0505', 'נושם'),
    ('v2-0507', 'videbis'),
    ('v2-0509', 'ἐσθίειν,'),
    ('v2-0512', '2.'),
    ('v2-0515', '356 358.'),
    ('v2-0517', 'λεπτοῖσι'),
    ('v2-0517', 'ἐξεντερισθεῖσα,'),
    ('v2-0518', 'يتسند'),
    ('v2-0522', 'πρῖνον.'),
    ('v2-0522', 'verisimile;'),
    # tranche 2, group A (scan check 10-Nov-2026, apply_review.py)
    ('v2-0525', 'ἄμπελον,'),
    ('v2-0525', 'δὲ,'),
    ('v2-0526', 'Ἠΐδει'),
    ('v2-0527', 'verisimile'),
    ('v2-0530', 'rent'),
    ('v2-0530', 'filius,'),
    ('v2-0532', 'XXV.'),
    ('v2-0532', 'XII.'),
    ('v2-0534', 'effossum'),
    ('v2-0538', 'Φιλοσκίων.'),
    ('v2-0540', 'ἀπεικασθήσονται·'),
    ('v2-0541', 'Janse-'),
    ('v2-0542', 'Ἦιξαν'),
    # tranche 2, group B (scan check 10-Nov-2026, apply_review.py); p. 560 ועם is a FIXES item instead
    # (the Hebrew line was read in visual order)
    ('v2-0545', 'בארעיח'),
    ('v2-0545', 'פי פחת'),
    ('v2-0549', 'τοιῶς'),
    ('v2-0553', 'ἥπατι'),
    ('v2-0555', 'columbae'),
    ('v2-0556', 'ἀσθένειαν'),
    ('v2-0562', 'λῳ·'),
    ('v2-0563', 'θαλάττῃ,'),
    ('v2-0565', 'نوحا'),
    ('v2-0565', 'τῃσιν'),
    ('v2-0566', 'cum'),
    # tranche 2, group C (scan check 10-Nov-2026, apply_review.py); "tr[?]igesimo" (a blank sort in trigesimo,
    # p. 588) not taken
    ('v2-0567', 'νωμῶντες'),
    ('v2-0567', 'Parva'),
    ('v2-0572', 'constit.'),
    ('v2-0573', 'προσελθεῖν'),
    ('v2-0574', 'caussis,'),
    ('v2-0575', 'πρὸς'),
    ('v2-0580', 'ضعيف'),
    ('v2-0583', 'المملوحة'),
    ('v2-0583', 'الحمص'),
    ('v2-0588', 'χέδροπά'),
    ('v2-0588', 'caussis'),
    ('v2-0588', 'ἅλμην·'),
    # tranche 4 (scan check 12-Nov-2026)
    ('v2-0650', 'מאר,'),
    ('v2-0650', 'מאר,'),
    ('v2-0651', 'ἡλίκη τρυγὼν,'),
    ('v2-0652', 'פסיונין'),
    ('v2-0658', 'الكيموس'),
    ('v2-0658', 'licioris.'),
    ('v2-0659', 'انا'),
    ('v2-0660', 'ياتي'),
    ('v2-0660', 'عناية'),
    ('v2-0663', 'Proficisci'),
    ('v2-0666', 'θερινῆς'),
    ('v2-0666', 'Je'),
    ('v2-0680', 'אפרחהא.'),
    ('v2-0683', 'לשכוי,'),
    ('v2-0687', 'ישראל'),
    ('v2-0687', 'quo'),
    ('v2-0698', 'דמשתכחאביני'),
    ('v2-0711', 'כבש'),
    # tranche 5 (scan check 13-Nov-2026)
    ('v2-0722', 'בער'),
    ('v2-0722', 'ולצפצף,'),
    ('v2-0723', 'وهو'),
    ('v2-0725', 'צפצף'),
    ('v2-0734', 'שמשך,'),
    ('v2-0740', 'ἐὺν'),
    ('v2-0741', 'صهيب'),
    ('v2-0743', 'hodiernum'),
    ('v2-0748', 'ψυχρὰν'),
    ('v2-0760', 'הוה'),
    ('v2-0764', 'ἀετῶν'),
    ('v2-0764', 'secundo'),
    ('v2-0772', 'العظام'),
    ('v2-0775', 'Samaritana uza'),
    ('v2-0775', 'oznija.'),
    ('v2-0775', 'verisimiles,'),
    ('v2-0777', 'דדה,'),
}

# Differences that the scan cannot decide or that are conventions, not readings: never changed by the
# vote, listed for review. Each was seen in the pilot (01-Nov-2026).
SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹ᵃᵇᶜᵈᵉᶠᵍʰⁱʲᵏˡᵐⁿᵒᵖʳˢᵗᵘᵛʷˣʸᶻ", "0123456789abcdefghijklmnoprstuvwxyz")
MARK_PUNCT = str.maketrans("", "", "(){}^")


def ambiguous(old: str, new: str) -> str:
    o, n = key(old), key(new)
    if o.translate(SUPERSCRIPTS) == n.translate(SUPERSCRIPTS):
        return "note-mark format"
    # a note mark written as a superscript letter or with brackets: ^{b)} -> ^{(ᵇ)} (p. 568, 10-Nov-2026)
    if "^{" in old and o.translate(SUPERSCRIPTS).translate(MARK_PUNCT) == n.translate(SUPERSCRIPTS).translate(MARK_PUNCT):
        return "note-mark format"
    if len(o) == len(n) and all(a == b or {a, b} == {"ف", "غ"} for a, b in zip(o, n)):
        return "ف/غ: the same shape in this type (medial)"
    if len(o) == len(n) and all(a == b or {a, b} == {"ד", "ר"} for a, b in zip(o, n)):
        return "ד/ר: hardly different in this type on the scan (ch. 35: חולד read as חולר 8 times)"
    if len(o) == len(n) and all(a == b or {a, b} == {"ذ", "ن"} for a, b in zip(o, n)):
        return "ذ/ن: ذ is cup-shaped like ن in this type (ch. 35: ذلك, ذهبت)"
    if o.replace("ذ", "نن") == n or o.replace("ذ", "ن") == n:
        return "ذ/ن: ذ is cup-shaped like ن in this type (ch. 35: اذانها read as اننانها)"
    if re.sub("ου", "ε", o) == n or re.sub("ού", "έ", o) == n or o.replace("ου", "υ") == n:
        return "ȣ ligature (ου) read as ε or υ"
    if o.replace("στ", "ς") == n:
        return "στ ligature written ς"
    # the lower-case φ of this type is tall and looks like a capital: every φ -> Φ change of tranches 1-2
    # was wrong on the scan (11-Nov-2026)
    if o != n and len(o) == len(n) and all(a == b or {a, b} == {"φ", "Φ"} for a, b in zip(o, n)):
        return "φ/Φ: the lower-case φ of this type looks like a capital"
    if len(n) < len(o) and n in o and len(o) - len(n) >= 2:
        return "shorter reading (the judge read a part)"
    return ""


def by_word(it: dict) -> list[dict]:
    """A flag of several words is voted word by word when the judge read as many words as the main
    OCR; a reader with another word count has no vote on those words."""
    m, j = it["main"].split(), (it["printed"] or "").split()
    if len(m) < 2 or len(j) != len(m):
        return [it]
    out = []
    for i, w in enumerate(m):
        sub = {**it, "main": w, "printed": j[i]}
        for n in ("flash", "mdz"):
            r = it[n].split()
            sub[n] = r[i] if len(r) == len(m) else ""
        out.append(sub)
    return out


def apply(blocks: list[dict], line: str, old: str, new: str) -> bool:
    """Replace old by new in the block line most like `line` (an earlier change may have touched it)."""
    ev.LOOSE = True
    if not any(old in b["text"] for b in blocks):  # "<i>alphenec</i>,": try the word without its punctuation
        old, new = PUNCT.sub("", old), PUNCT.sub("", new)
    cands = [(fuzz.ratio(ev.norm(raw), line), bi, i) for bi, b in enumerate(blocks)
             for i, raw in enumerate(b["text"].split("\n")) if old in raw]
    if not cands or max(cands)[0] < 90:
        return False
    _, bi, i = max(cands)
    b = blocks[bi]
    lines = b["text"].split("\n")
    lines[i] = lines[i].replace(old, new, 1)
    b["text"] = "\n".join(lines)
    b["runs"] = [{"lang": b.get("lang", "other"), "text": b["text"]}]  # runs no longer split by language
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("first", type=int)
    p.add_argument("last", type=int)
    p.add_argument("--vol", type=int, default=2)
    p.add_argument("--main", default="or-claude-opus-5.5@low")
    p.add_argument("--judge", default="", help="judge tag: reads data/fix/{range}.judge.{tag}.jsonl (judge_page.py)")
    p.add_argument("--skip-mdz-only", action="store_true", help="ignore flags where only MDZ differs from the main OCR")
    a = p.parse_args()
    rng = f"v{a.vol}-{a.first}-{a.last}"
    sfx = (f".{a.judge}" if a.judge else "") + (".nomdz" if a.skip_mdz_only else "")
    recs = [json.loads(x) for x in (DATA / "fix" / f"{rng}.judge{'.' + a.judge if a.judge else ''}.jsonl")
            .read_text(encoding="utf-8").splitlines()]
    if a.skip_mdz_only:
        for rec in recs:
            rec["items"] = [it for it in rec["items"] if it["flash"] and it["flash"] != it["main"]]
    rows, decisions, tally = [], [], Counter()
    for rec in recs:
        for it in (w for item in rec["items"] for w in by_word(item)):
            pr = it["printed"] or ""
            k = key(pr)
            agree = [n for n in ("flash", "mdz") if it[n] and " ".join(key(w, n == "mdz") for w in it[n].split())
                     == " ".join(key(w, n == "mdz") for w in pr.split())]
            if " ".join(key(w) for w in pr.split()) == " ".join(key(w) for w in it["main"].split()):
                outcome, new = "keep", ""
            elif agree:
                new = it["flash"] if "flash" in agree else pr
                new = re.sub(r'(?<=[א-ת])"(?=[א-ת])', "״", new)  # Flash writes " for ״
                new = new.replace("ſ", "s")
                amb = ambiguous(it["main"], new)
                outcome = (f"rejected ({REJECT[rec['page'], it['main']]})" if (rec["page"], it["main"]) in REJECT
                           else f"review ({amb})" if amb and (rec["page"], it["main"]) not in ACCEPT else
                           "review (MDZ only)" if agree == ["mdz"] and (rec["page"], it["main"]) not in ACCEPT else
                           "change" if similar(it["main"], new) else "review (not similar)")
            else:
                outcome, new = ("review (judge read another text)" if k else "no answer"), ""
            tally[outcome] += 1
            if outcome == "change":
                decisions.append({"page": rec["page"], "line": rec["line"], "old": it["main"], "new": new,
                                  "script": it["script"], "agree": agree})
            rows.append({"page": rec["page"], "script": it["script"], "main": it["main"], "flash": it["flash"],
                         "mdz": it["mdz"], "judge": pr, "confident": it["confident"], "outcome": outcome,
                         "new": new, "line": rec["line"]})
    (DATA / "fix" / f"{rng}.decisions{sfx}.json").write_text(json.dumps(
        {"rule": "change where the image judge reads the same as Flash or MDZ, against the main OCR",
         "items": decisions}, ensure_ascii=False, indent=1), encoding="utf-8")
    out = ROOT / "logs" / f"vote_{rng}{sfx}.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    # the voted OCR as an engine of its own
    src, dst = DATA / "ocr" / a.main, DATA / "ocr" / f"{a.main}+vote{sfx.replace('.', '-')}"
    dst.mkdir(parents=True, exist_ok=True)
    failed = 0
    by_page = {}
    for d in decisions:
        by_page.setdefault(d["page"], []).append(d)
    for f in sorted(src.glob(f"v{a.vol}-*.json")):
        if not f.stem[3:].isdigit() or not a.first <= int(f.stem[3:]) <= a.last:
            continue  # only the pages of this range: other ranges have their own decisions
        res = json.loads(f.read_text(encoding="utf-8"))
        for d in by_page.get(f.stem, []):
            if not apply(res["blocks"], d["line"], d["old"], d["new"]):
                failed += 1
                print(f"  {f.stem}: not applied (tags inside the span?): {d['old']} -> {d['new']}")
        res["meta"] = {**res.get("meta", {}), "vote": f"{len(by_page.get(f.stem, []))} decisions from {rng}"}
        (dst / f.name).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(rows)} flags: {dict(tally)}; {len(decisions)} changes ({failed} not applied); "
          f"wrote {out} and {dst}")


if __name__ == "__main__":
    main()
