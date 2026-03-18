#!/usr/bin/env python3
"""the plate of spaghetti. all nodes, all edges, all labels.
reads term_graph.json, outputs viz_graph_full.png.








python viz_graph_full.py [--input term_graph.json] [--output-dir .]
"""

import json
import argparse
import re
import unicodedata
import numpy as np
from pathlib import Path
from collections import defaultdict

import sys
import matplotlib
if "--no-show" in sys.argv:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import networkx as nx
except ImportError:
    import sys
    sys.exit("requires networkx: pip install networkx")


AREA_COLORS = {
    "algebra":                "#2d2d2d",
    "analysis":               "#666666",
    "foundations":             "#999999",
    "geometry_topology":      "#444444",
    "discrete_applied":       "#777777",
    "probability_statistics": "#aaaaaa",
    "number_theory":          "#555555",
    "cross-cutting":          "#bbbbbb",
    "applied_cs":             "#cccccc",
    "applied_statistics":     "#dddddd",
    "unknown":                "#eeeeee",
}


def sanitize_label(text: str) -> str:
    """replace unicode math symbols with ascii equivalents for font safety."""
    out = []
    for ch in text:
        cp = ord(ch)
        if 0x1D400 <= cp <= 0x1D7FF:
            name = unicodedata.name(ch, "")
            m = re.match(r'.*?(CAPITAL|SMALL)\s+(\w)$', name)
            if m:
                letter = m.group(2)
                if m.group(1) == "SMALL":
                    letter = letter.lower()
                out.append(letter)
            else:
                m2 = re.search(r'DIGIT\s+(\w+)$', name)
                if m2:
                    digits = {"ZERO":"0","ONE":"1","TWO":"2","THREE":"3",
                              "FOUR":"4","FIVE":"5","SIX":"6","SEVEN":"7",
                              "EIGHT":"8","NINE":"9"}
                    out.append(digits.get(m2.group(1), "?"))
                else:
                    out.append("?")
        elif cp == 0x2102: out.append("C")
        elif cp == 0x2115: out.append("N")
        elif cp == 0x211A: out.append("Q")
        elif cp == 0x211D: out.append("R")
        elif cp == 0x2124: out.append("Z")
        else:
            out.append(ch)
    return "".join(out)


def primary_area(node_data: dict) -> str:
    areas = node_data.get("math_areas", [])
    if not areas:
        return "unknown"
    for a in areas:
        if a != "cross-cutting":
            return a
    return areas[0]


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

    G = nx.DiGraph()
    for nid in nodes:
        G.add_node(nid)
    for e in edges:
        G.add_edge(e["source"], e["target"], type=e["type"])

    print(f"full graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    print("computing layout (this may take a minute)...")

    pos = nx.spring_layout(G, k=0.8 / np.sqrt(max(G.number_of_nodes(), 1)),
                           iterations=50, seed=42)

    # node properties
    max_deg = max((nodes[nid]["degree"] for nid in G.nodes()), default=1) or 1
    node_colors = []
    node_sizes = []
    for nid in G.nodes():
        area = primary_area(nodes[nid])
        node_colors.append(AREA_COLORS.get(area, "#cccccc"))
        deg = nodes[nid]["degree"]
        node_sizes.append(max(1, min(deg * 0.8, 80)))

    # big canvas
    fig, ax = plt.subplots(figsize=(48, 48))
    ax.set_facecolor("white")

    # edges: hair-thin
    nx.draw_networkx_edges(G, pos, ax=ax,
                           edge_color="#cccccc",
                           alpha=0.08,
                           width=0.15,
                           arrows=False)

    # nodes
    nx.draw_networkx_nodes(G, pos, ax=ax,
                           node_color=node_colors,
                           node_size=node_sizes,
                           edgecolors="none",
                           alpha=0.7)

    # labels: all of them
    for nid in G.nodes():
        deg = nodes[nid]["degree"]
        fsize = 1.0 + 3.0 * (deg / max_deg)
        alpha = max(0.25, min(0.95, 0.25 + 0.7 * (deg / max_deg)))
        ax.annotate(sanitize_label(nid), pos[nid],
                    fontsize=fsize, color="#111111", alpha=alpha,
                    ha="center", va="center",
                    textcoords="offset points", xytext=(0, 2))

    # legend
    legend_areas = sorted(set(primary_area(nodes[nid]) for nid in G.nodes()))
    handles = [
        plt.Line2D([0], [0], marker="o", color="w",
                    markerfacecolor=AREA_COLORS.get(a, "#cccccc"),
                    markersize=8, label=a.replace("_", " "))
        for a in legend_areas
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=8,
              framealpha=0.9, ncol=2)

    ax.set_axis_off()
    plt.tight_layout()

    out_path = output_dir / "viz_graph_full.png"
    print(f"saving {out_path} (large file)...")
    plt.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="white")
    pdf_path = out_path.with_suffix(".pdf")
    print(f"saving pdf (may be large for vector rendering)...")
    plt.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    print(f"wrote {out_path}")
    print(f"wrote {pdf_path}")
    if not args.no_show:
        plt.show()
    plt.close()

    # export data structure
    data_out = {
        "nodes": list(G.nodes()),
        "node_areas": {nid: primary_area(nodes[nid]) for nid in G.nodes()},
        "edges": [{"source": u, "target": v, "type": d.get("type")}
                  for u, v, d in G.edges(data=True)],
    }
    data_path = output_dir / "viz_graph_full_data.json"
    json.dump(data_out, open(data_path, "w", encoding="utf-8"), indent=2)
    print(f"wrote {data_path}")

    return data_out


if __name__ == "__main__":
    main()
