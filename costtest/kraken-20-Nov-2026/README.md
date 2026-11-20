# Kraken PP-OCRv6 on the gold pages (20-Nov-2026)

Can Kraken (free, local) be a first OCR or an extra reader for the Hierozoicon? Test on the three gold pages
(`data/gold/v2-0410`, `v2-0422`, `v2-0428`, the `.scan.jpg` files).

- Kraken 7.1.1 in `Claude\syriac-ocr\.venv` (see [SYRIAC.md](../../SYRIAC.md)); set `PYTHONIOENCODING=utf-8`.
- Model: PP-OCRv6 medium, multilingual (lat, grc, heb, ara and others), Benjamin Kiessling, Inria,
  zenodo 10.5281/zenodo.21788410, Apache-2.0; in the htrmopo cache `1980fa54-b49e-5256-95b6-928290bc48f8/medium.safetensors`.
- Command: `kraken -i v2-0410.scan.jpg out.txt segment -bl ocr --no-reorder -m medium.safetensors`.
  About 3 to 4 minutes a page on CPU (3 pages in parallel took 3 min 47 s). Cost 0.
- Output: the `v2-NNNN.kraken.txt` files here.

## Results (words compared in order with the gold text, per script)

| Script | p. 410 | p. 422 | p. 428 |
|---|---|---|---|
| Latin (ſ→s, case ignored) | 95% of 360 words | 82% of 229 (italic) | 94% of 313 |
| Greek | 9 words, 22% exact | – | 54 words, 78% exact, 94% character similarity |
| Arabic block (own lines) | – | about 77% of 120 words (each word reversed: output is visual order; ی/ي, ک/ك normalised) | – |
| Hebrew inside Latin lines | 0 of 57 | – | 0 of 5 |
| Arabic / Syriac inside Latin lines | – | – | 0 of 9 / 0 of 4 |

The Hebrew, Arabic and Syriac words inside a Latin line are mostly **left out**: the line reads
`Hebraice  ſaphan per Sin` where the print has שפן. Lines that are wholly Arabic are read.
Greek errors are small (ράμφεε for ῥάμφει, Iρυλλίων for Γρυλλίων). It keeps the long ſ and the line-end ¬.

## Conclusion

- Not a first pass: every line with an RTL word would need the LLM again.
- Useful as a **free extra reader** for Latin and Greek (catches the models' "corrections toward the
  expected word"), and for Arabic blocks (with the line reversed). Syriac blocks: Qoruyo, see SYRIAC.md.
- Not tested: Ethiopic, Samaritan, the vol. 3 print, and how far Kraken disagrees with the Opus OCR on pages
  where Opus is wrong (the real measure of a second reader).
