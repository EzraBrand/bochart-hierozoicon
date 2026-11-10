"""Candidate names for names.json: capitalized Latin words of one or more entries that no row of the
table covers, with their count and one context line, for review (10-Nov-2026).

  uv run names_candidates.py jonah columba-pennae ...      # entries (data/entries/*/la.json)

Sentence-initial words and common Latin capitalized words are left out by a stop list; the rest is a
list to read, not a decision: a row is added to names.json by hand (basis "general knowledge" when
not checked in a catalogue).
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import abbrev
import names

sys.stdout.reconfigure(encoding="utf-8")
DATA = Path(__file__).parent / "data"
STOP = set("""Et Sed Nam Quod Quae Qui Quia Quum Cum Ita Itaque Unde Hinc Hic Haec Hoc Id Ad In Ex De Non Ut Si
Sic Vel Aut Nec Neque Enim Autem Vero Verum Ergo Igitur Tum Tunc Deinde Primo Secundo Tertio Quarto Quinto
Sexto Septimo Octavo Nono Decimo Denique Porro Praeterea Quin Quippe Nempe Scilicet Videlicet Item Idem
Eadem Ipse Ipsa Ille Illa Illud Is Ea Iste Ista Istud Nos Vos Ego Tu Deus Dei Deo Deum Dominus Domini Domino
Christus Christi Christo Christum Spiritus Sanctus Hebraei Hebraeis Hebraeo Hebraeorum Hebraea Hebraice
Graeci Graecis Graece Graeca Graecum Graecorum Latini Latine Latina Latinis Arabes Arabibus Arabice Arabum
Arabs Syri Syris Syriace Syrus Chaldaeus Chaldaei Chaldaice Chaldaeo Chaldaeum Judaei Iudaei Judaeis Iudaeis
Judaeorum Iudaeorum Persae Persice Aethiopes Aethiopice Aegyptii Aegyptiis Aegypti Aegypto Aegyptus Romani
Romanis Romanorum Galli Gallis Gallice Germani Germanice Itali Italice Hispani Hispanice Angli Anglice
Belgae Belgice Poloni Turcae Turcice Indi Scriptura Scripturae Sacra Sacrae Sacri Scriptores Scriptoribus
Lex Legis Lege Levit Gen Exod Deut Num Psal Prov Eccles Esa Ies Ierem Ezech Dan Os Ioel Amos Ion Mich Nah
Hab Soph Zach Mal Matth Marc Luc Ioh Act Rom Cor Gal Eph Phil Col Thess Tim Tit Hebr Iac Pet Iud Apoc Reg
Sam Par Esdr Nehem Esth Iob Cant Thren Sap Sir Tob Iudith Macc Cap Lib Tom Pag Vers Vs Fol Col Vide Vid
Infra Supra Ibid Ibidem Loc Cit Seq Seqq Edit Ed Apud Alii Aliis Alias Alius Aliud Multi Omnes Omnia Omne
Plura Pleraque Quidam Quaedam Quoddam Nonnulli Pauci Quis Quid Quot Quomodo Quare Cur Quando Ubi Unde Quo
Qua Quam Quanto Quantum Tam Tamen Tandem Atque Ac Etiam Quoque Adeo Imo Immo Nihil Nil Nemo Nullus Nulla
Nullum Totus Tota Totum Omnis Omni Alter Altera Alterum Uterque Utraque Utrumque Neuter Prior Posterior
Primum Secundum Tertium Ultimo Postremo Praeter Propter Per Pro Prae Post Ante Inter Intra Extra Super
Sub Circa Contra Ob Ab A Ea Eo Eam Eum Eius Ejus Eorum Earum Illi Illis Illius Illum Illam Hujus Huius
Horum Harum His Hos Has Hac Hunc Hanc Hi Hae Haec Hoc Alia Aliam Alio Aliqui Aliqua Aliquid Aliquis Quas
Quos Quibus Quorum Quarum Cujus Cuius Cui Quem Quum Qualis Quale Talis Tale Tales Talia Tot Tanta Tantum
Tanti Olim Nunc Iam Jam Semper Nunquam Numquam Saepe Raro Modo Mox Statim Simul Interim Postea Antea Deinceps
Rursus Rursum Iterum Vicissim Vix Fere Ferme Paene Pene Plane Prorsus Omnino Certe Certo Sane Profecto
Nimirum Utique Forte Fortasse Forsan Forsitan Fortassis Videtur Videntur Vide Notandum Observandum Respondeo
Respondet Dico Dicit Dicitur Dicunt Dicuntur Inquit Inquiunt Ait Aiunt Scribit Scribunt Addit Addunt Legitur
Leguntur Legendum Lege Vertit Vertunt Verterunt Reddit Reddunt Reddidit Reddiderunt Interpres Interpretes
Interpretatur Interpretantur Exponit Exponunt Explicat Explicant Significat Significant Sequitur Sequuntur
Constat Patet Liquet Apparet Probatur Probat Confirmatur Colligitur Conjicio Suspicor Puto Credo Censeo
Existimo Arbitror Opinor Fateor Nego Negat Negant Concedo Pergit Pergunt Columba Columbae Columbam
Columbarum Columbis Columbas Turtur Turturis Turturem Turtures Turturum Turturibus Aves Avis Avem Avium
Avibus Oriens Orientis Orientales Occidens Occidentales Septentrio Meridies Mundus Mundi Mundo Mundum
Terra Terrae Terram Mare Maris Caelum Coelum Coeli Sol Solis Luna Lunae Rex Regis Regi Regem Reges Regum
Regibus Regina Propheta Prophetae Prophetam Prophetarum Apostolus Apostoli Evangelista Evangelium Evangelii
Ecclesia Ecclesiae Templum Templi Templo Lex Sabbatum Pascha Pentecoste Festum Natalis Nativitas Baptismus
Baptismo Baptismi Spiritu Spiritum Filius Filii Filium Filio Pater Patris Patrem Patri Mater Matris Verbum
Verbi Verbo Vox Vocis Vocem Voce Voces Vocibus Nomen Nominis Nomine Nomina Nominibus Radix Radice Radicis
Verbum Verba Nota Notae Notandum Textus Textu Versio Versione Versiones Versionis Lectio Lectione Codex
Codices Codicis Codice Codicibus Exemplar Exemplaria Editio Editione Liber Libri Libro Librum Libris Libros
Pars Parte Partem Caput Capite Capitis Capita Sectio Titulus Tractatus Tractatu Glossa Glossae Commentarius
Commentario Commentarii Scholia Scholiastes Scholiasta Lexicon Lexico Lexici Vocabularium Thesaurus Historia
Historiae Historiam Natura Naturae Naturam Naturali Naturalis Animal Animalis Animalia Animalium Animali
Genus Generis Genere Genera Species Speciei Speciem Auctor Auctores Auctoris Auctorum Auctore Poeta Poetae
Philosophus Philosophi Medicus Medici Geographus Grammaticus Grammatici Historicus Historici Rabbi Rabbini
Rabbinis Rabbinorum Rabbinus Talmud Talmudis Talmude Talmudici Talmudistae Targum Targumim Thargum Massora
Massorethae Misna Mischna Gemara Midrasch Medrasch Kabbala Cabbala Seniores Vulgatus Vulgata Vulgatae Vulgato
Vulgatum Syra Syrae Syro Syrum Arabica Arabicae Arabicam Arabico Arabicum Chaldaea Chaldaeae Chaldaicum
Persica Persicae Persicum Aethiopica Aethiopicae Aethiopicum Samaritana Samaritanus Samaritani Graecus
Graecam Graeco Latinus Latinum Latino Latinam Hebraeus Hebraeum Hebraeam Hebraicum Hebraica Hebraicae
Hebraicam Hebraico Alcoranus Alcorani Alcorano Alcoranum Alcorani Azoara Sura Hagiographa Pentateuchus
Pentateuchi Septuaginta Vetus Veteris Veteri Veteres Veterum Veteribus Novum Novi Novo Recentiores Recentiorum
Recentioribus Antiqui Antiquorum Antiquis Antiquitas Antiquitatis Iuniores Juniores Nostri Nostrorum Nostris
Noster Nostra Nostrum Vestri Posteri Posterorum Majores Maiores Patres Patrum Patribus Doctores Doctorum
Doctoribus Magistri Magistrorum Magister Discipuli Discipulus Sapientes Sapientum Sapientium Sapiens
Scribae Pharisaei Sadducaei Esseni Karaei Caraei Karaitae Samaritani Cuthaei Idumaei Ismaelitae Agareni
Saraceni Mauri Turcae Tartari Indi Sinae Chinenses Aethiopes Abyssini Nubae Libyes Afri Africani Punici
Poeni Carthaginienses Phoenices Tyrii Sidonii Syri Assyrii Babylonii Chaldaei Medi Parthi Armenii Cappadoces
Cilices Lydi Phryges Cares Iones Aeoles Dores Achaei Lacedaemonii Spartani Athenienses Thebani Corinthii
Macedones Thraces Scythae Sarmatae Getae Daci Illyrii Pannonii Germani Galli Britanni Hispani Lusitani Itali
Siculi Sardi Corsi Cretenses Cyprii Rhodii Lesbii Chii Samii Cyrenaei Alexandrini Aegyptii Arabes Nabataei
Idumaei Moabitae Ammonitae Philisthaei Philistaei Cananaei Chananaei Amorrhaei Hethaei Jebusaei Hevaei
Pheresaei Gergesaei Amalecitae Madianitae Edomitae Israelitae Israel Israelis Judah Iuda Juda Jerusalem
Hierosolyma Hierosolymae Hierosolymis Hierosolymitani Sion Zion Moria Galilaea Galilaeae Samaria Samariae
Judaea Iudaea Judaeae Iudaeae Palaestina Palaestinae Palaestinam Syria Syriae Syriam Mesopotamia Babylon
Babylonis Babylone Ninive Assyria Persia Media Arabia Arabiae Arabiam Aegyptus Aegypti Aegypto Aegyptum
Aethiopia Aethiopiae Libya Libyae Africa Africae Asia Asiae Europa Europae Graecia Graeciae Italia Italiae
Roma Romae Romam Gallia Galliae Germania Germaniae Hispania Hispaniae Britannia Anglia Hollandia Belgium
India Indiae Indiam Sina Nilus Nili Nilo Nilum Jordanis Iordanis Jordanem Euphrates Euphratis Tigris Tigridis
Libanus Libani Carmelus Carmeli Sinai Horeb Hermon Tabor Ierusalem Noachus Noachi Noacho Noachum Noe Noemi
Abraham Abrahamus Abrahami Abrahamo Isaac Isaaci Jacob Iacob Jacobi Iacobi Joseph Ioseph Moses Mosis Mosi
Mosen Mose Aaron Aaronis David Davidis Davidi Davide Davidem Salomo Salomon Salomonis Salomoni Salomonem
Salomone Esaias Esaiae Jesaias Jeremias Jeremiae Ieremias Ezechiel Ezechielis Daniel Danielis Hoseas Oseas
Joel Ioel Amos Abdias Jonas Ionas Jonae Ionae Micha Michaeas Nahum Habacuc Sophonias Haggaeus Zacharias
Zachariae Malachias Job Iob Jobi Iobi Ruth Esther Nehemias Esdras Tobias Judith Iudith Maccabaei Petrus
Petri Paulus Pauli Paulo Paulum Johannes Ioannes Joannes Johannis Ioannis Joannis Matthaeus Matthaei
Marcus Marci Lucas Lucae Jacobus Iacobus Judas Iudas Maria Mariae Elisabeth Herodes Herodis Pilatus
Caesar Caesaris Caesare Augustus Augusti Tiberius Tiberii Nero Neronis Vespasianus Titus Domitianus
Trajanus Hadrianus Constantinus Constantini Justinianus Alexander Alexandri Alexandro Alexandrum Philippus
Philippi Darius Darii Cyrus Cyri Xerxes Xerxis Artaxerxes Nabuchodonosor Nabuchodonosoris Sennacherib
Salmanassar Pharao Pharaonis Pharaone Venus Veneris Veneri Venerem Jupiter Iupiter Jovis Iovis Jovi Jovem
Juno Iuno Junonis Minerva Minervae Apollo Apollinis Diana Dianae Mars Martis Mercurius Mercurii Neptunus
Vulcanus Bacchus Bacchi Ceres Cereris Vesta Pluto Saturnus Saturni Hercules Herculis Aeneas Aeneae Achilles
Ulysses Hector Priamus Helena Paris Troja Troia Trojae Trojani Troiani""".split())


def main():
    rows = names.items()
    known = {f for r in rows for f in r["forms"]}
    cnt, ctx = Counter(), {}
    for e in sys.argv[1:]:
        la = json.loads((DATA / "entries" / e / "la.json").read_text(encoding="utf-8"))
        for b in la["main"] + la["notes"]:
            text = abbrev.joined(b["text"])
            for m in re.finditer(r"(?<![\w.])([A-Z][a-z]{3,})(?!\w)", text):
                w = m.group(1)
                if w in STOP or w in known or w.lower() in STOP:
                    continue
                # a sentence-initial word (after . ! ? or at the start) is skipped
                before = text[:m.start()].rstrip()
                if not before or before[-1] in ".!?":
                    continue
                cnt[w] += 1
                ctx.setdefault(w, (e, text[max(0, m.start() - 60):m.end() + 40].replace("\n", " ")))
    for w, n in cnt.most_common():
        e, c = ctx[w]
        print(f"{n:3d}  {w:<20} {e:<12} …{c}…")


if __name__ == "__main__":
    main()
