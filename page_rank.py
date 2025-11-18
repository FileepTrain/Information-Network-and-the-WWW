import networkx as nx
import argparse
import matplotlib.pyplot as plt
from web_crawler import  crawl_to_gml 
from vis_graph import draw_graph, plot_degree_loglog

# File Handeling Funcitons
# ====================================================================================================
def load_gml(path: str):
    """To take in a graph .gml file, and check that the input ID values are ints
    Input: either a local file with just the name, or the file's entire path
    Output: the graph that corresponds to the the file name
    """
    try:
        G = nx.read_gml(path)
    except Exception as e:
        raise nx.NetworkXError(f"Failed to read GML file: {e}")
    
    # ensure directed
    if not isinstance(G, nx.DiGraph):
        G = nx.DiGraph(G)
    
    #Normalize node labels to strings
    G = nx.relabel_nodes(G, lambda n: str(n), copy=True)
    
    if G.number_of_nodes() == 0:
        raise nx.NetworkXError("Graph has no nodes.")
    if G.number_of_edges() == 0:
        print("[WARN] Graph has no edges.")
            
    return G

def export_gml(G: nx.DiGraph, path: str) -> None:
    """
    Writes a graph to .gml.
    """
    nx.write_gml(G, path)
    
def write_pagerank_values(pr: dict, path: str):
    """
    Write "node pagerank" lines sorted descending by score.
    """
    with open(path, "w", encoding="utf-8") as f:
        for node, score in sorted(pr.items(), key=lambda kv: kv[1], reverse=True):
            f.write(f"{node} {score:.12f}\n")
    print(f"[PR] Wrote PageRank values to {path}")

# Functions
# ====================================================================================================
def run_pagerank(G: nx.DiGraph, alpha: float = 0.85, max_iter: int = 200, tol: float = 1e-8):
    if G.number_of_nodes() == 0:
        raise nx.NetworkXError("Cannot run PageRank on an empty graph.")
    return nx.pagerank(G, alpha=alpha, max_iter=max_iter, tol=tol)

# Arg Parser
# ====================================================================================================
"""To take all the arguments in the command line, save relevant information needed to compute
the functions, and make some checks that it follows the input instructions
"""
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PageRank assignment")
    
    parser.add_argument(
        "--crawler",
        help="Path to crawler output file",
    )
    parser.add_argument(
        "--input",
        help="Path to input .gml graph file",
    )
    parser.add_argument(
        "--loglogplot",
        action="store_true",
        help="Generate a log–log plot (test flag)",
    )
    parser.add_argument(
        "--crawler_graph",
        help="Path to save the crawled graph as .gml (used only with --crawler)",
    )
    parser.add_argument(
        "--pagerank_values",
        help="Path to save the PageRank values",
    )

    return parser

# Main
# ====================================================================================================
"""Builds the parser, and calls the functions that correspond to said argument. 
It also checks for additional erros such as requiring a .gml file,
ensuring that the input .gml file is properly made, the node ids are digits and within range, etc.
"""
def main():
    parser = build_parser()
    args = parser.parse_args()
    
    # make sure user calls crawler or input but not both
    if args.crawler and args.input:
        parser.error("You cannot use --crawler and --input at the same time. Choose one.")

    if not args.crawler and not args.input:
        parser.error("You must provide either --crawler <txt> or --input <gml>.")
        
    # initialize G
    G = nx.DiGraph()
    
    if args.crawler:
        out_gml = args.crawler_graph or "out_graph.gml"
        print(f"[CRAWL] reading seeds from {args.crawler}")
        print(f"[CRAWL] output GML -> {out_gml}")
        crawl_to_gml(args.crawler, out_gml)
        print("[CRAWL] done.")
        
        # load the newly created graph for use (PageRank, plotting, etc.)
        G = load_gml(out_gml)
        
    if args.input:
        G = load_gml(args.input)
        print(f"[INPUT] Loaded {args.input}: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        
    #visualize graph
    draw_graph(G, out_path="graph.png")
        
    # log–log degree plot if requested
    if args.loglogplot:
        plot_degree_loglog(G, out_path="degree_loglog.png")

    # PageRank if requested
    if args.pagerank_values:
        pr = run_pagerank(G)
        write_pagerank_values(pr, args.pagerank_values)

    # If nothing given, show help
    if not any(vars(args).values()):
        parser.print_help()
        
        
if __name__ == "__main__":
    main()