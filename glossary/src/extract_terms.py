#!/usr/bin/env python3
"""
phase 2: term and definition extraction from wikipedia math glossaries.

python extract_terms.py [--cache-dir raw_wikitext] [--output-dir .]
"""

import argparse
import csv
import html as html_mod
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


GLOSSARY_META = {
    "Glossary of algebraic geometry": {
        "math_area": "geometry_topology", "scope": "primary",
    },
    "Glossary of algebraic topology": {
        "math_area": "geometry_topology", "scope": "primary",
    },
    "Glossary of areas of mathematics": {
        "math_area": "cross-cutting", "scope": "secondary",
    },
    "Glossary of arithmetic and diophantine geometry": {
        "math_area": "number_theory", "scope": "primary",
    },
    "Glossary of calculus": {
        "math_area": "analysis", "scope": "primary",
    },
    "Glossary of category theory": {
        "math_area": "foundations", "scope": "primary",
    },
    "Glossary of classical algebraic geometry": {
        "math_area": "geometry_topology", "scope": "primary",
    },
    "Glossary of commutative algebra": {
        "math_area": "algebra", "scope": "primary",
    },
    "Glossary of cryptographic keys": {
        "math_area": "applied_cs", "scope": "exclude",
    },
    "Glossary of differential geometry and topology": {
        "math_area": "geometry_topology", "scope": "primary",
    },
    "Glossary of experimental design": {
        "math_area": "applied_statistics", "scope": "exclude",
    },
    "Glossary of field theory": {
        "math_area": "algebra", "scope": "primary",
    },
    "Glossary of functional analysis": {
        "math_area": "analysis", "scope": "primary",
    },
    "Glossary of game theory": {
        "math_area": "discrete_applied", "scope": "primary",
    },
    "Glossary of general topology": {
        "math_area": "geometry_topology", "scope": "primary",
    },
    "Glossary of graph theory": {
        "math_area": "discrete_applied", "scope": "primary",
    },
    "Glossary of group theory": {
        "math_area": "algebra", "scope": "primary",
    },
    "Glossary of invariant theory": {
        "math_area": "algebra", "scope": "primary",
    },
    "Glossary of Lie groups and Lie algebras": {
        "math_area": "algebra", "scope": "primary",
    },
    "Glossary of linear algebra": {
        "math_area": "algebra", "scope": "primary",
    },
    "Glossary of mathematical jargon": {
        "math_area": "cross-cutting", "scope": "secondary",
    },
    "Glossary of mathematical symbols": {
        "math_area": "cross-cutting", "scope": "separate",
    },
    "Glossary of module theory": {
        "math_area": "algebra", "scope": "primary",
    },
    "Glossary of number theory": {
        "math_area": "number_theory", "scope": "primary",
    },
    "Glossary of order theory": {
        "math_area": "discrete_applied", "scope": "primary",
    },
    "Glossary of Principia Mathematica": {
        "math_area": "foundations", "scope": "exclude",
    },
    "Glossary of probability and statistics": {
        "math_area": "probability_statistics", "scope": "primary",
    },
    "Glossary of real and complex analysis": {
        "math_area": "analysis", "scope": "primary",
    },
    "Glossary of representation theory": {
        "math_area": "algebra", "scope": "primary",
    },
    "Glossary of Riemannian and metric geometry": {
        "math_area": "geometry_topology", "scope": "primary",
    },
    "Glossary of ring theory": {
        "math_area": "algebra", "scope": "primary",
    },
    "Glossary of set theory": {
        "math_area": "foundations", "scope": "primary",
    },
    "Glossary of shapes with metaphorical names": {
        "math_area": "geometry_topology", "scope": "exclude",
    },
    "Glossary of symplectic geometry": {
        "math_area": "geometry_topology", "scope": "primary",
    },
    "Glossary of systems theory": {
        "math_area": "applied_cs", "scope": "exclude",
    },
    "Glossary of tensor theory": {
        "math_area": "analysis", "scope": "primary",
    },
}


@dataclass
class ExtractedTerm:
    term: str
    definition: str
    source_glossary: str
    math_area: str
    scope: str
    extraction_method: str
    line_number: int
    definition_wikilinks: list = field(default_factory=list)
    term_wikilink: str = ""
    section: str = ""
    definition_raw: str = ""
    is_stub: bool = False
    has_math: bool = False
    has_disambiguation: bool = False


