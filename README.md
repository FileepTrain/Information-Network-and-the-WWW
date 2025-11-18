# Information-Network-and-the-WWW
## Mo Gibson and Philip Tran
This program works by creating a graph of the internet using Python and applying the Pagerank algorithm to identify the most relevant pages. 

## Setup Instructions
    --crawler: the text file users create to specify the web crawl. First, an integer with the number of pages (total nodes in the graph). Then, the domain that it will crawl. Finally, in order, for each line, the initial web pages to start crawling. All webpages must be in the domain called in the second line.

    --input graph.gml: If --crawler isn't called, this calls a directed graph that the program will use for the page rank algorithm and Loglog plot.

    --loglogplot: Creates a log-log plot (Specifically this plot to show the Power Laws Distribution; Structure of the Web slides)

    --crawler_graph out_graph.gml: Save the directed graph (used for analysis) to "out_graph.gml"

    --pagerank_values node_rank.txt: Save the page rank of all the websites analyzed to "node_rank.txt"


## Sample Command-Line Usage
    python page_rank.py --crawler crawler.txt
![Program Output](images/fin_term.png)

    python page_rank.py --input graph.gml