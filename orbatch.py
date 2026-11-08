"""OpenRouter Batch API: half price for requests that may wait (median about 7 minutes, at most 24 h).

  from orbatch import run_batch
  results = run_batch("anthropic/claude-opus-5.5", {"v2-0410": body, ...}, log_name="ocr_opus")

A body has the same shape as for /v1/chat/completions (without "model"). The batch id is saved in
logs/batch_{log_name}.json at submit, so a stopped script resumes polling with the same id
(nothing is paid twice). Results come back as {custom_id: chat-completion response body or
{"error": ...}}.
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).parent
KEY_FILE = Path(os.environ.get("OPENROUTER_KEY_FILE", Path.home() / "Desktop/Misc/key.txt"))
API = "https://openrouter.ai/api/v1/batches"


def _headers() -> dict:
    return {"Authorization": "Bearer " + KEY_FILE.read_text(encoding="utf-8").strip()}


def submit(model: str, bodies: dict[str, dict], provider: dict | None = None,
           endpoint: str = "/v1/chat/completions") -> str:
    """endpoint "/v1/messages" (Anthropic format) takes base64 images; "/v1/chat/completions" only URLs."""
    batch_model = model if model.endswith(":batch") else model + ":batch"
    payload = {"endpoint": endpoint, "model": batch_model}
    if provider:
        payload["provider"] = provider
    # "requests" must come last: the server reads the body as a stream
    payload["requests"] = [{"custom_id": cid, "body": {**b, "model": batch_model}} for cid, b in bodies.items()]
    r = requests.post(API, headers=_headers(), json=payload, timeout=600)
    d = r.json()
    if not r.ok:
        raise RuntimeError(f"batch submit: HTTP {r.status_code}: {d}")
    return (d.get("data") or d)["id"]


def get(batch_id: str) -> dict:
    r = requests.get(f"{API}/{batch_id}", headers=_headers(), timeout=120)
    d = r.json()
    if not r.ok:
        raise RuntimeError(f"batch get: HTTP {r.status_code}: {d}")
    return d.get("data") or d


def wait(batch_id: str, every: int = 60) -> dict:
    t = time.monotonic()
    misses = 0
    while True:
        try:
            b = get(batch_id)
        except RuntimeError as e:  # a new batch can answer 404 for a short time after submit
            misses += 1
            if "404" not in str(e) or misses > 10:
                raise
            print(f"batch {batch_id}: not found yet, retry", flush=True)
            time.sleep(every)
            continue
        st = b.get("status")
        counts = b.get("request_counts") or {}
        print(f"batch {batch_id}: {st} {counts} ({(time.monotonic() - t) / 60:.1f} min)", flush=True)
        if st in ("completed", "failed", "expired", "cancelled"):
            if b.get("error"):
                print(f"batch {batch_id}: error {b['error']}", flush=True)
            return b
        time.sleep(every)


def results(b: dict) -> dict[str, dict]:
    out = {}
    for r in b.get("results") or []:
        resp = r.get("response")
        out[r["custom_id"]] = resp["body"] if resp and resp.get("body") else {"error": r.get("error") or resp}
    return out


def run_batch(model: str, bodies: dict[str, dict], log_name: str, provider: dict | None = None,
              endpoint: str = "/v1/chat/completions") -> dict[str, dict]:
    state = ROOT / "logs" / f"batch_{log_name}.json"
    state.parent.mkdir(exist_ok=True)
    if state.exists():
        batch_id = json.loads(state.read_text(encoding="utf-8"))["id"]
        print(f"resuming batch {batch_id} ({state.name})", flush=True)
    else:
        batch_id = submit(model, bodies, provider, endpoint)
        state.write_text(json.dumps({"id": batch_id, "model": model, "n": len(bodies),
                                     "submitted": time.strftime("%Y-%m-%d %H:%M")}), encoding="utf-8")
        print(f"submitted batch {batch_id}: {len(bodies)} requests to {model}:batch", flush=True)
    b = wait(batch_id)
    res = results(b)
    cost = sum((x.get("usage") or {}).get("cost", 0) for x in res.values())
    print(f"batch {batch_id}: {b.get('status')}, {len(res)} results, cost ${cost:.4f}", flush=True)
    return res


if __name__ == "__main__":  # uv run orbatch.py BATCH_ID: status of a batch
    sys.stdout.reconfigure(encoding="utf-8")
    b = get(sys.argv[1])
    print(json.dumps({k: v for k, v in b.items() if k != "results"}, indent=1))
