#!/usr/bin/env python3
"""degree distribution plots for the term graph.
reads term_graph.json, outputs viz_degree_dist.png."""

import json
import argparse
import numpy as np
from pathlib import Path

import sys
import matplotlib
if "--no-show" in sys.argv:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import Counter


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

    if args.exclude:
        exclude_set = set(args.exclude)
        for nid in exclude_set:
            nodes.pop(nid, None)

    in_degs = [n["in_degree"] for n in nodes.values()]
    out_degs = [n["out_degree"] for n in nodes.values()]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    for ax, data, label in [
        (axes[0], in_degs, r"$k_{\mathrm{in}}$"),
        (axes[1], out_degs, r"$k_{\mathrm{out}}$"),
    ]:
        counts = Counter(data)
        ks = sorted(counts.keys())
        freqs = [counts[k] for k in ks]

        # filter to k > 0 for log-log
        ks_pos = [k for k in ks if k > 0]
        freqs_pos = [counts[k] for k in ks_pos]

        ax.scatter(ks_pos, freqs_pos, s=12, alpha=0.7, color="#333333",
                   edgecolors="none")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(label, fontsize=11)
        ax.set_ylabel(r"$n(k)$", fontsize=11)
        ax.tick_params(labelsize=9)

        # annotate zero-degree count
        n_zero = counts.get(0, 0)
        if n_zero:
            ax.annotate(
                f"$k=0$: {n_zero}",
                xy=(0.95, 0.95), xycoords="axes fraction",
                ha="right", va="top", fontsize=8,
                color="#666666",
            )

    plt.tight_layout()
    out_path = output_dir / "viz_degree_dist.png"
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
        "in_degrees": in_degs,
        "out_degrees": out_degs,
        "in_degree_counts": {str(k): v for k, v in Counter(in_degs).items()},
        "out_degree_counts": {str(k): v for k, v in Counter(out_degs).items()},
    }
    data_path = output_dir / "viz_degree_dist_data.json"
    json.dump(data_out, open(data_path, "w", encoding="utf-8"), indent=2)
    print(f"wrote {data_path}")

    return data_out


if __name__ == "__main__":
    main()
