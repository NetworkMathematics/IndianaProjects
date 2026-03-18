#!/usr/bin/env python3
"""core backbone network visualization
top-k nodes by degree
reads term_graph.json, outputs viz_graph_core.png.

python viz_graph_core.py [--input term_graph.json] [--top-k 120] [--output-dir .]
"""

import json
import argparse
import re
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

import unicodedata


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


def primary_area(node_data: dict) -> str:
    """pick a single math area for coloring (most specific wins)."""
    areas = node_data.get("math_areas", [])
    if not areas:
        return "unknown"
    # prefer non-cross-cutting
    for a in areas:
        if a != "cross-cutting":
            return a
    return areas[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="term_graph.json")
    parser.add_argument("--top-k", type=int, default=120)
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

    # select top-k nodes by total degree
    ranked = sorted(nodes.values(), key=lambda n: -n["degree"])
    top_ids = set(n["id"] for n in ranked[:args.top_k])

    # build networkx graph from subgraph
    G = nx.DiGraph()
    for nid in top_ids:
        G.add_node(nid)

    edge_types_in_graph = defaultdict(int)
    for e in edges:
        if e["source"] in top_ids and e["target"] in top_ids:
            G.add_edge(e["source"], e["target"], type=e["type"])
            edge_types_in_graph[e["type"]] += 1

    print(f"subgraph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    for t, c in sorted(edge_types_in_graph.items()):
        print(f"  {t}: {c}")

    # layout
    pos = nx.spring_layout(G, k=1.8 / np.sqrt(G.number_of_nodes()),
                           iterations=80, seed=42)

    # node properties
    node_colors = []
    node_sizes = []
    for nid in G.nodes():
        area = primary_area(nodes[nid])
        node_colors.append(AREA_COLORS.get(area, "#cccccc"))
        deg = nodes[nid]["degree"]
        node_sizes.append(max(8, min(deg * 2.5, 200)))

    # edge properties by type
    edge_styles = {
        "definitional_dependency": ("#888888", 0.3, 0.5),
        "stub_reference":          ("#aaaaaa", 0.4, 0.8),
        "cross_glossary_identity": ("#cccccc", 0.2, 0.4),
    }

    fig, ax = plt.subplots(figsize=(14, 14))
    ax.set_facecolor("white")

    # draw edges by type
    for etype, (color, alpha, width) in edge_styles.items():
        elist = [(u, v) for u, v, d in G.edges(data=True) if d.get("type") == etype]
        if elist:
            nx.draw_networkx_edges(G, pos, edgelist=elist, ax=ax,
                                   edge_color=color, alpha=alpha,
                                   width=width, arrows=True,
                                   arrowsize=4, arrowstyle="-|>",
                                   connectionstyle="arc3,rad=0.05")

    # draw nodes
    nx.draw_networkx_nodes(G, pos, ax=ax,
                           node_color=node_colors,
                           node_size=node_sizes,
                           edgecolors="#333333",
                           linewidths=0.3,
                           alpha=0.85)

    # label all nodes, font size scaled by degree
    max_deg = max(nodes[nid]["degree"] for nid in G.nodes()) or 1
    for nid in G.nodes():
        deg = nodes[nid]["degree"]
        fsize = 3.5 + 4.5 * (deg / max_deg)
        ax.annotate(sanitize_label(nid), pos[nid], fontsize=fsize,
                    color="#111111", ha="center", va="center",
                    textcoords="offset points", xytext=(0, 6))

    # legend for math areas
    legend_areas = sorted(set(primary_area(nodes[nid]) for nid in G.nodes()))
    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="w",
                    markerfacecolor=AREA_COLORS.get(a, "#cccccc"),
                    markersize=6, label=a.replace("_", " "))
        for a in legend_areas
    ]
    ax.legend(handles=legend_handles, loc="lower left", fontsize=6,
              framealpha=0.8, ncol=2)

    ax.set_axis_off()
    plt.tight_layout()

    out_path = output_dir / "viz_graph_core.png"
    plt.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    pdf_path = out_path.with_suffix(".pdf")
    plt.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    print(f"wrote {out_path}")
    print(f"wrote {pdf_path}")
    if not args.no_show:
        plt.show()
    plt.close()

    # export data structure
    data_out = {
        "top_k": args.top_k,
        "nodes": list(G.nodes()),
        "node_areas": {nid: primary_area(nodes[nid]) for nid in G.nodes()},
        "edges": [{"source": u, "target": v, "type": d.get("type")}
                  for u, v, d in G.edges(data=True)],
        "edge_type_counts": dict(edge_types_in_graph),
    }
    data_path = output_dir / "viz_graph_core_data.json"
    json.dump(data_out, open(data_path, "w", encoding="utf-8"), indent=2)
    print(f"wrote {data_path}")

    return data_out


if __name__ == "__main__":
    main()
