#!/usr/bin/env python3
"""connected component size distribution.
reads term_graph.json, outputs viz_components.png."""

import json
import argparse
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter

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

    # union-find for undirected components
    parent = {nid: nid for nid in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for e in edges:
        union(e["source"], e["target"])

    components = defaultdict(list)
    for nid in nodes:
        components[find(nid)].append(nid)

    sizes = sorted([len(c) for c in components.values()], reverse=True)
    size_counts = Counter(sizes)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # left: component size distribution (excluding largest)
    ax = axes[0]
    if len(sizes) > 1:
        small_sizes = sizes[1:]  # exclude giant component
        sc = Counter(small_sizes)
        ks = sorted(sc.keys())
        freqs = [sc[k] for k in ks]
        ax.bar(ks, freqs, color="#404040", edgecolor="none", width=0.8)
        ax.set_xlabel(r"$|\mathcal{C}|$ (excl. giant)", fontsize=10)
        ax.set_ylabel(r"$n(\mathcal{C})$", fontsize=10)
        ax.tick_params(labelsize=8)

    # annotate giant component
    if sizes:
        ax.annotate(
            f"giant component: {sizes[0]} nodes",
            xy=(0.95, 0.95), xycoords="axes fraction",
            ha="right", va="top", fontsize=8,
            color="#666666",
        )

    # right: cumulative fraction of nodes in top-k components
    ax2 = axes[1]
    cumsum = np.cumsum(sizes) / sum(sizes)
    ax2.plot(range(1, len(cumsum) + 1), cumsum, color="#333333", linewidth=1.2)
    ax2.set_xlabel(r"$k$ (components, ranked by size)", fontsize=10)
    ax2.set_ylabel(r"cumulative node fraction", fontsize=10)
    ax2.set_xscale("log")
    ax2.tick_params(labelsize=8)
    ax2.axhline(y=0.9, color="#999999", linestyle="--", linewidth=0.5)

    plt.tight_layout()
    out_path = output_dir / "viz_components.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    pdf_path = out_path.with_suffix(".pdf")
    plt.savefig(pdf_path, bbox_inches="tight")
    print(f"wrote {out_path}")
    print(f"wrote {pdf_path}")
    if not args.no_show:
        plt.show()
    plt.close()

    # summary to stdout
    print(f"total components: {len(sizes)}")
    print(f"giant component: {sizes[0]} nodes ({sizes[0]/len(nodes)*100:.1f}%)")
    print(f"isolates: {size_counts.get(1, 0)}")
    print(f"components of size 2-10: {sum(c for s, c in size_counts.items() if 2 <= s <= 10)}")

    # export data structure
    data_out = {
        "component_sizes": sizes,
        "size_counts": {str(k): v for k, v in size_counts.items()},
        "components": {root: members for root, members in components.items()},
        "cumulative_node_fraction": cumsum.tolist(),
    }
    data_path = output_dir / "viz_components_data.json"
    json.dump(data_out, open(data_path, "w", encoding="utf-8"), indent=2)
    print(f"wrote {data_path}")

    return data_out


if __name__ == "__main__":
    main()
