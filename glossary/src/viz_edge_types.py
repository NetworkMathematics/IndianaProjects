#!/usr/bin/env python3
"""edge type composition and per-area breakdown.
reads term_graph.json, outputs viz_edge_types.png."""

import json
import argparse
import numpy as np
from pathlib import Path
from collections import defaultdict

import sys
import matplotlib
if "--no-show" in sys.argv:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="term_graph.json")
    parser.add_argument("--output-dir", default="visualizations")
    parser.add_argument("--exclude", action="append", default=[],
                        metavar="NODE",
                        help="node to exclude (repeatable, quote multi-word names)")
    parser.add_argument("--no-show", action="store_true",
                        help="disable interactive display")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    graph = json.load(open(args.input, encoding="utf-8"))
    nodes = graph["nodes"]
    edges = graph["edges"]

    if args.exclude:
        exclude_set = set(args.exclude)
        for nid in exclude_set:
            nodes.pop(nid, None)
        edges = [e for e in edges
                 if e["source"] not in exclude_set
                 and e["target"] not in exclude_set]

    # global edge type counts
    by_type = defaultdict(int)
    for e in edges:
        by_type[e["type"]] += 1

    # per source-area edge type counts
    area_type = defaultdict(lambda: defaultdict(int))
    for e in edges:
        src_areas = nodes[e["source"]]["math_areas"]
        for sa in src_areas:
            area_type[sa][e["type"]] += 1

    types = sorted(by_type.keys())
    areas = sorted(area_type.keys())

    colors = {
        "definitional_dependency": "#404040",
        "stub_reference": "#999999",
        "cross_glossary_identity": "#cccccc",
    }

    fig, axes = plt.subplots(1, 2, figsize=(12, 5),
                              gridspec_kw={"width_ratios": [1, 2.5]})

    # left: global bar chart
    ax = axes[0]
    type_labels = [t.replace("_", "\n") for t in types]
    counts = [by_type[t] for t in types]
    bars = ax.barh(range(len(types)), counts,
                   color=[colors.get(t, "#666666") for t in types])
    ax.set_yticks(range(len(types)))
    ax.set_yticklabels(type_labels, fontsize=8)
    ax.set_xlabel(r"$n_{\mathrm{edges}}$", fontsize=10)
    ax.tick_params(labelsize=8)
    ax.invert_yaxis()

    for bar, c in zip(bars, counts):
        ax.text(bar.get_width() + max(counts) * 0.02, bar.get_y() + bar.get_height() / 2,
                str(c), va="center", fontsize=8, color="#333333")

    # right: stacked bar per area
    ax2 = axes[1]
    area_labels = [a.replace("_", "\n") for a in areas]
    bottoms = np.zeros(len(areas))

    for t in types:
        vals = [area_type[a][t] for a in areas]
        ax2.barh(range(len(areas)), vals, left=bottoms,
                 color=colors.get(t, "#666666"),
                 label=t.replace("_", " "))
        bottoms += np.array(vals)

    ax2.set_yticks(range(len(areas)))
    ax2.set_yticklabels(area_labels, fontsize=8)
    ax2.set_xlabel(r"$n_{\mathrm{edges}}$", fontsize=10)
    ax2.tick_params(labelsize=8)
    ax2.invert_yaxis()
    ax2.legend(fontsize=7, loc="lower right")

    plt.tight_layout()
    out_path = output_dir / "viz_edge_types.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    pdf_path = out_path.with_suffix(".pdf")
    plt.savefig(pdf_path, bbox_inches="tight")
    print(f"wrote {out_path}")
    print(f"wrote {pdf_path}")
    if not args.no_show:
        plt.show()
    plt.close()

    # export data structure
    data_out = {
        "global_edge_type_counts": dict(by_type),
        "per_area_edge_type_counts": {a: dict(area_type[a]) for a in areas},
    }
    data_path = output_dir / "viz_edge_types_data.json"
    json.dump(data_out, open(data_path, "w", encoding="utf-8"), indent=2)
    print(f"wrote {data_path}")

    return data_out


if __name__ == "__main__":
    main()
