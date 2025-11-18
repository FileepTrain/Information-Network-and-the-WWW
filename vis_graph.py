# vis_graph.py
import math
import matplotlib.pyplot as plt
import networkx as nx
import os
import numpy as np


def draw_graph(G: nx.DiGraph, out_path: str = "graph.png"):
    """
    Draws the graph, saves it to an image, and always displays it.
    - Always shows all node labels.
    - Uses the largest weakly-connected component to fix spacing issues.
    """

    n_total = G.number_of_nodes()
    m_total = G.number_of_edges()
    if n_total == 0:
        print("[DRAW] Graph is empty; nothing to draw.")
        return

    print(f"[DRAW] Preparing {n_total} nodes / {m_total} edges...")

    # --- fix weird spacing (isolated nodes far away) ---
    wccs = list(nx.weakly_connected_components(G))
    if len(wccs) > 1:
        largest = max(wccs, key=len)
        G = G.subgraph(largest).copy()
        print(f"[DRAW] Using largest connected component ({G.number_of_nodes()} nodes, {G.number_of_edges()} edges)")

    n = G.number_of_nodes()

    pos = nx.random_layout(G, seed=42)

    # --- draw everything ---
    plt.figure(figsize=(10, 8))
    nx.draw_networkx_nodes(G, pos, node_size=30, alpha=0.9)
    nx.draw_networkx_edges(G, pos, width=0.5, alpha=0.6)
    nx.draw_networkx_labels(G, pos, font_size=5, font_color="black")

    plt.axis("off")
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    print(f"[DRAW] Saved graph visualization to {out_path}")

    # always show
    plt.show()

def plot_degree_loglog(G: nx.DiGraph, out_path: str = "degree_loglog.png"):
    """
    Plot the degree distribution on log–log axes, with a smooth line like the sample figure.
    """
    import numpy as np
    import matplotlib.pyplot as plt

    if G.number_of_nodes() == 0:
        print("[LOGLOG] Graph is empty; nothing to plot.")
        return

    # total degree per node (in + out)
    degs = np.array([G.in_degree(n) + G.out_degree(n) for n in G.nodes()])
    unique, counts = np.unique(degs, return_counts=True)

    # remove degree 0 entries (can't show log(0))
    mask = unique > 0
    unique = unique[mask]
    counts = counts[mask]

    if len(unique) == 0:
        print("[LOGLOG] No positive degrees; nothing to plot.")
        return

    plt.figure(figsize=(8, 6))

    # use a connected line instead of scattered dots
    plt.loglog(unique, counts, marker="", linestyle="-", linewidth=1.2)

    plt.xlabel("degree (log)")
    plt.ylabel("number of nodes (log)")
    plt.title("LogLog Plot")
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)
    plt.tight_layout()
    plt.savefig(out_path, dpi=200)
    print(f"[LOGLOG] Saved degree log–log plot to {out_path}")
    plt.show()
