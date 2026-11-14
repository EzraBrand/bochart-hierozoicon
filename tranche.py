"""Run the unattended steps of a tranche in one go, with a log per step (11-Nov-2026).

  uv run tranche.py prepare 591 648 --tag t3 --group A:591-610 --group B:611-630 --group C:631-648
      fetch.py sample (SAMPLE must hold the pages) -> mdz_ocr.py -> OCR: Opus batch and Flash sync
      (4 workers) at the same time -> check.py -> judge.py --batch -> vote.py -> qa.py -> review_pack.py
  uv run tranche.py translate deror turtur hirundo --tag t3
      one batch for the chunks of all the chapters (entry.batch_all), then entry.py X for the fixed
      steps of every chapter, then the site

The second reader (Flash) ran as a batch in tranches 1-2 and took 26 minutes against Opus's 7; sync
with 4 workers it is done before the Opus batch is (about $0.50 more on 60 pages). Logs:
logs/tranche_{tag}_{step}.log. A step that fails stops the run; the steps are resumable (every script
skips what is done), so the same command is run again.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "logs"
PY = sys.executable
OPUS, FLASH = "anthropic/claude-opus-5.5", "google/gemini-3.8-flash"
PAID = {"judge", "ocr retry"}  # the steps of run() that call a model


def spend() -> float | None:
    """The key's total spend in USD (OpenRouter /api/v1/key). The batch results carry no cost, so the
    cost of a step is the difference before and after it (11-Nov-2026)."""
    try:
        import requests
        key = Path(os.environ["OPENROUTER_KEY_FILE"]).read_text(encoding="utf-8").strip()
        r = requests.get("https://openrouter.ai/api/v1/key", headers={"Authorization": "Bearer " + key}, timeout=60)
        return float(r.json()["data"]["usage"])
    except Exception as e:  # the cost line is a convenience: never stop a run for it
        print(f"(key spend not read: {type(e).__name__})", flush=True)
        return None


def balance_notice(need: float = 20.0) -> None:
    """Print a notice when the key's balance is low (14-Nov-2026). OpenRouter refuses a batch whose cost
    ESTIMATE (about 5 times the real cost) is above the balance; orbatch then sends the batch in parts, one
    after the other, which costs waiting time. The agent that runs the tranche tells the owner at once."""
    try:
        import requests
        key = Path(os.environ["OPENROUTER_KEY_FILE"]).read_text(encoding="utf-8").strip()
        d = requests.get("https://openrouter.ai/api/v1/key", headers={"Authorization": "Bearer " + key}, timeout=60).json()["data"]
        left = d.get("limit_remaining")
        if left is not None and left < need:
            print(f"NOTICE FOR THE OWNER: the key has ${left:.2f} left (expires {str(d.get('expires_at'))[:10]}). "
                  f"Below about ${need:.0f} a batch can be refused for its estimate and is then sent in parts "
                  f"(slower, same price). Below about $10 a tranche of 80 pages cannot finish.", flush=True)
    except Exception as e:
        print(f"(key balance not read: {type(e).__name__})", flush=True)


def cost_since(before: float | None, name: str) -> None:
    after = spend()
    if before is not None and after is not None:
        print(f"[{time.strftime('%H:%M')}] {name}: cost ${after - before:.2f} (key spend ${after:.2f})", flush=True)


def log_path(tag: str, step: str) -> Path:
    LOGS.mkdir(exist_ok=True)
    return LOGS / f"tranche_{tag}_{step}.log"


def start(args: list[str], log: Path) -> subprocess.Popen:
    fh = log.open("a", encoding="utf-8")
    fh.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} {' '.join(args)}\n")
    fh.flush()
    return subprocess.Popen([PY, *args], cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT,
                            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})


def run(args: list[str], log: Path, name: str) -> None:
    t = time.monotonic()
    before = spend() if name in PAID else None
    print(f"[{time.strftime('%H:%M')}] {name}: {' '.join(args)} -> {log.name}", flush=True)
    p = start(args, log)
    p.wait()
    cost_since(before, name)
    print(f"[{time.strftime('%H:%M')}] {name}: exit {p.returncode} after {(time.monotonic() - t) / 60:.1f} min", flush=True)
    if p.returncode:
        print(log.read_text(encoding="utf-8")[-1500:])
        sys.exit(f"{name} failed; see {log}")


def keys(first: int, last: int) -> list[str]:
    return [f"v2-{p:04d}" for p in range(first, last + 1)]


def missing(engine: str, ks: list[str]) -> list[str]:
    return [k for k in ks if not (ROOT / "data" / "ocr" / engine / f"{k}.json").exists()]


def prepare(a) -> None:
    balance_notice()
    ks = keys(a.first, a.last)
    run(["fetch.py", "sample"], log_path(a.tag, "fetch"), "fetch")
    for k in ks:
        if not (ROOT / "data" / "mdz_hocr" / f"{k}.hocr").exists():
            sys.exit(f"{k}: no MDZ hOCR (canvas not in SAMPLE, or MDZ answered 500: run fetch.py sample again)")
    run(["mdz_ocr.py", *ks], log_path(a.tag, "mdz_ocr"), "mdz_ocr")
    # OCR: the Opus batch and the Flash workers at the same time
    t = time.monotonic()
    before = spend()
    procs = []
    if missing("or-claude-opus-5.5@low", ks):
        procs.append(("opus batch", start(["ocr.py", *ks, "--model", OPUS, "--compact", "--batch",
                                           "--max-tokens", str(a.max_tokens), "--batch-log", f"ocr_opus_{a.tag}"],
                                          log_path(a.tag, "ocr_opus"))))
    if missing("or-gemini-3.8-flash@low", ks):
        for i in range(a.workers):
            procs.append((f"flash {i}", start(["ocr.py", *ks, "--model", FLASH, "--compact",
                                               "--start", str(i), "--stride", str(a.workers)],
                                              log_path(a.tag, "ocr_flash"))))
    print(f"[{time.strftime('%H:%M')}] OCR: {len(procs)} processes started", flush=True)
    for name, p in procs:
        p.wait()
        print(f"[{time.strftime('%H:%M')}] {name}: exit {p.returncode} after {(time.monotonic() - t) / 60:.1f} min", flush=True)
    cost_since(before, "OCR (Opus batch + Flash)")
    for engine, model, extra in (("or-claude-opus-5.5@low", OPUS, ["--max-tokens", str(a.max_tokens)]),
                                 ("or-gemini-3.8-flash@low", FLASH, [])):
        if missing(engine, ks):  # a page that failed in the batch or a worker: once more, sync
            print(f"{engine}: {len(missing(engine, ks))} page(s) missing, retried sync: {missing(engine, ks)}", flush=True)
            run(["ocr.py", *missing(engine, ks), "--model", model, "--compact", *extra], log_path(a.tag, "ocr_retry"), "ocr retry")
        if missing(engine, ks):
            sys.exit(f"{engine}: still missing {missing(engine, ks)}")
    rng = [str(a.first), str(a.last)]
    run(["check.py", *rng], log_path(a.tag, "check"), "check")
    run(["judge.py", *rng, "--batch"], log_path(a.tag, "judge"), "judge")
    run(["vote.py", *rng], log_path(a.tag, "vote"), "vote")
    run(["qa.py", *rng, "--main", "or-claude-opus-5.5@low+vote"], log_path(a.tag, "qa"), "qa")
    groups = [x for g in a.group for x in ("--group", g)]
    run(["review_pack.py", *rng, *groups], log_path(a.tag, "review_pack"), "review_pack")
    print(f"[{time.strftime('%H:%M')}] prepared pp. {a.first}-{a.last}: read logs/tranche_{a.tag}_qa.log and "
          f"logs/tranche_{a.tag}_vote.log; the scan check reads logs/review/*/items.tsv", flush=True)


def translate(a) -> None:
    balance_notice()
    t = time.monotonic()
    before = spend()
    # one batch for all the chapters' chunks (12-Nov-2026; a batch per chapter before), then the fixed steps
    run(["-c", f"import entry; entry.batch_all({a.entries!r}, {OPUS!r}, {a.effort!r}, {a.tag!r})"],
        log_path(a.tag, "translate_batch"), "translation batch")
    procs = [(e, start(["entry.py", e, "--batch", "--effort", a.effort], log_path(a.tag, f"translate_{e}")))
             for e in a.entries]
    failed = []
    for e, p in procs:
        p.wait()
        print(f"[{time.strftime('%H:%M')}] {e}: exit {p.returncode} after {(time.monotonic() - t) / 60:.1f} min", flush=True)
        if p.returncode:
            failed.append(e)
            print(log_path(a.tag, f"translate_{e}").read_text(encoding="utf-8")[-800:])
    cost_since(before, "translation")
    if failed:
        sys.exit(f"failed: {failed}")
    for e in a.entries:
        meta = json.loads((ROOT / "data" / "entries" / e / "en.json").read_text(encoding="utf-8"))["meta"]
        print(f"{e}: {len(meta.get('names_identified', []))} names identified, "
              f"{len(meta.get('abbreviations_expanded', []))} abbreviations expanded")
    run(["build_site.py"], log_path(a.tag, "build_site"), "build_site")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(required=True)
    s = sub.add_parser("prepare")
    s.add_argument("first", type=int)
    s.add_argument("last", type=int)
    s.add_argument("--tag", required=True)
    s.add_argument("--group", action="append", default=[], help="review_pack groups NAME:FIRST-LAST")
    s.add_argument("--workers", type=int, default=4, help="Flash sync workers")
    s.add_argument("--max-tokens", type=int, default=7000, help="Opus OCR batch (the balance hold is estimated from it)")
    s.set_defaults(func=prepare)
    s = sub.add_parser("translate")
    s.add_argument("entries", nargs="+")
    s.add_argument("--tag", required=True)
    s.add_argument("--effort", default="low")
    s.set_defaults(func=translate)
    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
