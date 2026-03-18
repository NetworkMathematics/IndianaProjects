#!/usr/bin/env python3
"""
finds terms appearing in multiple glossaries, compares
and classifies

python dedup_analysis.py [--input extracted_terms.json] [--output-dir .]
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path


def normalize_term(term: str) -> str:
    """normalize a term for matching across glossaries.
    strips parenthetical qualifiers so 'kernel (algebra)' and
    'kernel (analysis)' collide; intentional for dedup detection."""
    t = term.lower().strip()
    t = re.sub(r'\s*\([^)]*\)\s*', '', t)
    t = re.sub(r'^(the|a|an)\s+', '', t)
    t = re.sub(r'[^\w\s-]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def definition_similarity(def_a: str, def_b: str) -> float:
    """compute similarity between two definitions (0.0 to 1.0)."""
    if not def_a or not def_b:
        return 0.0
    return SequenceMatcher(None, def_a.lower(), def_b.lower()).ratio()


def classify_relationship(entries: list[dict]) -> dict:
    """classify the relationship between multiple definitions of the same term.
    returns relationship type, max pairwise similarity, primary index, notes."""
    non_stubs = [e for e in entries if not e.get("is_stub", False) and e.get("definition", "")]
    stubs = [e for e in entries if e.get("is_stub", False) or not e.get("definition", "")]

    if not non_stubs:
        return {
            "relationship": "all_stubs",
            "max_similarity": 0.0,
            "primary_index": 0,
            "notes": f"all {len(entries)} entries are stubs or empty"
        }

    has_stub_component = bool(non_stubs and stubs)

    # pairwise similarities among non-stubs
    max_sim = 0.0
    for i in range(len(non_stubs)):
        for j in range(i + 1, len(non_stubs)):
            s = definition_similarity(
                non_stubs[i]["definition"],
                non_stubs[j]["definition"]
            )
            max_sim = max(max_sim, s)

    # longest non-stub definition as primary
    primary = max(range(len(entries)), key=lambda i: len(entries[i].get("definition", "")))

    if len(non_stubs) == 1 and stubs:
        return {
            "relationship": "stub_vs_full",
            "max_similarity": 0.0,
            "primary_index": primary,
            "notes": f"1 full definition, {len(stubs)} stub(s)"
        }

    if len(non_stubs) >= 2:
        if max_sim > 0.85:
            rel = "identical"
            notes = f"near-identical (similarity: {max_sim:.2f})"
        elif max_sim > 0.5:
            rel = "overlapping"
            notes = f"substantial overlap (similarity: {max_sim:.2f})"
        else:
            rel = "complementary"
            notes = f"different perspectives (similarity: {max_sim:.2f})"

        if has_stub_component:
            notes += f"; also {len(stubs)} stub(s)"

        return {
            "relationship": rel,
            "max_similarity": max_sim,
            "primary_index": primary,
            "notes": notes
        }

    return {
        "relationship": "unique",
        "max_similarity": 0.0,
        "primary_index": 0,
        "notes": "single entry"
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="extracted_terms.json")
    parser.add_argument("--output-dir", default=".")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    terms = json.load(open(input_path, encoding="utf-8"))
    print(f"loaded {len(terms)} terms from {input_path}")

    # group by normalized term
    groups = defaultdict(list)
    for i, t in enumerate(terms):
        norm = normalize_term(t["term"])
        if norm:
            groups[norm].append(i)

    multi = {}
    single = {}
    for norm, indices in groups.items():
        glossaries = set(terms[i]["source_glossary"] for i in indices)
        if len(glossaries) > 1:
            multi[norm] = indices
        else:
            single[norm] = indices

    print(f"\nunique normalized terms: {len(groups)}")
    print(f"single-glossary terms:  {len(single)}")
    print(f"multi-glossary terms:   {len(multi)}")

    # analyze multi-glossary terms
    cross_terms = []
    rel_counts = defaultdict(int)

    for norm in sorted(multi.keys()):
        indices = multi[norm]
        entries = [terms[i] for i in indices]
        classification = classify_relationship(entries)
        rel_counts[classification["relationship"]] += 1

        record = {
            "normalized_term": norm,
            "display_terms": list(set(e["term"] for e in entries)),
            "glossaries": [e["source_glossary"] for e in entries],
            "math_areas": list(set(e["math_area"] for e in entries)),
            "num_entries": len(entries),
            "classification": classification,
            "entries": [
                {
                    "term": e["term"],
                    "definition": e["definition"],
                    "source_glossary": e["source_glossary"],
                    "math_area": e["math_area"],
                    "extraction_method": e["extraction_method"],
                    "is_stub": e.get("is_stub", False),
                    "definition_length": len(e.get("definition", "")),
                    "wikilinks_count": len(e.get("definition_wikilinks", [])),
                    "term_wikilink": e.get("term_wikilink", ""),
                }
                for e in entries
            ]
        }
        cross_terms.append(record)

    # build report
    report = []
    report.append("cross-glossary deduplication analysis\n")
    report.append(f"total terms in dataset:       {len(terms)}")
    report.append(f"unique normalized terms:      {len(groups)}")
    report.append(f"single-glossary terms:        {len(single)}")
    report.append(f"multi-glossary terms:         {len(multi)}")
    report.append(f"  spanning 2 glossaries:      {sum(1 for r in cross_terms if r['num_entries'] == 2)}")
    report.append(f"  spanning 3+ glossaries:     {sum(1 for r in cross_terms if r['num_entries'] >= 3)}")
    report.append("")
    report.append("relationship classification:")
    for rel, count in sorted(rel_counts.items(), key=lambda x: -x[1]):
        report.append(f"  {rel:20s}  {count:4d}")

    # complementary definitions
    complementary = [r for r in cross_terms
                     if r["classification"]["relationship"] == "complementary"]
    report.append(f"\ncomplementary definitions ({len(complementary)} terms)")
    report.append("genuinely different definitions across glossaries.")

    for r in complementary[:30]:
        report.append("")
        report.append(f"  {r['normalized_term']}")
        report.append(f"  areas: {', '.join(r['math_areas'])}")
        for e in r["entries"]:
            src = e["source_glossary"].replace("Glossary of ", "")
            stub = " [stub]" if e["is_stub"] else ""
            defn = e["definition"][:120] if e["definition"] else "(empty)"
            report.append(f"    [{src}]{stub}")
            report.append(f"      {defn}")

    # near-identical definitions
    identical = [r for r in cross_terms
                 if r["classification"]["relationship"] == "identical"]
    report.append(f"\nnear-identical definitions ({len(identical)} terms)")
    report.append("redundant entries that could be merged.")

    for r in identical[:20]:
        sim = r["classification"]["max_similarity"]
        glossaries = [e["source_glossary"].replace("Glossary of ", "")
                      for e in r["entries"]]
        report.append(f"  {r['normalized_term']:40s}  sim={sim:.2f}  [{', '.join(glossaries)}]")

    # overlapping definitions
    overlapping = [r for r in cross_terms
                   if r["classification"]["relationship"] == "overlapping"]
    report.append(f"\noverlapping definitions ({len(overlapping)} terms)")
    report.append("partial overlap; may capture different aspects.")

    for r in overlapping[:20]:
        sim = r["classification"]["max_similarity"]
        report.append("")
        report.append(f"  {r['normalized_term']}  (sim={sim:.2f})")
        for e in r["entries"]:
            src = e["source_glossary"].replace("Glossary of ", "")
            defn = e["definition"][:100] if e["definition"] else "(empty)"
            report.append(f"    [{src}] {defn}")

    # terms spanning 3+ glossaries
    wide = sorted([r for r in cross_terms if r["num_entries"] >= 3],
                  key=lambda r: -r["num_entries"])
    report.append(f"\nterms spanning 3+ glossaries ({len(wide)} terms)")

    for r in wide[:25]:
        glossaries = [e["source_glossary"].replace("Glossary of ", "")
                      for e in r["entries"]]
        rel = r["classification"]["relationship"]
        report.append(f"  {r['normalized_term']:35s}  {r['num_entries']}x  {rel:15s}  [{', '.join(glossaries)}]")

    report_text = "\n".join(report)
    print(report_text)

    # write cross-glossary terms json
    cross_path = output_dir / "cross_glossary_terms.json"
    with open(cross_path, "w", encoding="utf-8") as f:
        json.dump(cross_terms, f, indent=2, ensure_ascii=False)
    print(f"\nwrote {cross_path} ({len(cross_terms)} multi-glossary terms)")

    # write report
    report_path = output_dir / "cross_glossary_report.txt"
    report_path.write_text(report_text, encoding="utf-8")
    print(f"wrote {report_path}")

    # enriched full dataset with dedup metadata
    for t in terms:
        t["is_cross_glossary"] = False
        t["cross_glossary_group"] = ""
        t["cross_glossary_relationship"] = ""
        t["is_primary_definition"] = True

    for r in cross_terms:
        norm = r["normalized_term"]
        rel = r["classification"]["relationship"]
        primary_idx = r["classification"]["primary_index"]
        indices = multi[norm]

        for rank, idx in enumerate(indices):
            terms[idx]["is_cross_glossary"] = True
            terms[idx]["cross_glossary_group"] = norm
            terms[idx]["cross_glossary_relationship"] = rel
            terms[idx]["is_primary_definition"] = (rank == primary_idx)

    enriched_path = output_dir / "extracted_terms_enriched.json"
    with open(enriched_path, "w", encoding="utf-8") as f:
        json.dump(terms, f, indent=2, ensure_ascii=False)
    print(f"wrote {enriched_path} ({len(terms)} terms with dedup metadata)")


if __name__ == "__main__":
    main()
