#!/usr/bin/env python3
"""
fetches glossaries from category:glossaries_of_mathematics

python glossary_inventory.py [--no-cache] [--delay seconds]
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    sys.exit("install requests: pip install requests")

API_URL = "https://en.wikipedia.org/w/api.php"
CATEGORY = "Category:Glossaries of mathematics"
CACHE_DIR = Path("raw_wikitext")
DEFAULT_DELAY = 1.0

# hand-curated metadata not derivable from wikitext alone.
MANUAL_ANNOTATIONS = {
    "Glossary of algebraic geometry": {
        "type": "concept", "math_area": "geometry_topology",
        "scope_priority": "primary",
        "notes": "scheme-theoretic; cross-refs commutative algebra and classical ag glossaries",
    },
    "Glossary of algebraic topology": {
        "type": "concept", "math_area": "geometry_topology",
        "scope_priority": "primary",
        "notes": "includes some homological algebra terms (no separate glossary exists)",
    },
    "Glossary of areas of mathematics": {
        "type": "meta", "math_area": "cross-cutting",
        "scope_priority": "secondary",
        "notes": "defines subfields, not concepts",
    },
    "Glossary of arithmetic and diophantine geometry": {
        "type": "concept", "math_area": "number_theory",
        "scope_priority": "primary",
        "notes": "number-theoretic algebraic geometry",
    },
    "Glossary of calculus": {
        "type": "concept", "math_area": "analysis",
        "scope_priority": "primary",
        "notes": "elementary level; long encyclopedic definitions",
    },
    "Glossary of category theory": {
        "type": "concept", "math_area": "foundations",
        "scope_priority": "primary",
        "notes": "dense; cross-references algebraic topology glossary",
    },
    "Glossary of classical algebraic geometry": {
        "type": "concept", "math_area": "geometry_topology",
        "scope_priority": "primary",
        "notes": "pre-scheme (19th-century) terminology; may contain archaic terms",
    },
    "Glossary of commutative algebra": {
        "type": "concept", "math_area": "algebra",
        "scope_priority": "primary",
        "notes": "cross-referenced by algebraic geometry glossary",
    },
    "Glossary of cryptographic keys": {
        "type": "peripheral", "math_area": "applied_cs",
        "scope_priority": "exclude",
        "notes": "applied cs, not mathematics; defines key types",
    },
    "Glossary of differential geometry and topology": {
        "type": "concept", "math_area": "geometry_topology",
        "scope_priority": "primary",
        "notes": "covers both differential geometry and differential topology",
    },
    "Glossary of experimental design": {
        "type": "peripheral", "math_area": "applied_statistics",
        "scope_priority": "exclude",
        "notes": "statistical methodology, not mathematical concepts",
    },
    "Glossary of field theory": {
        "type": "concept", "math_area": "algebra",
        "scope_priority": "primary",
        "notes": "algebraic field theory (galois theory, etc.)",
    },
    "Glossary of functional analysis": {
        "type": "concept", "math_area": "analysis",
        "scope_priority": "primary",
        "notes": "banach spaces, operator theory, etc.",
    },
    "Glossary of game theory": {
        "type": "concept", "math_area": "discrete_applied",
        "scope_priority": "primary",
        "notes": "some terms are economic rather than mathematical",
    },
    "Glossary of general topology": {
        "type": "concept", "math_area": "geometry_topology",
        "scope_priority": "primary",
        "notes": "foundational for other topology glossaries; clean definition-list format",
    },
    "Glossary of graph theory": {
        "type": "concept", "math_area": "discrete_applied",
        "scope_priority": "primary",
        "notes": "discrete math; likely large term count",
    },
    "Glossary of group theory": {
        "type": "concept", "math_area": "algebra",
        "scope_priority": "primary",
        "notes": "core algebra",
    },
    "Glossary of invariant theory": {
        "type": "concept", "math_area": "algebra",
        "scope_priority": "primary",
        "notes": "classical algebra; likely small",
    },
    "Glossary of Lie groups and Lie algebras": {
        "type": "concept", "math_area": "algebra",
        "scope_priority": "primary",
        "notes": "bridges algebra and differential geometry",
    },
    "Glossary of linear algebra": {
        "type": "concept", "math_area": "algebra",
        "scope_priority": "primary",
        "notes": "elementary; expected overlap with module theory",
    },
    "Glossary of mathematical jargon": {
        "type": "meta", "math_area": "cross-cutting",
        "scope_priority": "secondary",
        "notes": "informal usage conventions (canonical, pathological, wlog); not formal defs",
    },
    "Glossary of mathematical symbols": {
        "type": "meta", "math_area": "cross-cutting",
        "scope_priority": "separate",
        "notes": "notation, not concepts; completely different structure; needs own pipeline",
    },
    "Glossary of module theory": {
        "type": "concept", "math_area": "algebra",
        "scope_priority": "primary",
        "notes": "generalizes linear algebra",
    },
    "Glossary of number theory": {
        "type": "concept", "math_area": "number_theory",
        "scope_priority": "primary",
        "notes": "core number theory",
    },
    "Glossary of order theory": {
        "type": "concept", "math_area": "discrete_applied",
        "scope_priority": "primary",
        "notes": "lattices, posets, etc.",
    },
    "Glossary of Principia Mathematica": {
        "type": "peripheral", "math_area": "foundations",
        "scope_priority": "exclude",
        "notes": "russell-whitehead notation; historical interest only",
    },
    "Glossary of probability and statistics": {
        "type": "concept", "math_area": "probability_statistics",
        "scope_priority": "primary",
        "notes": "mixed levels; some terms are methodological",
    },
    "Glossary of real and complex analysis": {
        "type": "concept", "math_area": "analysis",
        "scope_priority": "primary",
        "notes": "core analysis",
    },
    "Glossary of representation theory": {
        "type": "concept", "math_area": "algebra",
        "scope_priority": "primary",
        "notes": "bridges algebra and analysis",
    },
    "Glossary of Riemannian and metric geometry": {
        "type": "concept", "math_area": "geometry_topology",
        "scope_priority": "primary",
        "notes": "curvature, geodesics, etc.",
    },
    "Glossary of ring theory": {
        "type": "concept", "math_area": "algebra",
        "scope_priority": "primary",
        "notes": "core algebra; expected overlap with commutative algebra",
    },
    "Glossary of set theory": {
        "type": "concept", "math_area": "foundations",
        "scope_priority": "primary",
        "notes": "foundational; terms used across all subfields",
    },
    "Glossary of shapes with metaphorical names": {
        "type": "peripheral", "math_area": "geometry_topology",
        "scope_priority": "exclude",
        "notes": "novelty catalog (monkey saddle, dunce cap, etc.)",
    },
    "Glossary of symplectic geometry": {
        "type": "concept", "math_area": "geometry_topology",
        "scope_priority": "primary",
        "notes": "bridges geometry and physics",
    },
    "Glossary of systems theory": {
        "type": "peripheral", "math_area": "applied_cs",
        "scope_priority": "exclude",
        "notes": "interdisciplinary (control theory, cybernetics); not core math",
    },
    "Glossary of tensor theory": {
        "type": "concept", "math_area": "analysis",
        "scope_priority": "primary",
        "notes": "multilinear algebra and differential geometry",
    },
}


SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "mathglossaryinventory/1.0 (academic research; "
                  "https://en.wikipedia.org/wiki/Category:Glossaries_of_mathematics) "
                  "python-requests/" + requests.__version__,
})


def api_get(params: dict) -> dict:
    """make a get request to the mediawiki api."""
    params.setdefault("format", "json")
    resp = SESSION.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_category_members(category: str) -> list[dict]:
    """return all pages in a category, handling continuation."""
    members = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category,
        "cmlimit": "50",
        "cmtype": "page",
    }
    while True:
        data = api_get(params)
        members.extend(data["query"]["categorymembers"])
        if "continue" not in data:
            break
        params["cmcontinue"] = data["continue"]["cmcontinue"]
    return members


def get_wikitext(title: str, cache_dir: Path, use_cache: bool = True) -> str:
    """fetch raw wikitext for a page; caches to disk."""
    safe_name = re.sub(r'[^\w\s-]', '_', title) + ".txt"
    cache_path = cache_dir / safe_name
    if use_cache and cache_path.exists():
        return cache_path.read_text(encoding="utf-8")

    data = api_get({
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
    })
    pages = data["query"]["pages"]
    page = next(iter(pages.values()))
    wikitext = page["revisions"][0]["slots"]["main"]["*"]

    cache_dir.mkdir(exist_ok=True)
    cache_path.write_text(wikitext, encoding="utf-8")
    return wikitext


def get_page_size(title: str) -> Optional[int]:
    """return page size in bytes via api."""
    data = api_get({
        "action": "query",
        "titles": title,
        "prop": "info",
    })
    pages = data["query"]["pages"]
    page = next(iter(pages.values()))
    return page.get("length")


def _find_bare_colon(text: str) -> int:
    """find first colon not inside [[ ]] or {{ }}."""
    depth_sq = 0
    depth_cur = 0
    for i, ch in enumerate(text):
        if text[i:i+2] == "[[":
            depth_sq += 1
        elif text[i:i+2] == "]]":
            depth_sq = max(0, depth_sq - 1)
        elif text[i:i+2] == "{{":
            depth_cur += 1
        elif text[i:i+2] == "}}":
            depth_cur = max(0, depth_cur - 1)
        elif ch == ":" and depth_sq == 0 and depth_cur == 0:
            return i
    return -1


def _clean_wikilinks(text: str) -> str:
    """[[target|display]] to display; [[target]] to target."""
    text = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', text)
    text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)
    return text


def _strip_line(line: str) -> str:
    """strip html comments from a line."""
    return re.sub(r'<!--.*?-->', '', line)


def _normalize_term(term: str) -> str:
    """normalize a term for deduplication."""
    t = term.lower().strip()
    t = t.strip(".,;:!?-*#")
    t = re.sub(r'\s+', ' ', t)
    return t


def extract_template_terms(lines: list[str]) -> list[str]:
    """extract terms from {{term|...}} or {{anchor|...}} templates."""
    pat = re.compile(r'\{\{(?:term|anchor)\|([^}]+)\}\}', re.IGNORECASE)
    results = []
    for line in lines:
        line = _strip_line(line)
        for m in pat.finditer(line):
            raw = m.group(1)
            term = raw.split("|")[0].strip()
            if term.startswith("1="):
                term = term[2:]
            term = term.strip()
            if term:
                results.append(term)
    return results


def extract_deflist_terms(lines: list[str]) -> list[str]:
    """extract terms from ; term : definition markup."""
    results = []
    for line in lines:
        if not line.startswith(";"):
            continue
        text = _strip_line(line[1:].strip())
        text = re.sub(r"'{2,3}", "", text)
        text = re.sub(r'\{\{anchor\|[^}]*\}\}', '', text)
        colon_pos = _find_bare_colon(text)
        if colon_pos > 0:
            term = text[:colon_pos].strip()
        else:
            term = text.strip()
        term = _clean_wikilinks(term)
        term = term.strip().rstrip(".")
        if term and len(term) < 200:
            results.append(term)
    return results


def extract_bold_terms(lines: list[str]) -> list[str]:
    """extract terms from '''bold''' at start of line/bullet."""
    pat = re.compile(r"^(?:[*]\s*)?'{3}(.+?)'{3}")
    results = []
    for line in lines:
        stripped = _strip_line(line.strip())
        if stripped.startswith(";") or stripped.startswith("|"):
            continue
        m = pat.match(stripped)
        if m:
            term = m.group(1).strip()
            term = _clean_wikilinks(term)
            term = term.strip().rstrip(",").rstrip(".")
            if term and len(term) < 200:
                results.append(term)
    return results


def extract_table_terms(lines: list[str]) -> list[str]:
    """extract terms from table rows: | '''term''' || definition."""
    pat = re.compile(r'^\|\s*(?:\'{3})?([^|\']+?)(?:\'{3})?\s*\|\|')
    results = []
    for line in lines:
        cleaned = _strip_line(line.strip())
        m = pat.match(cleaned)
        if m:
            term = m.group(1).strip()
            term = _clean_wikilinks(term)
            if term and len(term) < 200:
                results.append(term)
    return results


def detect_format(wikitext: str) -> dict:
    """analyse wikitext to detect structural formats and estimate term count."""
    lines = wikitext.split("\n")

    # extract terms via all four methods (with full cleanup)
    term_template_names = extract_template_terms(lines)
    deflist_term_names = extract_deflist_terms(lines)
    bold_term_names = extract_bold_terms(lines)
    table_term_names = extract_table_terms(lines)

    # detect glossary template markers and section headers (format metadata)
    glossary_start = re.compile(
        r'\{\{(?:glossary|glossary begin|glossary start)', re.IGNORECASE
    )
    defn_template = re.compile(r'\{\{defn\|', re.IGNORECASE)
    section_header = re.compile(r'^(={2,4})\s*(.+?)\s*\1\s*$')

    has_glossary_template = False
    defn_count = 0
    section_counts = {"l2": 0, "l3": 0, "l4": 0}

    for line in lines:
        line = _strip_line(line)
        if glossary_start.search(line):
            has_glossary_template = True
        if defn_template.search(line):
            defn_count += 1
        m = section_header.match(line)
        if m:
            level = len(m.group(1))
            if level == 2:
                section_counts["l2"] += 1
            elif level == 3:
                section_counts["l3"] += 1
            elif level == 4:
                section_counts["l4"] += 1

    counts = {
        "term_templates": len(term_template_names),
        "defn_templates": defn_count,
        "deflist_terms": len(deflist_term_names),
        "bold_terms": len(bold_term_names),
        "table_terms": len(table_term_names),
        "section_headers_l2": section_counts["l2"],
        "section_headers_l3": section_counts["l3"],
        "section_headers_l4": section_counts["l4"],
    }

    # determine dominant format(s)
    format_types = []
    if counts["term_templates"] > 5:
        format_types.append("glossary_template")
    if counts["deflist_terms"] > 5:
        format_types.append("definition_list")
    if counts["bold_terms"] > 5:
        format_types.append("bold_term_paragraphs")
    if counts["table_terms"] > 5:
        format_types.append("table")

    # fallback: pick whichever pattern has the max count
    if not format_types:
        max_count = max(
            counts["term_templates"],
            counts["deflist_terms"],
            counts["bold_terms"],
            counts["table_terms"],
        )
        if max_count > 0:
            if counts["term_templates"] == max_count:
                format_types.append("glossary_template")
            if counts["deflist_terms"] == max_count:
                format_types.append("definition_list")
            if counts["bold_terms"] == max_count:
                format_types.append("bold_term_paragraphs")
            if counts["table_terms"] == max_count:
                format_types.append("table")

    if not format_types:
        format_types.append("unknown")

    # deduplicated union across all extraction methods
    all_terms = set()
    for name_list in [term_template_names, deflist_term_names,
                      bold_term_names, table_term_names]:
        for t in name_list:
            n = _normalize_term(t)
            if n:
                all_terms.add(n)

    estimated_terms = len(all_terms)

    return {
        "format_types": format_types,
        "estimated_terms": estimated_terms,
        "has_glossary_template": has_glossary_template,
        "has_definition_list": counts["deflist_terms"] > 0,
        "has_bold_term_paragraphs": counts["bold_terms"] > 0,
        "has_table_entries": counts["table_terms"] > 0,
        "section_count_l2": counts["section_headers_l2"],
        "section_count_l3": counts["section_headers_l3"],
        "section_count_l4": counts["section_headers_l4"],
        "raw_counts": counts,
        "sample_terms_template": term_template_names[:5],
        "sample_terms_bold": bold_term_names[:5],
        "sample_terms_deflist": deflist_term_names[:5],
    }


def count_wikilinks(wikitext: str) -> int:
    """count internal wikilinks [[...]] in the text."""
    return len(re.findall(r'\[\[([^\]|]+)', wikitext))


def page_size_kb(wikitext: str) -> float:
    return len(wikitext.encode("utf-8")) / 1024


def main():
    parser = argparse.ArgumentParser(
        description="inventory wikipedia's mathematics glossaries."
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="re-fetch wikitext even if cached locally",
    )
    parser.add_argument(
        "--delay", type=float, default=DEFAULT_DELAY,
        help=f"seconds between api requests (default: {DEFAULT_DELAY})",
    )
    parser.add_argument(
        "--output-dir", type=str, default=".",
        help="directory for output files (default: current directory)",
    )
    args = parser.parse_args()
    use_cache = not args.no_cache
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    print(f"fetching category members from {CATEGORY} ...")
    members = get_category_members(CATEGORY)
    print(f"  found {len(members)} glossaries.\n")

    if len(members) != 36:
        print(f"  warning: expected 36, got {len(members)}. "
              f"category may have changed.\n")

    results = []

    for i, member in enumerate(members):
        title = member["title"]
        pageid = member["pageid"]
        print(f"[{i+1}/{len(members)}] {title}")

        wikitext = get_wikitext(title, CACHE_DIR, use_cache=use_cache)
        time.sleep(args.delay)

        fmt = detect_format(wikitext)
        n_wikilinks = count_wikilinks(wikitext)
        size_kb = page_size_kb(wikitext)

        annotation = MANUAL_ANNOTATIONS.get(title, {})
        url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"

        row = {
            "number": i + 1,
            "title": title,
            "pageid": pageid,
            "url": url,
            "size_kb": round(size_kb, 1),
            "wikilinks": n_wikilinks,
            "format_types": "; ".join(fmt["format_types"]),
            "estimated_terms": fmt["estimated_terms"],
            "has_glossary_template": fmt["has_glossary_template"],
            "has_definition_list": fmt["has_definition_list"],
            "has_bold_term_paragraphs": fmt["has_bold_term_paragraphs"],
            "has_table_entries": fmt["has_table_entries"],
            "section_count_l2": fmt["section_count_l2"],
            "section_count_l3": fmt["section_count_l3"],
            "section_count_l4": fmt["section_count_l4"],
            "sample_terms": "; ".join(
                fmt["sample_terms_template"]
                or fmt["sample_terms_deflist"]
                or fmt["sample_terms_bold"]
            ),
            "type": annotation.get("type", ""),
            "math_area": annotation.get("math_area", ""),
            "scope_priority": annotation.get("scope_priority", ""),
            "notes": annotation.get("notes", ""),
        }
        results.append(row)

        print(f"  {size_kb:.0f} kb | \\sim{fmt['estimated_terms']} terms | "
              f"format: {', '.join(fmt['format_types'])} | "
              f"scope: {annotation.get('scope_priority', '???')}")

    csv_path = output_dir / "glossary_inventory.csv"
    fieldnames = list(results[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"\nwrote {csv_path}")

    json_path = output_dir / "glossary_inventory.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"wrote {json_path}")

    print("\nsummary")

    total_terms = sum(r["estimated_terms"] for r in results)
    primary = [r for r in results if r["scope_priority"] == "primary"]
    primary_terms = sum(r["estimated_terms"] for r in primary)

    print(f"total glossaries:     {len(results)}")
    print(f"primary (in scope):   {len(primary)}")
    print(f"estimated total terms (all): {total_terms}")
    print(f"estimated total terms (primary only): {primary_terms}")

    print("\nformat distribution:")
    fmt_counts = {}
    for r in results:
        for fmt in r["format_types"].split("; "):
            fmt_counts[fmt] = fmt_counts.get(fmt, 0) + 1
    for fmt, count in sorted(fmt_counts.items(), key=lambda x: -x[1]):
        print(f"  {fmt}: {count}")

    print("\ntop 10 by estimated term count:")
    for r in sorted(results, key=lambda x: -x["estimated_terms"])[:10]:
        print(f"  {r['estimated_terms']:4d}  {r['title']}")

    print("\nsmallest 5 by estimated term count:")
    for r in sorted(results, key=lambda x: x["estimated_terms"])[:5]:
        print(f"  {r['estimated_terms']:4d}  {r['title']}")

    print(f"\nwikitext cached in: {CACHE_DIR.resolve()}/")
    print(f"edit manual_annotations in the script to adjust categorizations.")


if __name__ == "__main__":
    main()
