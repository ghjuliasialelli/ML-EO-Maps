#!/usr/bin/env python
"""
Detect which website chapters have diverged from the LaTeX manuscript.

Usage:
    conda run -n mleomaps python tools/sync_diverge.py /path/to/overleaf/main.tex

It splits main.tex at every \\section / \\subsection boundary (in document order),
maps each block to its .qmd file, and prints a similarity score plus the
content words that appear in the manuscript but not the .qmd. Chapters below the
threshold (or where the block count no longer lines up) are flagged for manual sync.

If the manuscript's SECTION STRUCTURE changes (a subsection added/removed/reordered),
the block count will stop matching MAP and the script says so — update MAP below.
"""
import re, sys, difflib
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Ordered list of (qmd filename, number of consecutive section/subsection blocks
# that belong to this file). All are 1 except appendix_processing_pathways, which
# owns its \section plus two \subsections. Order MUST match main.tex.
MAP = [
    ("introduction.qmd", 1),
    ("eo_data_landscape.qmd", 1),
    ("eo_missions.qmd", 1),
    ("accessing_eo_data.qmd", 1),
    ("data_selection_preprocessing.qmd", 1),
    ("data_selection.qmd", 1),
    ("data_preprocessing.qmd", 1),
    ("ml_pipeline.qmd", 1),
    ("ml_ready_dataset.qmd", 1),
    ("model_design_training.qmd", 1),
    ("uncertainty_quantification.qmd", 1),
    ("uq_sources.qmd", 1),
    ("uq_methods.qmd", 1),
    ("uq_calibration.qmd", 1),
    ("uq_spatial.qmd", 1),
    ("uq_operationalizing.qmd", 1),
    ("map_production.qmd", 1),
    ("map_generation.qmd", 1),
    ("post_processing.qmd", 1),
    ("sharing.qmd", 1),
    ("validation.qmd", 1),
    ("validation_general.qmd", 1),
    ("validation_design_based.qmd", 1),
    ("validation_beyond.qmd", 1),
    ("conclusion.qmd", 1),
    ("conclusion_summary.qmd", 1),
    ("conclusion_forward.qmd", 1),
    ("conclusion_limitations.qmd", 1),
    ("acknowledgments.qmd", 1),
    ("appendix_s1_gaps.qmd", 1),
    ("appendix_processing_pathways.qmd", 3),
    ("appendix_sar_rtc.qmd", 1),
    ("appendix_cloud_masking.qmd", 1),
]

# LaTeX/markup tokens to ignore when reporting "content" words.
LATEX = set("""textbf textit emph texttt begin end tabular table figure includegraphics
centering caption label section subsection subsubsection paragraph noindent bigskip
vspace hspace resizebox textwidth linewidth item itemize enumerate cite citep citet
citealt multicolumn multirow toprule midrule bottomrule addlinespace footnotesize
scriptsize small footnote href url texttimes checkmark faglobe faleaf fatree
facrosshairs faasterisk textsuperscript sidewaystable quad qquad sigma beta gamma
theta pi clip trim tikz input include standalone clearpage newpage textsc mathrm
frac cdot times approx leq geq times left right htbp lllllll eiades famappin
arraystretch renewcommand cmidrule arraybackslash allowbreak textdegree setlength
tabcolsep begingroup endgroup bibliographystyle bibliography elsarticle harv document
references urls auto width height linewidth gensymb overview landscape infrastructure""".split())
STOP = set("with that this from into their they which have been than only over each such more most them then when will your also both".split())


def words(t):
    t = t.lower()
    t = re.sub(r'@[a-z0-9_:\-]+', ' ', t)   # citation / xref keys
    return [w for w in re.findall(r'[a-z]{4,}', t) if w not in STOP and w not in LATEX]


def clean_tex(block):
    lines = block.split("\n")
    # drop the leading \section/\subsection header line (its words live in the .qmd
    # YAML title, which we strip from the qmd side too)
    if lines and re.match(r'\s*\\(section|subsection)', lines[0]):
        lines = lines[1:]
    out = ['' if ln.lstrip().startswith('%') else ln.split('%')[0] for ln in lines]
    t = "\n".join(out)
    t = re.sub(r'\\cite[tp]?\{[^}]*\}', ' ', t)
    # strip any remaining \command, with optional [..] and {..} arguments
    for _ in range(3):
        t = re.sub(r'\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^}]*\})?', ' ', t)
    return t


def clean_qmd(t):
    t = re.sub(r'^---.*?---', '', t, flags=re.S)
    return re.sub(r'\[@[^\]]*\]', ' ', t)


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python tools/sync_diverge.py /path/to/overleaf/main.tex")
    tex = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").split("\n")

    # split points: \section, \section*, \subsection (NOT \subsection*, NOT \subsubsection)
    def is_split(ln):
        return bool(re.match(r'\s*\\section\*?\{', ln) or re.match(r'\s*\\subsection\{', ln))
    idx = [i for i, ln in enumerate(tex) if is_split(ln)]
    blocks = [("\n".join(tex[idx[k]:idx[k+1] if k+1 < len(idx) else len(tex)]))
              for k in range(len(idx))]

    expected = sum(n for _, n in MAP)
    if len(blocks) != expected:
        print(f"!! STRUCTURE MISMATCH: found {len(blocks)} section/subsection blocks, "
              f"MAP expects {expected}.\n   The manuscript structure changed — the "
              f"headers below no longer line up with MAP. Fix MAP in this script.\n")
        for b in blocks:
            print("   ", b.split("\n")[0][:90])
        return

    print(f"{'chapter':38} {'sim%':>5}  manuscript-only content words")
    print("-" * 100)
    pos = 0
    for qmd, n in MAP:
        blk = "\n".join(blocks[pos:pos+n]); pos += n
        p = REPO / qmd
        if not p.exists():
            print(f"{qmd:38}  MISSING QMD"); continue
        qw = words(clean_qmd(p.read_text(encoding="utf-8", errors="replace")))
        tw = words(clean_tex(blk))
        sim = difflib.SequenceMatcher(None, qw, tw).ratio() * 100
        cq, ct = Counter(qw), Counter(tw)
        added = sorted(((ct[w]-cq.get(w, 0), w) for w in ct if ct[w] > cq.get(w, 0)), reverse=True)
        # a chapter is worth checking only if the manuscript has real prose words the .qmd lacks
        real = [w for _, w in added if len(w) >= 5]
        flag = "  <-- CHECK" if len(real) >= 3 else ""
        print(f"{qmd:38} {sim:5.1f}  {', '.join(w for _, w in added[:12])}{flag}")


if __name__ == "__main__":
    main()
