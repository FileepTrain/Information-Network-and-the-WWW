# web_crawler.py
from urllib.parse import urlparse, urlunparse, urljoin
from scrapy.crawler import CrawlerProcess
from scrapy.exceptions import CloseSpider
import scrapy
import networkx as nx
import sys
from collections import OrderedDict


def normalize_domain(domain_line: str) -> str:
    """Accepts 'dblp.org' OR 'https://dblp.org/pid' and returns 'dblp.org'."""
    parsed = urlparse(domain_line)
    return (parsed.netloc or domain_line).lower().strip()


def read_txt_crawler(path: str):
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    n = int(lines[0])
    domain_raw = lines[1]
    domain = normalize_domain(domain_raw)
    pages = lines[2:2 + n]
    return n, domain, pages


class DomainSpider(scrapy.Spider):
    name = "domain_spider"
    custom_settings = {
        # Respect robots unless your assignment allows otherwise
        "ROBOTSTXT_OBEY": True,

        # Keep logs quiet
        "LOG_LEVEL": "CRITICAL",

        # Timeouts / retries (gentle, but more resilient)
        "DOWNLOAD_TIMEOUT": 20,            # was 7
        "RETRY_ENABLED": True,             # was False
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [408, 429, 500, 502, 503, 504, 522, 524],
        "HTTPERROR_ALLOW_ALL": True,       # give us Response objects for non-200s

        # Throughput + autothrottle (friendlier and reduces flakiness)
        "CONCURRENT_REQUESTS": 16,         # was 64
        "CONCURRENT_REQUESTS_PER_DOMAIN": 8,  # was 32
        "REACTOR_THREADPOOL_MAXSIZE": 64,

        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 0.1,
        "AUTOTHROTTLE_MAX_DELAY": 5,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": 2.0,

        # No artificial delays beyond autothrottle
        "DOWNLOAD_DELAY": 0,
        "RANDOMIZE_DOWNLOAD_DELAY": False,

        # Lean requests
        "COOKIES_ENABLED": False,
        "COMPRESSION_ENABLED": True,

        # Cache DNS heavily
        "DNSCACHE_ENABLED": True,
        "DNSCACHE_SIZE": 10000,

        # Prefer BFS queues (keeps domains warm; fewer cold TCP handshakes)
        "DEPTH_PRIORITY": 1,
        "SCHEDULER_DISK_QUEUE": "scrapy.squeues.PickleFifoDiskQueue",
        "SCHEDULER_MEMORY_QUEUE": "scrapy.squeues.FifoMemoryQueue",

        # Skip huge pages
        "DOWNLOAD_MAXSIZE": 5 * 1024 * 1024,  # 5 MB
        "DOWNLOAD_FAIL_ON_DATALOSS": False,

        # Trim some overhead
        "TELNETCONSOLE_ENABLED": False,

        # Slightly stricter accept headers; enables brotli if installed
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
        },
    }

    def __init__(self, start_urls, allowed_domain, max_nodes, out_gml, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = start_urls
        self.allowed_domain = allowed_domain  # normalized like 'dblp.org'
        self.max_nodes = max_nodes
        self.out_gml = out_gml
        self.visited = set()
        self.visit_order = []    # preserves first-seen order
        self.edges = set()
        # canonicalized seeds so we can force-keep them later
        self.seed_nodes = {self.canon(u) for u in start_urls if self.same_domain(u)}

    def canon(self, url: str) -> str:
        p = urlparse(url)
        # strip fragment AND query to merge tracking variants
        return urlunparse((
            p.scheme or "https",
            p.netloc.lower(),
            (p.path.rstrip("/") or "/"),
            p.params,
            "",           # drop query
            ""            # drop fragment
        ))

    def same_domain(self, url: str) -> bool:
        netloc = urlparse(url).netloc.lower()
        dom = self.allowed_domain
        # allow exact or subdomains: foo.dblp.org matches dblp.org
        return netloc == dom or netloc.endswith("." + dom)

    def is_html(self, response) -> bool:
        ctype = response.headers.get(b"Content-Type", b"").decode("utf-8").lower()
        return "text/html" in ctype or "application/xhtml+xml" in ctype

    def start_requests(self):
        # Always attach an errback so we can record seeds even on failure/timeout
        for u in self.start_urls:
            yield scrapy.Request(
                u,
                callback=self.parse,
                errback=self.on_error,
                dont_filter=True
            )

    def on_error(self, failure):
        """Record the request URL as a node even if the fetch failed."""
        req = failure.request
        src = self.canon(req.url)
        if src not in self.visited:
            self.visited.add(src)
            self.visit_order.append(src)
            pct = 100 * len(self.visited) / self.max_nodes
            print(f"[CRAWL] {len(self.visited)}/{self.max_nodes} pages ({pct:.1f}%)",
                  end="\r", flush=True)

        # stop immediately if cap reached
        if len(self.visited) >= self.max_nodes:
            raise CloseSpider(reason="max_nodes_reached")

    def parse(self, response):
        src = self.canon(response.url)

        # mark the page as seen (even for non-200 or non-HTML)
        if src not in self.visited:
            self.visited.add(src)
            self.visit_order.append(src)

        # progress tracker
        pct = 100 * len(self.visited) / self.max_nodes
        print(f"[CRAWL] {len(self.visited)}/{self.max_nodes} pages ({pct:.1f}%)",
              end="\r", flush=True)

        # cap reached?
        if len(self.visited) >= self.max_nodes:
            raise CloseSpider(reason="max_nodes_reached")

        # If not OK/HTML, keep the node but don't extract links
        if response.status != 200 or not self.is_html(response):
            return

        for href in response.css("a::attr(href)").getall():
            if len(self.visited) >= self.max_nodes:
                break  # don't queue more work

            abs_url = urljoin(response.url, href)
            if not abs_url.startswith("http"):
                continue
            if not self.same_domain(abs_url):
                continue

            # *** Only follow links that end with ".html" (matches the example) ***
            if not abs_url.lower().endswith(".html"):
                continue

            dst = self.canon(abs_url)
            self.edges.add((src, dst))

            if dst not in self.visited:
                yield scrapy.Request(
                    abs_url,
                    callback=self.parse,
                    errback=self.on_error,
                    dont_filter=True
                )

    def closed(self, reason):
        # newline so the final message isn't on same line as progress
        print()

        # Prioritize seeds, then first-seen order, capped at max_nodes
        ordered = list(OrderedDict.fromkeys(list(self.seed_nodes) + self.visit_order))[:self.max_nodes]
        keep_nodes = set(ordered)

        # keep edges only among kept nodes and not self-loops
        edges_kept = [(u, v) for (u, v) in self.edges
                      if u in keep_nodes and v in keep_nodes and u != v]

        G = nx.DiGraph()
        G.add_edges_from(edges_kept)

        # also add isolated nodes that were kept but have no edges
        for u in keep_nodes:
            if u not in G:
                G.add_node(u)

        nx.write_gml(G, self.out_gml)
        self.logger.info(
            f"Wrote GML to {self.out_gml} "
            f"({G.number_of_nodes()} nodes, {G.number_of_edges()} edges). "
            f"Visited={len(self.visited)}, RawEdges={len(self.edges)}, KeptEdges={len(edges_kept)}"
        )


def crawl_to_gml(crawler_txt: str, out_gml: str):
    n, domain, pages = read_txt_crawler(crawler_txt)

    starts = []
    for u in pages:
        if not u.startswith("http"):
            u = "https://" + u.lstrip("/")
        # filter to same domain (including subdomains)
        net = urlparse(u).netloc.lower()
        if not (net == domain or net.endswith("." + domain)):
            continue
        starts.append(u)

    if not starts:
        raise RuntimeError("No valid start URLs inside the specified domain.")

    process = CrawlerProcess()
    process.crawl(
        DomainSpider,
        start_urls=starts,
        allowed_domain=domain,
        max_nodes=n,
        out_gml=out_gml
    )
    process.start()


# Optional: allow running from CLI like `python web_crawler.py input.txt output.gml`
if __name__ == "__main__":
    if len(sys.argv) == 3:
        crawl_to_gml(sys.argv[1], sys.argv[2])
    else:
        print("Usage: python web_crawler.py <crawler.txt> <out.gml>")
