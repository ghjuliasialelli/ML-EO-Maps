#!/usr/bin/env python
"""
Build the data behind the "Reference map" page (reference_map.qmd).

Scans every chapter listed in _quarto.yml for citation keys, joins them with the
entries in references.bib, and writes includes/reference_map.json.

Usage:
    conda run -n mleomaps python tools/build_reference_map.py

Re-run whenever references.bib or the chapters' citations change, then re-render.
"""
import json, re
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "includes" / "reference_map.json"

# Short labels for the ring (full titles stay in the tooltip).
SHORT = {
    "introduction.qmd": "Introduction",
    "eo_data_landscape.qmd": "EO data landscape",
    "eo_missions.qmd": "EO missions",
    "accessing_eo_data.qmd": "Accessing EO data",
    "data_selection_preprocessing.qmd": "Data sel. & preproc.",
    "data_selection.qmd": "Data selection",
    "data_preprocessing.qmd": "Data preprocessing",
    "ml_pipeline.qmd": "ML pipeline",
    "ml_ready_dataset.qmd": "ML-ready dataset",
    "model_design_training.qmd": "Model design & training",
    "uncertainty_quantification.qmd": "Uncertainty (overview)",
    "uq_sources.qmd": "Sources of uncertainty",
    "uq_methods.qmd": "UQ methods",
    "uq_calibration.qmd": "Calibration",
    "uq_spatial.qmd": "Spatial uncertainty",
    "uq_operationalizing.qmd": "Operationalizing UQ",
    "map_production.qmd": "Map production",
    "map_generation.qmd": "Map generation",
    "post_processing.qmd": "Post-processing",
    "sharing.qmd": "Sharing",
    "validation.qmd": "Validation (overview)",
    "validation_general.qmd": "Validation misconceptions",
    "validation_design_based.qmd": "Design-based accuracy",
    "validation_beyond.qmd": "Beyond probability sampling",
    "conclusion.qmd": "Conclusion",
    "conclusion_summary.qmd": "Summary",
    "conclusion_forward.qmd": "Looking forward",
    "conclusion_limitations.qmd": "Limitations",
    "appendix_s1_gaps.qmd": "S1 data gaps",
    "appendix_processing_pathways.qmd": "Processing pathways",
    "appendix_s2_artifacts.qmd": "S2 tiling artifacts",
    "appendix_sar_geometry.qmd": "SAR viewing geometry",
    "appendix_sar_rtc.qmd": "SAR calibration & RTC",
    "appendix_sar_ard.qmd": "Analysis-ready SAR",
    "appendix_cloud_masking.qmd": "Cloud masking",
    "appendix_optical_radiometry.qmd": "Optical radiometry",
    "appendix_combining_missions.qmd": "Landsat + Sentinel-2",
}
PART_SHORT = {
    "Front matter": "Intro",
    "Overview of the EO data infrastructure landscape": "EO data",
    "Data selection and preprocessing": "Data",
    "Machine learning dataset construction and model training": "ML",
    "Uncertainty quantification": "Uncertainty",
    "Map production and distribution": "Map production",
    "Validation": "Validation",
    "Conclusion": "Conclusion",
    "Dive Deeper": "Dive Deeper",
}

# --- LaTeX-ish cleanup -------------------------------------------------------
ACCENTS = {
    "'": {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú", "c": "ć", "n": "ń", "s": "ś", "y": "ý", "z": "ź",
          "A": "Á", "E": "É", "I": "Í", "O": "Ó", "U": "Ú", "C": "Ć", "S": "Ś", "Z": "Ź"},
    "`": {"a": "à", "e": "è", "i": "ì", "o": "ò", "u": "ù", "A": "À", "E": "È"},
    '"': {"a": "ä", "e": "ë", "i": "ï", "o": "ö", "u": "ü", "A": "Ä", "O": "Ö", "U": "Ü"},
    "^": {"a": "â", "e": "ê", "i": "î", "o": "ô", "u": "û"},
    "~": {"a": "ã", "n": "ñ", "o": "õ", "N": "Ñ"},
    "c": {"c": "ç", "C": "Ç", "s": "ş"},
    "v": {"c": "č", "s": "š", "z": "ž", "r": "ř", "e": "ě", "C": "Č", "S": "Š", "Z": "Ž"},
    "H": {"o": "ő", "u": "ű"},
}


def delatex(s: str) -> str:
    s = s.replace("\\i", "i")

    def acc(m):
        cmd, ch = m.group(1), m.group(2)
        return ACCENTS.get(cmd, {}).get(ch, ch)

    s = re.sub(r"\\([`'\"^~]|[cvH](?=[\s{]))\s*\{?\s*([A-Za-z])\s*\}?", acc, s)
    s = (s.replace("\\&", "&").replace("\\%", "%").replace("\\_", "_")
          .replace("---", "—").replace("--", "–").replace("&thinsp;", " ")
          .replace("\\ss", "ß").replace("\\o", "ø").replace("\\aa", "å"))
    s = re.sub(r"\\(emph|textit|textbf|mathrm|text)\s*", "", s)
    s = re.sub(r"\$([^$]*)\$", r"\1", s)
    s = s.replace("{", "").replace("}", "").replace("~", " ")
    return re.sub(r"\s+", " ", s).strip()


