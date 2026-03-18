#!/usr/bin/env python3
"""ego network visualization.
n-hop neighborhood around a specified term
reads term_graph.json, outputs viz_ego_{term}.png.

python viz_graph_ego.py --term "group" [--hops 2] [--input term_graph.json]
python viz_graph_ego.py --term "homomorphism" --hops 1
"""

import json
import argparse
import re
import numpy as np
from pathlib import Path

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
    areas = node_data.get("math_areas", [])
    if not areas:
        return "unknown"
    for a in areas:
        if a != "cross-cutting":
            return a
    return areas[0]


def find_node(nodes: dict, query: str) -> str:
    """find a node matching the query (case-insensitive, partial match)."""
    q = query.lower().strip()
    # exact match
    if q in nodes:
        return q
    # substring match
    candidates = [nid for nid in nodes if q in nid]
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        # prefer exact word match
        exact_word = [c for c in candidates if re.search(r'\b' + re.escape(q) + r'\b', c)]
        if len(exact_word) == 1:
            return exact_word[0]
        # prefer shortest
        candidates.sort(key=len)
        print(f"  ambiguous query '{query}', candidates: {candidates[:10]}")
        print(f"  using: {candidates[0]}")
        return candidates[0]
    return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="term_graph.json")
    parser.add_argument("--term", type=str, required=True)
    parser.add_argument("--hops", type=int, default=2)
    parser.add_argument("--max-nodes", type=int, default=200,
                        help="cap on neighborhood size")
    parser.add_argument("--output-dir", default="visualizations")
    parser.add_argument("--exclude", action="append", default=[],
                        metavar="NODE",
                        help="node to exclude (repeatable, quote multi-word names)")
    parser.add_argument("--no-show", action="store_true",
                        help="disable interactive display")
    args = parser.parse_args()

    graph = json.load(open(args.input, encoding="utf-8"))
    nodes = graph["nodes"]
    edges = graph["edges"]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.exclude:
        exclude_set = set(args.exclude)
        for nid in exclude_set:
            nodes.pop(nid, None)
        edges = [e for e in edges
                 if e["source"] not in exclude_set
                 and e["target"] not in exclude_set]

    # resolve term
    center = find_node(nodes, args.term)
    if not center:
        print(f"term '{args.term}' not found in graph")
        return None

    print(f"center node: {center}")
    print(f"  degree: {nodes[center]['degree']}, "
          f"areas: {nodes[center]['math_areas']}")

    # build full networkx graph (undirected for neighborhood search)
    G_full = nx.DiGraph()
    for nid in nodes:
        G_full.add_node(nid)
    for e in edges:
        G_full.add_edge(e["source"], e["target"], type=e["type"])

    # bfs to collect n-hop neighborhood
    neighborhood = {center}
    frontier = {center}
    for hop in range(args.hops):
        next_frontier = set()
        for n in frontier:
            # both directions
            next_frontier.update(G_full.successors(n))
            next_frontier.update(G_full.predecessors(n))
        next_frontier -= neighborhood
        neighborhood.update(next_frontier)
        frontier = next_frontier

        if len(neighborhood) > args.max_nodes:
            print(f"  neighborhood exceeded {args.max_nodes} at hop {hop+1}, truncating")
            # keep only highest-degree nodes from this frontier
            excess = len(neighborhood) - args.max_nodes
            frontier_ranked = sorted(next_frontier,
                                     key=lambda n: nodes[n]["degree"])
            to_remove = set(frontier_ranked[:excess])
            neighborhood -= to_remove
            frontier -= to_remove
            break

    # build subgraph
    G = G_full.subgraph(neighborhood).copy()
    print(f"  ego graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    if G.number_of_nodes() < 2:
        print("  too few nodes to visualize")
        return None

    # layout: center node fixed at origin
    k_val = 2.5 / np.sqrt(max(G.number_of_nodes(), 1))
    fixed = {center: (0.0, 0.0)}
    pos = nx.spring_layout(G, k=k_val, iterations=80, seed=42,
                           pos=fixed, fixed=[center])

    # distance from center determines opacity
    center_pos = np.array(pos[center])
    max_dist = max(np.linalg.norm(np.array(pos[n]) - center_pos)
                   for n in G.nodes()) or 1.0

    # node properties
    node_list = list(G.nodes())
    node_colors = []
    node_sizes = []
    node_alphas = []
    for nid in node_list:
        area = primary_area(nodes[nid])
        node_colors.append(AREA_COLORS.get(area, "#cccccc"))
        deg = nodes[nid]["degree"]
        node_sizes.append(max(15, min(deg * 3, 300)) if nid != center
                          else 400)
        dist = np.linalg.norm(np.array(pos[nid]) - center_pos) / max_dist
        node_alphas.append(max(0.3, 1.0 - dist * 0.6))

    side = max(8, min(14, np.sqrt(G.number_of_nodes()) * 1.0))
    fig, ax = plt.subplots(figsize=(side, side))
    ax.set_facecolor("white")

    # draw edges
    edge_colors = []
    edge_alphas = []
    for u, v in G.edges():
        edge_colors.append("#888888")
        edge_alphas.append(0.25)

    nx.draw_networkx_edges(G, pos, ax=ax,
                           edge_color=edge_colors,
                           alpha=0.25,
                           width=0.4,
                           arrows=True,
                           arrowsize=3,
                           arrowstyle="-|>",
                           connectionstyle="arc3,rad=0.03")

    # draw nodes
    nx.draw_networkx_nodes(G, pos, ax=ax,
                           nodelist=node_list,
                           node_color=node_colors,
                           node_size=node_sizes,
                           edgecolors="#333333",
                           linewidths=0.3,
                           alpha=0.8)

    # highlight center
    nx.draw_networkx_nodes(G, pos, ax=ax,
                           nodelist=[center],
                           node_color="#000000",
                           node_size=400,
                           edgecolors="#000000",
                           linewidths=1.5)

    # label all nodes, font size scaled by subgraph degree
    sub_deg = dict(G.degree())
    max_sub_deg = max(sub_deg.values()) if sub_deg else 1
    for nid in G.nodes():
        deg = sub_deg[nid]
        fsize = 4.0 + 4.0 * (deg / max(max_sub_deg, 1))
        weight = "bold" if nid == center else "normal"
        ax.annotate(sanitize_label(nid), pos[nid], fontsize=fsize,
                    color="#111111", ha="center", va="center",
                    fontweight=weight,
                    textcoords="offset points", xytext=(0, 6))

    # legend
    areas_present = sorted(set(primary_area(nodes[nid]) for nid in G.nodes()))
    handles = [
        plt.Line2D([0], [0], marker="o", color="w",
                    markerfacecolor=AREA_COLORS.get(a, "#cccccc"),
                    markersize=6, label=a.replace("_", " "))
        for a in areas_present
    ]
    ax.legend(handles=handles, loc="lower left", fontsize=6, framealpha=0.8)

    ax.set_axis_off()
    plt.tight_layout()

    safe_name = re.sub(r'[^\w-]', '_', center)
    out_path = output_dir / f"viz_ego_{safe_name}.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    pdf_path = out_path.with_suffix(".pdf")
    plt.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    print(f"wrote {out_path}")
    print(f"wrote {pdf_path}")
    if not args.no_show:
        plt.show()
    plt.close()

    # export data structure
    data_out = {
        "center": center,
        "hops": args.hops,
        "nodes": list(G.nodes()),
        "node_areas": {nid: primary_area(nodes[nid]) for nid in G.nodes()},
        "edges": [{"source": u, "target": v, "type": d.get("type")}
                  for u, v, d in G.edges(data=True)],
    }
    data_path = output_dir / f"viz_ego_{safe_name}_data.json"
    json.dump(data_out, open(data_path, "w", encoding="utf-8"), indent=2)
    print(f"wrote {data_path}")

    return data_out


if __name__ == "__main__":
    main()
