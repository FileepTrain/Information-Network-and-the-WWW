import math
import matplotlib.pyplot as plt
import networkx as nx

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