def parse_bib(text: str) -> dict:
    """Minimal brace-aware BibTeX parser: {key: {field: value}}."""
    entries, i = {}, 0
    while (m := re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,").search(text, i)):
        etype, key = m.group(1).lower(), m.group(2).strip()
        j, depth = m.end(), 1
        while j < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            j += 1
        body, fields = text[m.end():j - 1], {"_type": etype}
        k = 0
        fre = re.compile(r"\s*,?\s*([A-Za-z_\-]+)\s*=\s*")
        while (fm := fre.match(body, k)):
            name, p = fm.group(1).lower(), fm.end()
            if p < len(body) and body[p] == "{":
                d, q = 1, p + 1
                while q < len(body) and d:
                    d += {"{": 1, "}": -1}.get(body[q], 0)
                    q += 1
                val, k = body[p + 1:q - 1], q
            elif p < len(body) and body[p] == '"':
                q = body.index('"', p + 1)
                val, k = body[p + 1:q], q + 1
            else:
                vm = re.match(r"[^,]*", body[p:])
                val, k = vm.group(0), p + vm.end()
            fields[name] = val.strip()
        entries.setdefault(key, fields)  # first definition wins, like citeproc
        i = j
    return entries


def short_authors(a: str) -> str:
    names = [n.strip() for n in re.split(r"\s+and\s+", delatex(a)) if n.strip()]
    if not names:
        return ""
    def last(n):
        return n.split(",")[0].strip() if "," in n else n.split()[-1]
    if names[-1].lower() == "others":
        names = names[:-1] + ["x", "y"]
    if len(names) == 1:
        return last(names[0])
    if len(names) == 2:
        return f"{last(names[0])} & {last(names[1])}"
    return f"{last(names[0])} et al."


def chapter_order():
    """Yield (file, part_title) in book order, read from the book: block of _quarto.yml."""
    mode, part = None, None
    for line in (REPO / "_quarto.yml").read_text(encoding="utf-8").splitlines():
        indent, s = len(line) - len(line.lstrip()), line.strip()
        if indent == 2 and s in ("chapters:", "appendices:"):
            mode = s[:-1]
        elif indent <= 2 and s:
            mode = None
        elif mode and (m := re.match(r"-\s*part:\s*\"?([^\"]+?)\"?$", s)):
            p = m.group(1)
            part = title_of(p) if p.endswith(".qmd") else p
            if p.endswith(".qmd"):
                yield p, part
        elif mode and (m := re.match(r"-\s*(\S+\.qmd)$", s)):
            if mode == "appendices":
                yield m.group(1), "Dive Deeper"
            elif indent > 4 and part:
                yield m.group(1), part
            else:
                yield m.group(1), "Front matter"


def title_of(qmd: str) -> str:
    t = (REPO / qmd).read_text(encoding="utf-8")
    m = re.search(r'^title:\s*"?(.*?)"?\s*$', t, re.M) or re.search(r"^#\s+(.*?)(\s*\{.*\})?\s*$", t, re.M)
    return m.group(1) if m else qmd


def main():

    bib = parse_bib((REPO / "references.bib").read_text(encoding="utf-8"))

    chapters, refs = [], {}
    for f, part in chapter_order():
        text = (REPO / f).read_text(encoding="utf-8")
        text = re.sub(r"^---.*?---", "", text, flags=re.S)
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        keys = []
        for k in re.findall(r"(?<![\w/#])@([A-Za-z0-9][A-Za-z0-9_:\-\.]*[A-Za-z0-9_])", text):
            if k in bib and k not in keys:
                keys.append(k)
        if not keys:
            continue
        cid = f.removesuffix(".qmd")
        chapters.append({
            "id": cid, "title": title_of(f), "short": SHORT.get(f, title_of(f)),
            "part": part, "partShort": PART_SHORT.get(part, part), "href": f"{cid}.html",
        })
        for k in keys:
            if k not in refs:
                e = bib[k]
                year = re.search(r"\d{4}", e.get("year", "") or e.get("date", ""))
                doi = e.get("doi", "").strip()
                how = e.get("howpublished", "")
                how_url = re.search(r"\\url\s*\{([^}]+)\}", how)
                url = f"https://doi.org/{doi}" if doi else (
                    e.get("url", "").strip() or (how_url.group(1) if how_url else ""))
                venue = e.get("journal") or e.get("booktitle") or e.get("publisher") \
                    or e.get("institution") or ("" if how_url else how)
                refs[k] = {
                    "id": k, "title": delatex(e.get("title", k)),
                    "authors": short_authors(e.get("author", "") or e.get("editor", "")),
                    "year": int(year.group(0)) if year else None,
                    "venue": delatex(venue), "type": e["_type"], "url": url, "chapters": [],
                }
            refs[k]["chapters"].append(cid)

    out = {"chapters": chapters, "refs": list(refs.values()),
           "bibEntries": len(bib)}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(chapters)} chapters, {len(refs)} cited references "
          f"({len(bib)} bib entries) -> {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
