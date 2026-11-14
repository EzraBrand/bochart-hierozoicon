"""Names: a reviewed table (names.json) for the prompt, and identifications added after translation.

Latin declines names (Hieronymo, Plinii, Geuhario); the English needs one form for each person or
work. prompt_rows() lists, for the names that occur in a chunk, the English form the model must
use. identify() then adds " [=identification]" after the first use of each English form in a
document (a fixed step, not the model), for the rows that have one (TRANSLATION_RULES.md §4).
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
TABLE = ROOT / "names.json"


def items() -> list[dict]:
    return json.loads(TABLE.read_text(encoding="utf-8"))["items"] if TABLE.exists() else []


def form_rx(form: str) -> re.Pattern:
    return re.compile(rf"(?<!\w){re.escape(form)}(?!\w)")


def prompt_rows(text: str) -> str:
    text = re.sub(r"</?i>", "", re.sub(r"-\n(?=\w)", "", text)).replace("\n", " ")
    rows = [r for r in items() if any(form_rx(f).search(text) for f in r["forms"])]
    if not rows:
        return "(none)"
    return "\n".join(f'- {" / ".join(r["forms"])} -> "{r["english"]}"' for r in rows)


def identify(docs: list[list[dict]], skip: dict | None = None) -> list[str]:
    """Add the identification after the first use of each English form, in reading order, in place.
    -> the English forms identified. skip = {English form: n}: the first n uses in this chapter are
    another person of the same name and get no identification (entry "no_id"; 14-Nov-2026: "Elias" the
    prophet in the chapters on the ravens is not Elijah Levita; "Jonathan" on p. 751 is the son of Saul)."""
    skip = dict(skip or {})
    done = []
    rows = sorted((r for r in items() if r["id"]), key=lambda r: -len(r["english"]))
    for r in rows:
        # after the name, a possessive ("Giggeius'", "Gesner's") and a closing </i> that ends it; not inside
        # a longer word ("Kimchis", the plural: 10-Nov-2026)
        rx = re.compile(rf"(?<!\w)({re.escape(r['english'])}(?:'s|')?(?:</i>)?)(?!\w)")
        for blocks in docs:
            for b in blocks:
                def put(m, r=r):
                    if skip.get(r["english"], 0) > 0:
                        skip[r["english"]] -= 1
                        return m.group(0)
                    put.done = True
                    return f"{m.group(1)} [={r['id']}]"
                put.done = False
                new = rx.sub(lambda m: put(m) if not put.done else m.group(0), b["text"])
                n = put.done
                if n:
                    b["text"] = new
                    done.append(r["english"])
                    break
            else:
                continue
            break
    return done
