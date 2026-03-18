#!/usr/bin/env python3
"""merge preamble_definitions.json into extracted_terms.json.

NOTE: preamble_definitions.json is hand-curated list of term definitions
that appear in glossary preambles (before the glossary body).
this merges them into the main extracted terms, deduplicating
against terms already present.

usage:
  python merge_preambles.py [--preambles preamble_definitions.json]
                            [--terms extracted_terms.json]
                            [--output extracted_terms.json]
"""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preambles", default="preamble_definitions.json")
    parser.add_argument("--terms", default="extracted_terms.json")
    parser.add_argument("--output", default="extracted_terms.json",
                        help="output path (default: overwrite input)")
    args = parser.parse_args()

    preambles = json.load(open(args.preambles, encoding="utf-8"))
    terms = json.load(open(args.terms, encoding="utf-8"))
    print(f"existing terms: {len(terms)}")
    print(f"preamble candidates: {len(preambles)}")

    # build dedup index: (glossary, normalized_term)
    existing = set()
    for t in terms:
        key = (t["source_glossary"].lower(), t["term"].lower().strip())
        existing.add(key)

    added = []
    skipped = []
    for p in preambles:
        key = (p["source_glossary"].lower(), p["term"].lower().strip())
        if key in existing:
            skipped.append(p["term"])
            continue

        # build a record matching extract_terms.py output schema
        record = {
            "term": p["term"],
            "term_wikilink": "",
            "definition": p["definition"],
            "definition_raw": p["definition"],
            "definition_wikilinks": p.get("definition_wikilinks", []),
            "source_glossary": p["source_glossary"],
            "math_area": p.get("math_area", "unknown"),
            "scope": "primary",
            "extraction_method": "preamble",
            "section": p.get("section", "preamble"),
            "is_stub": len(p["definition"]) < 30,
            "has_math": False,
            "has_disambiguation": False,
        }
        terms.append(record)
        existing.add(key)
        added.append(p["term"])

    print(f"\nadded: {len(added)}")
    for t in added:
        print(f"  + {t}")
    if skipped:
        print(f"skipped (already present): {len(skipped)}")
        for t in skipped:
            print(f"  - {t}")

    print(f"\ntotal after merge: {len(terms)}")

    out_path = Path(args.output)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(terms, f, indent=2, ensure_ascii=False)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
