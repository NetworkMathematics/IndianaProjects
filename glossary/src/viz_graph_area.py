#!/usr/bin/env python3
"""
renders all nodes in a given math_area with internal edges

python viz_graph_area.py [--area algebra] [--input term_graph.json] [--output-dir .]
python viz_graph_area.py --all   # render all areas
python viz_graph_area.py --all --isolates   # render all areas

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


EDGE_STYLE = {
    "definitional_dependency": ("#555555", 0.35, 0.5),
    "stub_reference":          ("#888888", 0.5, 0.8),
    "cross_glossary_identity": ("#bbbbbb", 0.3, 0.4),
}


def render_area(graph_data: dict, area: str, output_dir: Path,
                show: bool = True, include_isolates: bool = False):
    """render subgraph for a single math area. returns data dict or None."""
    nodes = graph_data["nodes"]
    edges = graph_data["edges"]

    # select nodes belonging to this area
    area_nodes = set()
    for nid, ndata in nodes.items():
        if area in ndata.get("math_areas", []):
            area_nodes.add(nid)

    if not area_nodes:
        print(f"  no nodes for area '{area}', skipping")
        return None

    # build subgraph
    G = nx.DiGraph()
    for nid in area_nodes:
        G.add_node(nid)

    for e in edges:
        if e["source"] in area_nodes and e["target"] in area_nodes:
            G.add_edge(e["source"], e["target"], type=e["type"])

    # optionally drop isolates for cleaner viz
    isolates = list(nx.isolates(G))
    if not include_isolates:
        G.remove_nodes_from(isolates)

    if G.number_of_nodes() == 0:
        print(f"  {area}: all {len(area_nodes)} nodes are isolates in this subgraph, skipping")
        return None

    iso_msg = f" (showing {len(isolates)} isolates)" if include_isolates else f" (+{len(isolates)} isolates removed)"
    print(f"  {area}: {G.number_of_nodes()} nodes{iso_msg}, "
          f"{G.number_of_edges()} edges")

    # layout
    k_val = 2.0 / np.sqrt(max(G.number_of_nodes(), 1))
    pos = nx.spring_layout(G, k=k_val, iterations=60, seed=42)

    # sizing by degree within subgraph
    sub_deg = dict(G.degree())
    max_deg = max(sub_deg.values()) if sub_deg else 1

    node_sizes = [max(10, (sub_deg[n] / max(max_deg, 1)) * 250) for n in G.nodes()]
    node_colors = ["#444444"] * G.number_of_nodes()

    # figure size scales with node count
    side = max(6, min(14, np.sqrt(G.number_of_nodes()) * 1.2))
    fig, ax = plt.subplots(figsize=(side, side))
    ax.set_facecolor("white")

    # draw edges
    for etype, (color, alpha, width) in EDGE_STYLE.items():
        elist = [(u, v) for u, v, d in G.edges(data=True) if d.get("type") == etype]
        if elist:
            nx.draw_networkx_edges(G, pos, edgelist=elist, ax=ax,
                                   edge_color=color, alpha=alpha,
                                   width=width, arrows=True,
                                   arrowsize=3, arrowstyle="-|>",
                                   connectionstyle="arc3,rad=0.04")

    nx.draw_networkx_nodes(G, pos, ax=ax,
                           node_color=node_colors,
                           node_size=node_sizes,
                           edgecolors="#222222",
                           linewidths=0.3,
                           alpha=0.8)

    # label all nodes, font size scaled by subgraph degree
    for nid in G.nodes():
        deg = sub_deg[nid]
        fsize = 3.5 + 4.5 * (deg / max(max_deg, 1))
        ax.annotate(sanitize_label(nid), pos[nid], fontsize=fsize,
                    color="#111111", ha="center", va="center",
                    textcoords="offset points", xytext=(0, 6))

    ax.set_axis_off()
    plt.tight_layout()

    safe_area = area.replace(" ", "_")
    out_path = output_dir / f"viz_graph_{safe_area}.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    pdf_path = out_path.with_suffix(".pdf")
    plt.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    print(f"  wrote {out_path}")
    print(f"  wrote {pdf_path}")
    if show:
        plt.show()
    plt.close()

    # export data structure
    data_out = {
        "area": area,
        "nodes": list(G.nodes()),
        "edges": [{"source": u, "target": v, "type": d.get("type")}
                  for u, v, d in G.edges(data=True)],
        "isolates_removed": [nid for nid in isolates] if not include_isolates else [],
    }
    data_path = output_dir / f"viz_graph_{safe_area}_data.json"
    json.dump(data_out, open(data_path, "w", encoding="utf-8"), indent=2)
    print(f"  wrote {data_path}")

    return data_out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="term_graph.json")
    parser.add_argument("--area", type=str, default=None,
                        help="math area to render (e.g. 'algebra')")
    parser.add_argument("--all", action="store_true",
                        help="render all areas")
    parser.add_argument("--output-dir", default="visualizations")
    parser.add_argument("--isolates", action="store_true", default=False,
                        help="include isolate nodes (default: remove them)")
    parser.add_argument("--exclude", action="append", default=[],
                        metavar="NODE",
                        help="node to exclude (repeatable, quote multi-word names)")
    parser.add_argument("--no-show", action="store_true",
                        help="disable interactive display")
    args = parser.parse_args()

    graph = json.load(open(args.input, encoding="utf-8"))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.exclude:
        exclude_set = set(args.exclude)
        for nid in exclude_set:
            graph["nodes"].pop(nid, None)
        graph["edges"] = [e for e in graph["edges"]
                          if e["source"] not in exclude_set
                          and e["target"] not in exclude_set]

    # collect all areas
    all_areas = set()
    for n in graph["nodes"].values():
        all_areas.update(n.get("math_areas", []))
    all_areas = sorted(all_areas)

    show = not args.no_show
    all_data = {}

    if args.all:
        print(f"rendering {len(all_areas)} area subgraphs:")
        for area in all_areas:
            result = render_area(graph, area, output_dir, show=show,
                                include_isolates=args.isolates)
            if result is not None:
                all_data[area] = result
    elif args.area:
        result = render_area(graph, args.area, output_dir, show=show,
                             include_isolates=args.isolates)
        if result is not None:
            all_data[args.area] = result
    else:
        print(f"available areas: {', '.join(all_areas)}")
        print("use --area <name> or --all")

    return all_data


if __name__ == "__main__":
    main()