def _strip_comments(text: str) -> str:
    """strip html comments from text."""
    return re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)


def extract_wikilinks(text: str) -> list[dict]:
    """extract all [[target|display]] links from text."""
    links = []
    for m in re.finditer(r'\[\[([^\]]+)\]\]', text):
        inner = m.group(1)
        if "|" in inner:
            target, display = inner.split("|", 1)
        else:
            target = display = inner
        links.append({"target": target.strip(), "display": display.strip()})
    return links


def clean_wikitext(text: str) -> str:
    """strip wikitext markup from a definition, producing readable plain text."""
    s = text

    # references
    s = re.sub(r'<ref[^>]*/>', '', s)
    s = re.sub(r'<ref[^>]*>.*?</ref>', '', s, flags=re.DOTALL)

    # remove {{quote|...}}, citation templates
    s = re.sub(r'\{\{quote\|.*?\}\}', '', s, flags=re.DOTALL)
    s = re.sub(r'\{\{Harvard citations[^}]*\}\}', '', s)
    s = re.sub(r'\{\{cite[^}]*\}\}', '', s, flags=re.IGNORECASE)

    # navigation templates
    s = re.sub(r'\{\{(?:Main|See also|Further|main|see also|further)\|[^}]*\}\}', '', s)

    # math content templates: keep inner content, strip 1= named param prefix
    s = re.sub(r'\{\{math\|(?:1=)?([^}]*)\}\}', r'\1', s)
    s = re.sub(r'\{\{mvar\|(?:1=)?([^}]*)\}\}', r'\1', s)
    s = re.sub(r'\{\{angbr\|(?:1=)?([^}]*)\}\}', r'\1', s)
    s = re.sub(r'\{\{mset\|(?:1=)?([^}]*)\}\}', lambda m: '{' + m.group(1) + '}', s)

    # glossary internal links
    s = re.sub(r'\{\{gli\|([^|}]+)\|([^}]+)\}\}', r'\2', s)
    s = re.sub(r'\{\{gli\|([^}]+)\}\}', r'\1', s)

    # anchors
    s = re.sub(r'\{\{anchor\|[^}]*\}\}', '', s)

    # remaining templates (iterative for nesting)
    prev = None
    while prev != s:
        prev = s
        s = re.sub(r'\{\{[^{}]*\}\}', '', s)

    # wikilinks
    s = re.sub(r'\[\[([^|\]]+)\|([^\]]+)\]\]', r'\2', s)
    s = re.sub(r'\[\[([^\]]+)\]\]', r'\1', s)

    # external links
    s = re.sub(r'\[https?://\S+\s+([^\]]+)\]', r'\1', s)
    s = re.sub(r'\[https?://\S+\]', '', s)

    # html tags; <math> \to $...$
    s = re.sub(r'<math[^>]*>(.*?)</math>', r'$\1$', s, flags=re.DOTALL)
    s = re.sub(r'<nowiki>(.*?)</nowiki>', r'\1', s, flags=re.DOTALL)
    s = re.sub(r'<br\s*/?>', ' ', s)
    s = re.sub(r'</?(?:sub|sup|small|big|em|strong|span|div|blockquote)[^>]*>', '', s)
    s = _strip_comments(s)

    # bold/italic markup
    s = re.sub(r"'{2,5}", "", s)

    # html entities
    s = html_mod.unescape(s)

    # collapse whitespace, strip leading punctuation artifacts
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'^[;:*#]+\s*', '', s)

    return s


def clean_term(raw_term: str) -> tuple[str, str]:
    """clean a raw term string; returns (clean_term, wikilink_target)."""
    term = raw_term.strip()
    term = re.sub(r'</?nowiki>', '', term)
    term = _strip_comments(term)

    # extract wikilink target if present
    wikilink = ""
    m = re.search(r'\[\[([^|\]]+?)(?:\|([^\]]+))?\]\]', term)
    if m:
        wikilink = m.group(1).strip()
        display = (m.group(2) or m.group(1)).strip()
        term = term[:m.start()] + display + term[m.end():]

    # strip markup
    term = re.sub(r"'{2,5}", "", term)
    term = re.sub(r'\{\{anchor\|[^}]*\}\}', '', term)
    prev = None
    while prev != term:
        prev = term
        term = re.sub(r'\{\{[^{}]*\}\}', '', term)

    # handle template param prefixes
    if term.startswith("1="):
        term = term[2:]
    elif term.startswith("term="):
        term = term[5:]

    term = html_mod.unescape(term)
    term = term.strip().rstrip(".,;:-")
    term = re.sub(r'\s+', ' ', term).strip()

    return term, wikilink


