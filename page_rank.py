import networkx as nx
import argparse
import matplotlib.pyplot as plt

# File Handeling Funcitons
# ====================================================================================================
"""To take in a graph .gml file, and check that the input ID values are ints
Input: either a local file with just the name, or the file's entire path
Output: the graph that corresponds to the the file name
"""
def load_gml(path: str):
    try:
        G = nx.read_gml(path)
    except Exception as e:
        raise nx.NetworkXError(f"Failed to read GML file: {e}")
    
    #Normalize node labels to strings
    G = nx.relabel_nodes(G, lambda n: str(n), copy=True)
    
    #Check node attributes
    for node, data in G.nodes(data=True):
        for key, value in data.items():
            try:
                int(value)
            except Exception:
                raise nx.NetworkXError(f"Node {node} has non-numeric attribute '{key}': {value}")
            
    #Check edge attributes
    for u, v, data in G.edges(data=True):
        for key, value in data.items():
            try:
                int(value)
            except Exception:
                raise nx.NetworkXError(f"Edge ({u},{v}) has non-numeric attribute '{key}': {value}")
            
    return G

# Test Functions
# ====================================================================================================
def test_crawler(path):
    print(f"[TEST] --crawler argument detected: {path}")

def test_input(path):
    print(f"[TEST] --input argument detected: {path}")

def test_loglogplot(enabled):
    print(f"[TEST] --loglogplot flag detected: {enabled}")

def test_crawler_graph(path):
    print(f"[TEST] --crawler_graph argument detected: {path}")

def test_pagerank_values(path):
    print(f"[TEST] --pagerank_values argument detected: {path}")


# Arg Parser
# ====================================================================================================
"""To take all the arguments in the command line, save relevant information needed to compute
the functions, and make some checks that it follows the input instructions
"""
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Boilerplate for PageRank assignment")

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
        help="Path to save the crawler graph as .gml",
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

    if args.crawler:
        test_crawler(args.crawler)
    if args.input:
        test_input(args.input)
    if args.loglogplot:
        test_loglogplot(args.loglogplot)
    if args.crawler_graph:
        test_crawler_graph(args.crawler_graph)
    if args.pagerank_values:
        test_pagerank_values(args.pagerank_values)

    # If nothing given, show help
    if not any(vars(args).values()):
        parser.print_help()
        
        
if __name__ == "__main__":
    main()