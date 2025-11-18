# web_crawler.py
from urllib.parse import urlparse, urlunparse, urljoin
from scrapy.crawler import CrawlerProcess
from scrapy.exceptions import CloseSpider
import scrapy
import networkx as nx

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

        # Timeouts / retries
        "DOWNLOAD_TIMEOUT": 7,
        "RETRY_ENABLED": False,

        # Max throughput
        "CONCURRENT_REQUESTS": 64,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 32,
        "REACTOR_THREADPOOL_MAXSIZE": 64,

        # No artificial delays
        "DOWNLOAD_DELAY": 0,
        "RANDOMIZE_DOWNLOAD_DELAY": False,
        "AUTOTHROTTLE_ENABLED": False,

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
            # Optionally set a UA your class allows; modern UAs often get faster paths
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
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

    def parse(self, response):
        
        if response.status != 200:
            return
        if not self.is_html(response):
            return

        src = self.canon(response.url)
        if src in self.visited:
            return

        self.visited.add(src)
        self.visit_order.append(src)

        # stop immediately if cap reached
        if len(self.visited) >= self.max_nodes:
            raise CloseSpider(reason="max_nodes_reached")

        for href in response.css("a::attr(href)").getall():
            if len(self.visited) >= self.max_nodes:
                break  # don't queue more work

            abs_url = urljoin(response.url, href)
            if not abs_url.startswith("http"):
                continue
            if not self.same_domain(abs_url):
                continue

            dst = self.canon(abs_url)
            self.edges.add((src, dst))

            if dst not in self.visited:
                yield scrapy.Request(abs_url, callback=self.parse, dont_filter=True)


    def closed(self, reason):
        # respect the first-seen order strictly
        keep_nodes = set(self.visit_order[:self.max_nodes])

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
        if not (urlparse(u).netloc.lower() == domain or urlparse(u).netloc.lower().endswith("." + domain)):
            continue
        starts.append(u)

    if not starts:
        raise RuntimeError("No valid start URLs inside the specified domain.")

    process = CrawlerProcess()
    process.crawl(DomainSpider,
                  start_urls=starts,
                  allowed_domain=domain,
                  max_nodes=n,
                  out_gml=out_gml)
    process.start()