def parse_template(lines: list[str], glossary_title: str) -> list[ExtractedTerm]:
    """parse {{term|...}} / {{defn|...}} pairs."""
    results = []
    current_section = ""

    i = 0
    while i < len(lines):
        line = _strip_comments(lines[i])

        m = re.match(r'^==\s*([^=]+?)\s*==$', line)
        if m:
            current_section = m.group(1).strip()

        # look for {{term|...}}
        term_start = re.search(r'\{\{term\|', line, re.IGNORECASE)
        if not term_start:
            i += 1
            continue

        term_inner = _extract_balanced(line[term_start.end():], '{{', '}}')
        if term_inner is None:
            i += 1
            continue

        # extract term from template params
        term_params = _split_template_params(term_inner.strip())
        term_raw = ""
        for p in term_params:
            p = p.strip()
            if '=' in p:
                key, _, val = p.partition('=')
                key = key.strip()
                if key in ('1', 'term'):
                    term_raw = val.strip()
                    break
            else:
                term_raw = p
                break
        term_end_pos = term_start.end() + len(term_inner) + 2
        term_line = i + 1

        # find the {{defn|...}} that follows
        defn_text = ""
        defn_found = False

        search_start = line[term_end_pos:]
        remaining_lines = [search_start] + [
            _strip_comments(l) for l in lines[i+1:min(i+50, len(lines))]
        ]
        combined = "\n".join(remaining_lines)

        defn_match = re.search(r'\{\{defn\|', combined, re.IGNORECASE)
        if defn_match:
            start = defn_match.end()
            defn_text = _extract_balanced(combined[start:], '{{', '}}')
            if defn_text is not None:
                defn_found = True
                # strip trailing template params
                for _ in range(5):
                    m_trail = re.search(
                        r'\|(?:no|content|multi)\s*=[^|]*$', defn_text
                    )
                    if m_trail:
                        defn_text = defn_text[:m_trail.start()]
                    else:
                        break
                # strip leading template params
                while True:
                    m_lead = re.match(
                        r'(?:no|content|multi)\s*=[^|]*\|', defn_text
                    )
                    if m_lead:
                        defn_text = defn_text[m_lead.end():]
                    else:
                        break
                if defn_text.startswith("1="):
                    defn_text = defn_text[2:]
                elif defn_text.startswith("defn="):
                    defn_text = defn_text[5:]

        if not defn_found:
            after_term = line[term_end_pos:].strip()
            after_term = re.sub(r'\{\{glossary end\}\}', '', after_term,
                                flags=re.IGNORECASE).strip()
            if after_term:
                defn_text = after_term

        term_clean, term_wikilink = clean_term(term_raw)
        if not term_clean:
            i += 1
            continue

        defn_raw = defn_text.strip()
        defn_links = extract_wikilinks(defn_raw)
        defn_clean = clean_wikitext(defn_raw)

        is_stub = (
            not defn_clean
            or defn_clean.lower().startswith("see ")
            or len(defn_clean) < 10
        )
        has_math = bool(re.search(r'<math|\\frac|\\sum|\\int|\$[^$]+\$', defn_raw))
        has_disambig = bool(re.search(r'\(.*\)', term_clean))

        results.append(ExtractedTerm(
            term=term_clean,
            definition=defn_clean,
            source_glossary=glossary_title,
            math_area="",
            scope="",
            extraction_method="template",
            line_number=term_line,
            definition_wikilinks=defn_links,
            term_wikilink=term_wikilink,
            section=current_section,
            definition_raw=defn_raw[:500],
            is_stub=is_stub,
            has_math=has_math,
            has_disambiguation=has_disambig,
        ))

        i += 1

    return results


