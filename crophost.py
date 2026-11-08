"""Public URLs for image crops, for the OpenRouter Batch API (which takes no base64 images).

  from crophost import publish
  urls = publish({"ocr/v2-0430_1.jpg": img, ...})      # PIL images -> raw.githubusercontent.com URLs
  uv run crophost.py clean                              # after the run: empty the repo (force push)

The crops go into a local clone of the public repo EzraBrand/bochart-hierozoicon-crops (a folder
next to this repo, or CROPS_DIR), are committed and pushed; publish() returns when the first URL
answers. Files of earlier publish() calls stay until `clean`, so an OCR and a judge batch can run
at the same time. `clean` replaces the history with one commit that has only the README.
"""

import io
import os
import subprocess
import sys
import time
from pathlib import Path

import requests
from PIL import Image

REPO = "EzraBrand/bochart-hierozoicon-crops"
CLONE = Path(os.environ.get("CROPS_DIR", Path(__file__).resolve().parent.parent / "bochart-hierozoicon-crops"))
RAW = f"https://raw.githubusercontent.com/{REPO}/main/"


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=CLONE, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def jpeg(img: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return buf.getvalue()


def publish(images: dict[str, Image.Image | bytes], quality: int = 90) -> dict[str, str]:
    if not (CLONE / ".git").exists():
        subprocess.run(["git", "clone", "-q", f"https://github.com/{REPO}.git", str(CLONE)], check=True)
    git("pull", "-q", "--rebase")
    for rel, img in images.items():
        f = CLONE / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(img if isinstance(img, bytes) else jpeg(img, quality))
    git("add", "-A")
    if git("status", "--porcelain").strip():
        git("commit", "-q", "-m", f"{len(images)} crops for a batch run")
        git("push", "-q")
    urls = {rel: RAW + rel for rel in images}
    first = next(iter(urls.values()))
    for _ in range(30):  # the raw CDN can lag a few seconds behind the push
        if requests.head(first, timeout=30).status_code == 200:
            break
        time.sleep(5)
    else:
        raise RuntimeError(f"not reachable after push: {first}")
    print(f"published {len(images)} crops to {REPO}", flush=True)
    return urls


def clean() -> None:
    """One commit with only the README; the crops leave the repo and its history."""
    git("pull", "-q", "--rebase")
    git("checkout", "-q", "--orphan", "fresh")
    git("rm", "-rq", "--cached", ".")
    git("add", "README.md")
    git("commit", "-q", "-m", "Empty: crops of the last run removed")
    git("branch", "-D", "main")
    git("branch", "-m", "main")
    git("push", "-q", "-f", "-u", "origin", "main")
    for p in sorted(CLONE.iterdir()):
        if p.name not in (".git", "README.md"):
            subprocess.run(["rm", "-rf", str(p)], check=True)
    print(f"{REPO}: emptied (README only)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if sys.argv[1:] == ["clean"]:
        clean()
    else:
        sys.exit(__doc__)
