"""Abbreviations: a reviewed table and a fixed expansion step after translation (no model).

  uv run abbrev.py                       # check all entries, render ABBREVIATIONS.md
  uv run abbrev.py --candidates shafan   # dotted words not in the table, for review

abbreviations.json is maintained by hand (see its "note"). Rows with mode "expand" stay as printed
in the translation (the prompt says so) and expand() adds " [=expansion]" after the first use in a
document. Rows with mode "translate" are general Latin abbreviations the model renders in English.
check() counts each "expand" row in the Latin and in the English of an entry, so that a model
that translates or drops one is caught. Ported from lewysohn-zoologie.
"""

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
TABLE = ROOT / "abbreviations.json"
OUT_MD = ROOT / "ABBREVIATIONS.md"
KINDS = {"source": "Primary sources", "bibliography": "Bibliography (authors and works cited by name)",
         "general": "General abbreviations"}


def items() -> list[dict]:
    return json.loads(TABLE.read_text(encoding="utf-8"))["items"] if TABLE.exists() else []


def pattern(abbr: str) -> str:
    """The abbreviation as a whole token: not inside a longer word."""
    return rf"(?<![\w.]){re.escape(abbr)}(?!\w)"


def joined(text: str) -> str:
    """Source text with printed line breaks and <i> tags undone ("Hiero-\\nnymi" -> "Hieronymi")."""
    return re.sub(r"</?i>", "", re.sub(r"-\n(?=\w)", "", text).replace("\n", " "))


def found(text: str, rows: list[dict]) -> list[dict]:
    """Rows that occur in text, longest first; a shorter one inside a longer one does not count."""
    text, hits = joined(text), set()
    for r in sorted(rows, key=lambda r: -len(r["abbr"])):
        rx = re.compile(pattern(r["abbr"]))
        if rx.search(text):
            hits.add(r["abbr"])
            text = rx.sub(lambda m: "\0" * len(m.group(0)), text)
    return [r for r in rows if r["abbr"] in hits]


def prompt_rows(text: str) -> str:
    """The two lists for the translation prompt, limited to what occurs in the input."""
    rows = found(text, items())
    keep = ", ".join(f'"{r["abbr"]}"' for r in rows if r["mode"] == "expand") or "(none)"
    tr = ", ".join(f'"{r["abbr"]}" -> "{r["english"]}"' for r in rows if r["mode"] == "translate") or "(none)"
    return f"Keep as printed: {keep}\nTranslate: {tr}"


def expand(docs: list[list[dict]]) -> dict[str, int]:
    """Add " [=expansion]" after the first use of each "expand" row, in reading order, in place."""
    rows = sorted((r for r in items() if r["mode"] == "expand"), key=lambda r: -len(r["abbr"]))
    if not rows:
        return {}
    by_abbr = {r["abbr"]: r for r in rows}
    rx = re.compile("|".join(f"({pattern(r['abbr'])})" for r in rows))
    uses: dict[str, int] = {}
    for blocks in docs:
        for b in blocks:
            def sub(m):
                a = m.group(0)
                uses[a] = uses.get(a, 0) + 1
                return f"{a} [={by_abbr[a]['expansion']}]" if uses[a] == 1 else a
            b["text"] = rx.sub(sub, b["text"])
    return uses


def check(src_text: str, en_text: str) -> list[str]:
    """-> problems: "expand" rows whose count differs between the Latin and the English."""
    out = []
    en_text = re.sub(r" \[=[^\]]*\]", "", re.sub(r"</?i>", "", en_text))
    for r in items():
        if r["mode"] != "expand":
            continue
        n_src = len(re.findall(pattern(r["abbr"]), joined(src_text)))
        n_en = len(re.findall(pattern(r["abbr"]), en_text))
        if n_src != n_en:
            out.append(f"{r['abbr']}: {n_src} in the Latin, {n_en} in the English")
    return out


def render() -> str:
    lines = ["# Abbreviations and short references", "",
             "Generated file: edit `abbreviations.json` and run `uv run abbrev.py`. Built from the "
             "abbreviations as they occur, and reviewed by hand. **expand**: kept as printed in the English, "
             "with the expansion added after the first use (a fixed step, not the model). **translate**: a "
             "general Latin abbreviation, rendered in English by the translation. Basis: **standard**; "
             "**context**; **general knowledge**; **guess** = not certain, check.", ""]
    for kind, title in KINDS.items():
        rows = sorted((r for r in items() if r["kind"] == kind), key=lambda r: r["abbr"].casefold())
        if not rows:
            continue
        lines += [f"## {title}", "", "| Abbreviation | Expansion | Mode | Basis |", "|---|---|---|---|"]
        for r in rows:
            exp = r["expansion"] + (f" → *{r['english']}*" if r["mode"] == "translate" else "")
            lines.append("| " + " | ".join(c.replace("|", "\\|") for c in (r["abbr"], exp, r["mode"], r["basis"])) + " |")
        lines.append("")
    return "\n".join(lines)


CANDIDATE = re.compile(r"(?<![\w.])(?:[A-Za-z][a-z]{0,7}\.\s?){1,4}")


def candidates(entry: str) -> list[tuple[str, int]]:
    """Dotted short words in an entry's Latin that no table row covers, with counts, for review."""
    la = json.loads((ROOT / "data" / "entries" / entry / "la.json").read_text(encoding="utf-8"))
    text = joined("\n".join(b["text"] for b in la["main"] + la["notes"]))
    for r in sorted(items(), key=lambda r: -len(r["abbr"])):
        text = re.sub(pattern(r["abbr"]), " ", text)
    counts: dict[str, int] = {}
    for m in CANDIDATE.finditer(text):
        c = m.group(0).strip()
        after = text[m.end():m.end() + 2].strip()[:1]
        if " " not in c and len(c) > 3 and (not after or after.isupper()):
            continue  # a sentence end, not an abbreviation
        counts[c] = counts.get(c, 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--candidates":
        for c, n in candidates(sys.argv[2]):
            print(f"{n:4d}  {c}")
        return
    for path in sorted((ROOT / "data" / "entries").iterdir()):
        if (path / "en.json").exists():
            la = json.loads((path / "la.json").read_text(encoding="utf-8"))
            en = json.loads((path / "en.json").read_text(encoding="utf-8"))
            problems = check("\n".join(b["text"] for b in la["main"] + la["notes"]),
                             "\n".join(b["text"] for b in en["main"] + en["notes"]))
            print(f"{path.name}: " + ("; ".join(problems) if problems else "every 'expand' abbreviation kept"))
    OUT_MD.write_text(render(), encoding="utf-8")
    print(f"wrote {OUT_MD.name}")


if __name__ == "__main__":
    main()