def parse_bold_bullet(lines: list[str], glossary_title: str) -> list[ExtractedTerm]:
    """parse * '''term''' definition entries."""
    pat = re.compile(r"^\*\s*'{3}(.+?)'{3}\s*(.*)")
    results = []
    current_section = ""

    for i, line in enumerate(lines):
        stripped = _strip_comments(line.strip())

        m_sec = re.match(r'^==\s*([^=]+?)\s*==$', stripped)
        if m_sec:
            current_section = m_sec.group(1).strip()

        m = pat.match(stripped)
        if not m:
            continue

        term_raw = m.group(1).strip()
        defn_raw = m.group(2).strip()
        defn_raw = re.sub(r'^[-:\.]+\s*', '', defn_raw)

        term_clean, term_wikilink = clean_term(term_raw)
        if not term_clean:
            continue

        defn_links = extract_wikilinks(defn_raw)
        defn_clean = clean_wikitext(defn_raw)

        is_stub = (
            not defn_clean
            or defn_clean.lower().startswith("see ")
            or defn_clean.lower().startswith("the same as ")
            or len(defn_clean) < 10
        )
        has_math = bool(re.search(r'<math|\\frac|\\sum|\\int', defn_raw))
        has_disambig = bool(re.search(r'\(.*\)', term_clean))

        results.append(ExtractedTerm(
            term=term_clean,
            definition=defn_clean,
            source_glossary=glossary_title,
            math_area="",
            scope="",
            extraction_method="bold_bullet",
            line_number=i + 1,
            definition_wikilinks=defn_links,
            term_wikilink=term_wikilink,
            section=current_section,
            definition_raw=defn_raw[:500],
            is_stub=is_stub,
            has_math=has_math,
            has_disambiguation=has_disambig,
        ))

    return results


def parse_bare_bold(lines: list[str], glossary_title: str) -> list[ExtractedTerm]:
    """parse '''term''' definition entries (no bullet prefix).
    multi-line: definition may continue on following non-blank,
    non-header, non-bold-start lines."""
    pat = re.compile(r"^'{3}(.+?)'{3}\.?\s*(.*)")
    results = []
    current_section = ""

    i = 0
    while i < len(lines):
        stripped = _strip_comments(lines[i].strip())

        m_sec = re.match(r'^==\s*([^=]+?)\s*==$', stripped)
        if m_sec:
            current_section = m_sec.group(1).strip()

        if not stripped.startswith("'''"):
            i += 1
            continue

        m = pat.match(stripped)
        if not m:
            i += 1
            continue

        term_raw = m.group(1).strip()
        defn_raw = m.group(2).strip()
        defn_raw = re.sub(r'^[-:\.]+\s*', '', defn_raw)

        # collect continuation lines
        j = i + 1
        while j < len(lines):
            next_line = _strip_comments(lines[j].strip())
            if (not next_line
                    or next_line.startswith("==")
                    or next_line.startswith("'''")
                    or next_line.startswith("{{")
                    or next_line.startswith("*")
                    or next_line.startswith(";")):
                break
            defn_raw += " " + next_line.lstrip(":")
            j += 1

        term_clean, term_wikilink = clean_term(term_raw)
        if not term_clean:
            i = j
            continue

        defn_links = extract_wikilinks(defn_raw)
        defn_clean = clean_wikitext(defn_raw)

        is_stub = (
            not defn_clean
            or defn_clean.lower().startswith("see ")
            or defn_clean.lower().startswith("the same as ")
            or len(defn_clean) < 10
        )
        has_math = bool(re.search(r'<math|\\frac|\\sum|\\int', defn_raw))
        has_disambig = bool(re.search(r'\(.*\)', term_clean))

        results.append(ExtractedTerm(
            term=term_clean,
            definition=defn_clean,
            source_glossary=glossary_title,
            math_area="",
            scope="",
            extraction_method="bare_bold",
            line_number=i + 1,
            definition_wikilinks=defn_links,
            term_wikilink=term_wikilink,
            section=current_section,
            definition_raw=defn_raw[:500],
            is_stub=is_stub,
            has_math=has_math,
            has_disambiguation=has_disambig,
        ))

        i = j

    return results


