#!/usr/bin/env python3
"""cross-area edge density heatmap.
reads term_graph.json, outputs viz_area_heatmap.png."""

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

    # count edges between math area pairs
    area_edges = defaultdict(int)
    all_areas = set()
    for e in edges:
        src_areas = nodes[e["source"]]["math_areas"]
        tgt_areas = nodes[e["target"]]["math_areas"]
        for sa in src_areas:
            for ta in tgt_areas:
                area_edges[(sa, ta)] += 1
                all_areas.add(sa)
                all_areas.add(ta)

    areas = sorted(all_areas)
    n = len(areas)
    area_idx = {a: i for i, a in enumerate(areas)}

    mat = np.zeros((n, n))
    for (sa, ta), count in area_edges.items():
        mat[area_idx[sa], area_idx[ta]] = count

    # log scale for visibility (add 1 to avoid log(0))
    mat_log = np.log10(mat + 1)

    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(mat_log, cmap="Greys", aspect="equal")

    # short labels
    short = [a.replace("_", "\n") for a in areas]
    ax.set_xticks(range(n))
    ax.set_xticklabels(short, fontsize=7, rotation=45, ha="right")
    ax.set_yticks(range(n))
    ax.set_yticklabels(short, fontsize=7)
    ax.set_xlabel(r"$\mathrm{target\ area}$", fontsize=10)
    ax.set_ylabel(r"$\mathrm{source\ area}$", fontsize=10)

    # annotate cells with raw counts
    for i in range(n):
        for j in range(n):
            val = int(mat[i, j])
            if val > 0:
                color = "white" if mat_log[i, j] > mat_log.max() * 0.6 else "black"
                ax.text(j, i, str(val), ha="center", va="center",
                        fontsize=6, color=color)

    cbar = plt.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
    cbar.set_label(r"$\log_{10}(n+1)$", fontsize=9)
    cbar.ax.tick_params(labelsize=7)

    plt.tight_layout()
    out_path = output_dir / "viz_area_heatmap.png"
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
        "areas": areas,
        "matrix": mat.tolist(),
        "matrix_log": mat_log.tolist(),
    }
    data_path = output_dir / "viz_area_heatmap_data.json"
    json.dump(data_out, open(data_path, "w", encoding="utf-8"), indent=2)
    print(f"wrote {data_path}")

    return data_out


if __name__ == "__main__":
    main()
