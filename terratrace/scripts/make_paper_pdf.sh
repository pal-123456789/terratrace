#!/usr/bin/env bash
# Render docs/PAPER.md to the typeset PDF (docs/TerraTrace-paper.pdf).
#
# The paper contains Unicode (sigma, >=, approx, degree). The default LaTeX text font
# (Latin Modern) lacks some of those glyphs, so the build pins a font that covers them
# (DejaVu) — otherwise pandoc emits warnings and the PDF shows blank boxes. The script
# fails loudly when pandoc or xelatex is missing rather than writing a broken PDF.
#
#   bash scripts/make_paper_pdf.sh
#
set -euo pipefail
cd "$(dirname "$0")/.."                       # -> terratrace/

command -v pandoc  >/dev/null || { echo "error: pandoc is required (apt install pandoc)"; exit 1; }
command -v xelatex >/dev/null || { echo "error: xelatex is required (apt install texlive-xetex)"; exit 1; }

SRC=docs/PAPER.md
OUT=docs/TerraTrace-paper.pdf

pandoc "$SRC" -o "$OUT" \
  --pdf-engine=xelatex \
  --toc --toc-depth=2 \
  -V documentclass=article \
  -V geometry:margin=2.2cm \
  -V colorlinks=true -V linkcolor=teal -V urlcolor=teal \
  -V mainfont="DejaVu Serif" -V monofont="DejaVu Sans Mono" \
  -V fontsize=11pt

echo "wrote $OUT ($(wc -c < "$OUT") bytes)"