def parse_deflist(lines: list[str], glossary_title: str) -> list[ExtractedTerm]:
    """parse ; term : definition entries.
    handles both single-line and multi-line (: continuation) forms.
    also extracts {{anchor|...}} and {{vanchor|...}} aliases from each entry."""
    anchor_pat = re.compile(r'\{\{(?:anchor|vanchor)\|([^}|]+)(?:\|[^}]*)?\}\}', re.IGNORECASE)
    results = []
    current_section = ""

    i = 0
    while i < len(lines):
        stripped = _strip_comments(lines[i].strip())

        m_sec = re.match(r'^==\s*([^=]+?)\s*==$', stripped)
        if m_sec:
            current_section = m_sec.group(1).strip()

        if not stripped.startswith(";"):
            i += 1
            continue

        # preserve raw line (before comment stripping) for anchor extraction
        raw_full_line = lines[i]

        text = stripped[1:].strip()

        colon_pos = _find_bare_colon(text)
        if colon_pos > 0:
            term_raw = text[:colon_pos].strip()
            defn_raw = text[colon_pos + 1:].strip()
        else:
            term_raw = text
            defn_raw = ""

        # collect continuation lines starting with :
        j = i + 1
        while j < len(lines) and _strip_comments(lines[j].strip()).startswith(":"):
            continuation = _strip_comments(lines[j].strip())[1:].strip()
            defn_raw += " " + continuation
            j += 1

        term_clean, term_wikilink = clean_term(term_raw)
        if not term_clean:
            i = j
            continue

        defn_links = extract_wikilinks(defn_raw)
        defn_clean = clean_wikitext(defn_raw)

        is_stub = (
            not defn_clean
            or defn_clean.lower().startswith("see ")
            or len(defn_clean) < 10
        )
        has_math = bool(re.search(r'<math|\\frac|\\sum|\\int', defn_raw))
        has_disambig = bool(re.search(r'\(.*\)', term_clean))

        results.append(ExtractedTerm(
            term=term_clean,
            definition=defn_clean,
            source_glossary=glossary_title,
            math_area="",
            scope="",
            extraction_method="deflist",
            line_number=i + 1,
            definition_wikilinks=defn_links,
            term_wikilink=term_wikilink,
            section=current_section,
            definition_raw=defn_raw[:500],
            is_stub=is_stub,
            has_math=has_math,
            has_disambiguation=has_disambig,
        ))

        # extract anchor aliases from the raw line
        for m_anchor in anchor_pat.finditer(raw_full_line):
            alias = m_anchor.group(1).strip()
            if not alias or alias.startswith("2="):
                continue
            alias_clean, alias_wikilink = clean_term(alias)
            if not alias_clean or alias_clean.lower() == term_clean.lower():
                continue
            results.append(ExtractedTerm(
                term=alias_clean,
                definition=defn_clean,
                source_glossary=glossary_title,
                math_area="",
                scope="",
                extraction_method="deflist_anchor_alias",
                line_number=i + 1,
                definition_wikilinks=defn_links,
                term_wikilink=alias_wikilink or term_wikilink,
                section=current_section,
                definition_raw=defn_raw[:500],
                is_stub=is_stub,
                has_math=has_math,
                has_disambiguation=bool(re.search(r'\(.*\)', alias_clean)),
            ))

        i = j

    return results


def _extract_balanced(text: str, open_delim: str, close_delim: str) -> Optional[str]:
    """extract text up to balanced closing delimiter."""
    depth = 1
    i = 0
    while i < len(text):
        if text[i:i+len(close_delim)] == close_delim:
            depth -= 1
            if depth == 0:
                return text[:i]
            i += len(close_delim)
        elif text[i:i+len(open_delim)] == open_delim:
            depth += 1
            i += len(open_delim)
        else:
            i += 1
    return text


def _find_bare_colon(text: str) -> int:
    """find first colon not inside [[ ]], {{ }}, or < >."""
    depth_sq = 0
    depth_cur = 0
    depth_angle = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if text[i:i+2] == "[[":
            depth_sq += 1
            i += 2
            continue
        elif text[i:i+2] == "]]":
            depth_sq = max(0, depth_sq - 1)
            i += 2
            continue
        elif text[i:i+2] == "{{":
            depth_cur += 1
            i += 2
            continue
        elif text[i:i+2] == "}}":
            depth_cur = max(0, depth_cur - 1)
            i += 2
            continue
        elif ch == "<":
            depth_angle += 1
        elif ch == ">":
            depth_angle = max(0, depth_angle - 1)
        elif ch == ":" and depth_sq == 0 and depth_cur == 0 and depth_angle == 0:
            return i
        i += 1
    return -1


