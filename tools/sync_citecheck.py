#!/usr/bin/env python
"""
Check that every citation key used in the .qmd chapters resolves in references.bib.

Usage:
    conda run -n mleomaps python tools/sync_citecheck.py

Ignores Quarto cross-references (@fig-, @tbl-, @eq-, @sec-), which are not citations.
Prints any citation key that is used but missing from references.bib. If the manuscript
added new references, copy their BibTeX entries from the Overleaf .bib files into
references.bib and re-run.
"""
import re, glob, os
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

bib = (REPO / "references.bib").read_text(encoding="utf-8", errors="replace")
# handles keys on the same line or the next line after @type{
bibkeys = {k.strip() for k in re.findall(r'@\w+\s*\{\s*([^,\s]+)\s*,', bib)}

used = {}
for f in glob.glob(str(REPO / "*.qmd")):
    t = re.sub(r'^---.*?---', '', Path(f).read_text(encoding="utf-8", errors="replace"), flags=re.S)
    for m in re.findall(r'(?<![\w/#])@([A-Za-z][A-Za-z0-9_:\-]+)', t):
        if re.match(r'(fig|tbl|eq|sec)-', m):
            continue
        used.setdefault(m, set()).add(os.path.basename(f))

missing = {k: v for k, v in used.items() if k not in bibkeys}
print(f"references.bib keys: {len(bibkeys)} | citation keys used: {len(used)}")
if missing:
    print("\n!! MISSING (used but not in references.bib):")
    for k, v in sorted(missing.items()):
        print(f"   @{k}  <- {', '.join(sorted(v))}")
    raise SystemExit(1)
print("All citation keys resolve. OK")
