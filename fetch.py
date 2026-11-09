"""Fetch page images and the MDZ OCR layer of Bochart, Hierozoicon, ed. Rosenmüller (Leipzig 1793-96).

  py -3.13 fetch.py list --vol 2 --from 420 --to 450      # canvas, label, image id
  py -3.13 fetch.py preview --vol 2 424 445                # 1000px previews to pick pages
  py -3.13 fetch.py sample                                 # full-res pilot pages + hOCR + data/raw/manifest.json

Source: Munich, BSB / MDZ, IIIF Presentation 2.0. One manifest per volume.
Canvas = 1-based position in the manifest. In vol. 2, printed page = canvas - 16 (MDZ labels
"415 (0431)" = page 415, canvas 431; checked against the scans for the pilot pages).
Page key: "v2-0409" (volume, printed page) or "v2-scan0005" for an unnumbered page.
All responses are cached; requests are sequential with a delay. Scans are not stored in git.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")

VOLUMES = {1: "bsb10353453", 2: "bsb10353454", 3: "bsb10353455"}
MANIFEST = "https://api.digitale-sammlungen.de/iiif/presentation/v2/{id}/manifest"
DELAY = 2.0
DATA = Path(__file__).parent / "data"

# (volume, canvas, why). Pilot: Book III ch. 33, the shafan: vol. 2 p. 409 (after 3 lines of
# ch. 32) to the top of p. 429 (then ch. 34). The page before is fetched too.
SAMPLE = [
    (2, 424, "before"),
    *[(2, c, "shafan") for c in range(425, 446)],
    # Book III ch. 35, the choled (mole, not weasel): p. 435 (after ch. 34) to p. 453 (CAP. XXXVI.
    # at its foot); pp. 434 and 454 for the joins. Found in the MDZ hOCR, 08-Nov-2026.
    *[(2, c, "choled") for c in range(450, 471)],
    # Tranche 09-Nov-2026: ch. 34 (vulgar mouse, pp. 429-435; pp. 430-433 new), ch. 36 (kippod,
    # pp. 454-462) and Book IV (oviparous quadrupeds, chs. 1-8, pp. 463-523); p. 524 (Pars II, Book I
    # of the birds) for the join. Chapter heads found in the MDZ hOCR (logs/find_caps.py).
    *[(2, c, "achbar") for c in range(446, 450)],
    *[(2, c, "book4") for c in range(471, 541)],
]

session = requests.Session()
session.headers["User-Agent"] = "bochart-hierozoicon OCR research (personal research; sequential, cached)"
_last = 0.0


def get(url: str) -> requests.Response:
    global _last
    wait = DELAY - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    r = session.get(url, timeout=120)
    _last = time.monotonic()
    r.raise_for_status()
    return r


def manifest(vol: int) -> dict:
    path = DATA / "cache" / "manifests" / f"{VOLUMES[vol]}.json"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(get(MANIFEST.format(id=VOLUMES[vol])).content)
    return json.loads(path.read_text(encoding="utf-8"))


def canvases(vol: int) -> list[dict]:
    out = []
    for i, c in enumerate(manifest(vol)["sequences"][0]["canvases"], start=1):
        res = c["images"][0]["resource"]
        m = re.match(r"^(\S+) \((\d+)\)$", c["label"])  # "415 (0431)"; unnumbered pages: "[5] (0005)"?
        page = m.group(1) if m and m.group(1).isdigit() else None
        out.append({
            "volume": vol,
            "canvas": i,
            "label": c["label"],
            "printed_page": page,
            "image_service": res["service"]["@id"],
            "hocr": (c.get("seeAlso") or {}).get("@id"),
            "width": c["width"],
            "height": c["height"],
        })
    return out


def page_key(c: dict) -> str:
    if c["printed_page"]:
        return f"v{c['volume']}-{int(c['printed_page']):04d}"
    return f"v{c['volume']}-scan{c['canvas']:04d}"


def download(url: str, path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    tmp.write_bytes(get(url).content)
    tmp.replace(path)
    print(f"  saved {path.relative_to(DATA.parent)}", flush=True)


def cmd_list(a):
    for c in canvases(a.vol):
        if a.start <= c["canvas"] <= a.to:
            print(f"{c['canvas']:4d}  {c['label']:>12}  {c['image_service'].rsplit('/', 1)[-1]}")


def cmd_preview(a):
    cs = canvases(a.vol)
    for i in a.canvas:
        c = cs[i - 1]
        download(f"{c['image_service']}/full/1000,/0/default.jpg",
                 DATA / "preview" / f"{page_key(c)}.jpg")


def cmd_sample(a):
    records = []
    for vol, canvas, why in SAMPLE:
        c = canvases(vol)[canvas - 1]
        key = page_key(c)
        url = f"{c['image_service']}/full/full/0/default.jpg"
        print(f"vol. {vol} canvas {canvas} = p. {c['label']} ({why})", flush=True)
        download(url, DATA / "raw" / f"{key}.jpg")
        if c["hocr"]:
            download(c["hocr"], DATA / "mdz_hocr" / f"{key}.hocr")
        records.append({**c, "key": key, "kind": why, "source_url": url, "file": f"raw/{key}.jpg"})
    out = {
        "work": "Bochart, Hierozoicon, ed. E. F. C. Rosenmüller (Leipzig: Breitkopf, 1793-96)",
        "holder": "Bayerische Staatsbibliothek München (MDZ)",
        "licence": manifest(2).get("license"),
        "volumes": VOLUMES,
        "pages": records,
    }
    (DATA / "raw" / "manifest.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(records)} pages; manifest at data/raw/manifest.json")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(required=True)
    s = sub.add_parser("list")
    s.add_argument("--vol", type=int, default=2)
    s.add_argument("--from", dest="start", type=int, default=1)
    s.add_argument("--to", type=int, default=10**6)
    s.set_defaults(func=cmd_list)
    s = sub.add_parser("preview")
    s.add_argument("--vol", type=int, default=2)
    s.add_argument("canvas", type=int, nargs="+")
    s.set_defaults(func=cmd_preview)
    s = sub.add_parser("sample")
    s.set_defaults(func=cmd_sample)
    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