def _split_template_params(text: str) -> list[str]:
    """split template inner text on bare | (not inside [[ ]], {{ }}, or < >)."""
    params = []
    depth_sq = 0
    depth_cur = 0
    depth_angle = 0
    start = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if text[i:i+2] == "[[":
            depth_sq += 1
            i += 2
            continue
        elif text[i:i+2] == "]]":
            depth_sq = max(0, depth_sq - 1)
            i += 2
            continue
        elif text[i:i+2] == "{{":
            depth_cur += 1
            i += 2
            continue
        elif text[i:i+2] == "}}":
            depth_cur = max(0, depth_cur - 1)
            i += 2
            continue
        elif ch == "<":
            depth_angle += 1
        elif ch == ">":
            depth_angle = max(0, depth_angle - 1)
        elif ch == "|" and depth_sq == 0 and depth_cur == 0 and depth_angle == 0:
            params.append(text[start:i])
            start = i + 1
        i += 1
    params.append(text[start:])
    return params


def choose_parser(glossary_title: str, wikitext: str):
    """decide which parser(s) to run based on glossary identity and content."""
    bold_glossaries = {
        "Glossary of differential geometry and topology",
        "Glossary of order theory",
        "Glossary of cryptographic keys",
        "Glossary of shapes with metaphorical names",
        "Glossary of systems theory",
    }
    bare_bold_glossaries = {
        "Glossary of Riemannian and metric geometry",
    }
    deflist_glossaries = {
        "Glossary of field theory",
        "Glossary of game theory",
        "Glossary of general topology",
        "Glossary of tensor theory",
    }

    # mixed-format glossaries: run multiple parsers, deduplicate downstream
    if glossary_title == "Glossary of mathematical jargon":
        return [("deflist", parse_deflist), ("template", parse_template)]
    if glossary_title == "Glossary of group theory":
        return [("template", parse_template), ("bold_bullet", parse_bold_bullet),
                ("bare_bold", parse_bare_bold)]

    if glossary_title in bold_glossaries:
        return [("bold_bullet", parse_bold_bullet)]
    if glossary_title in bare_bold_glossaries:
        return [("bare_bold", parse_bare_bold)]
    if glossary_title in deflist_glossaries:
        return [("template", parse_template), ("deflist", parse_deflist)]

    return [("template", parse_template)]


def extract_glossary(
    glossary_title: str,
    wikitext: str,
    log: list[str],
) -> list[ExtractedTerm]:
    """extract all terms from a single glossary, deduplicating across parsers."""
    lines = wikitext.split("\n")
    parsers = choose_parser(glossary_title, wikitext)

    meta = GLOSSARY_META.get(glossary_title, {})
    math_area = meta.get("math_area", "unknown")
    scope = meta.get("scope", "unknown")

    all_terms = []
    seen_normalized = set()

    for parser_name, parser_fn in parsers:
        extracted = parser_fn(lines, glossary_title)

        new_count = 0
        dup_count = 0
        for entry in extracted:
            entry.math_area = math_area
            entry.scope = scope

            norm = entry.term.lower().strip()
            if norm in seen_normalized:
                dup_count += 1
                continue
            seen_normalized.add(norm)
            all_terms.append(entry)
            new_count += 1

        log.append(
            f"  {parser_name:15s}: {new_count:4d} new, "
            f"{dup_count:3d} dup  ({glossary_title})"
        )

    return all_terms


def _match_title(filename_title: str, known_titles) -> Optional[str]:
    """fuzzy-match a filename-derived title to known glossary titles."""
    # direct case-insensitive match
    for t in known_titles:
        if t.lower() == filename_title.lower():
            return t
    # normalized punctuation match
    for t in known_titles:
        t_norm = re.sub(r'[^\w\s]', ' ', t.lower())
        f_norm = re.sub(r'[^\w\s]', ' ', filename_title.lower())
        if t_norm == f_norm:
            return t
    # word overlap fallback
    fn_words = set(filename_title.lower().split())
    best = None
    best_score = 0
    for t in known_titles:
        t_words = set(t.lower().split())
        overlap = len(fn_words & t_words) / max(len(fn_words | t_words), 1)
        if overlap > best_score:
            best_score = overlap
            best = t
    if best_score > 0.6:
        return best
    return None


def main():
    parser = argparse.ArgumentParser(
        description="extract terms and definitions from wikipedia math glossaries."
    )
    parser.add_argument(
        "--cache-dir", type=str, default="raw_wikitext",
    )
    parser.add_argument(
        "--output-dir", type=str, default=".",
    )
    parser.add_argument(
        "--include-excluded", action="store_true",
        help="also extract from excluded/separate glossaries",
    )
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    if not cache_dir.exists():
        sys.exit(f"cache directory '{cache_dir}' not found.")

    files = sorted(cache_dir.glob("*.txt"))
    print(f"processing {len(files)} glossaries from {cache_dir}/\n")

    log = []
    all_terms: list[ExtractedTerm] = []

    for f in files:
        title = f.stem.replace("_", " ")

        matched_title = _match_title(title, GLOSSARY_META.keys())
        if not matched_title:
            log.append(f"warning: no metadata match for '{title}', skipping.")
            continue

        meta = GLOSSARY_META[matched_title]
        if meta["scope"] in ("exclude", "separate") and not args.include_excluded:
            log.append(f"  skip (scope={meta['scope']}): {matched_title}")
            continue

        wikitext = f.read_text(encoding="utf-8")
        terms = extract_glossary(matched_title, wikitext, log)
        all_terms.extend(terms)

        stubs = sum(1 for t in terms if t.is_stub)
        with_math = sum(1 for t in terms if t.has_math)
        print(
            f"  {len(terms):4d} terms  ({stubs:3d} stubs, {with_math:3d} math)  "
            f"{matched_title}"
        )

    print(f"\nextraction summary")
    print(f"total terms extracted: {len(all_terms)}")

    by_method = {}
    by_area = {}
    by_scope = {}
    stub_count = 0
    math_count = 0
    empty_def = 0

    for t in all_terms:
        by_method[t.extraction_method] = by_method.get(t.extraction_method, 0) + 1
        by_area[t.math_area] = by_area.get(t.math_area, 0) + 1
        by_scope[t.scope] = by_scope.get(t.scope, 0) + 1
        if t.is_stub:
            stub_count += 1
        if t.has_math:
            math_count += 1
        if not t.definition:
            empty_def += 1

    print(f"\nby extraction method:")
    for m, c in sorted(by_method.items(), key=lambda x: -x[1]):
        print(f"  {m:20s} {c:5d}")

    print(f"\nby math area:")
    for a, c in sorted(by_area.items(), key=lambda x: -x[1]):
        print(f"  {a:25s} {c:5d}")

    print(f"\nquality indicators:")
    print(f"  stubs (short/see-ref):   {stub_count:5d} ({stub_count/len(all_terms)*100:.1f}%)")
    print(f"  contains math notation:  {math_count:5d} ({math_count/len(all_terms)*100:.1f}%)")
    print(f"  empty definition:        {empty_def:5d} ({empty_def/len(all_terms)*100:.1f}%)")

    csv_path = output_dir / "extracted_terms.csv"
    fieldnames = [
        "term", "definition", "source_glossary", "math_area", "scope",
        "extraction_method", "section", "term_wikilink",
        "is_stub", "has_math", "has_disambiguation", "line_number",
        "definition_wikilinks_count",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in all_terms:
            row = {
                "term": t.term,
                "definition": t.definition,
                "source_glossary": t.source_glossary,
                "math_area": t.math_area,
                "scope": t.scope,
                "extraction_method": t.extraction_method,
                "section": t.section,
                "term_wikilink": t.term_wikilink,
                "is_stub": t.is_stub,
                "has_math": t.has_math,
                "has_disambiguation": t.has_disambiguation,
                "line_number": t.line_number,
                "definition_wikilinks_count": len(t.definition_wikilinks),
            }
            writer.writerow(row)
    print(f"\nwrote {csv_path}")

    json_path = output_dir / "extracted_terms.json"
    json_data = [asdict(t) for t in all_terms]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"wrote {json_path}")

    log_path = output_dir / "extraction_log.txt"
    log_path.write_text("\n".join(log), encoding="utf-8")
    print(f"wrote {log_path}")


if __name__ == "__main__":
    main()
