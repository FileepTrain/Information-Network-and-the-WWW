# --- add these imports at the top of page_rank.py ---
from scrapy.crawler import CrawlerProcess
from scrapy.exceptions import CloseSpider
import scrapy
from urllib.parse import urlparse, urlunparse, urljoin
import networkx as nx

# keep your existing read_txt_crawler(...) function
def read_txt_crawler(path: str):
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    n = int(lines[0])
    domain = lines[1]
    pages = lines[2:2 + n]
    return n, domain, pages

# ---------- Scrapy Spider ----------
class DomainSpider(scrapy.Spider):
    name = "domain_spider"
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "LOG_ENABLED": False,
        "DOWNLOAD_TIMEOUT": 10,
        "REDIRECT_ENABLED": True,
        "RETRY_ENABLED": True,
    }

    def __init__(self, start_urls, allowed_domain, max_nodes, out_gml, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = start_urls
        self.allowed_domain = allowed_domain
        self.max_nodes = max_nodes
        self.out_gml = out_gml

        self.visited = set()  # canonical URLs we’ve parsed
        self.edges = set()    # (src, dst)

    # canonicalize: strip fragments + normalize scheme/netloc/path
    def canon(self, url: str) -> str:
        p = urlparse(url)
        # strip fragment, keep query (up to you; you can also drop query)
        return urlunparse((p.scheme, p.netloc.lower(), p.path.rstrip("/") or "/", p.params, p.query, ""))

    def same_domain(self, url: str) -> bool:
        netloc = urlparse(url).netloc.lower()
        # strict match to the provided domain
        return netloc == self.allowed_domain.lower()

    def is_html(self, response) -> bool:
        ctype = response.headers.get(b"Content-Type", b"").decode("utf-8").lower()
        return "text/html" in ctype or "application/xhtml+xml" in ctype

    def parse(self, response):
        # only process HTML pages
        if not self.is_html(response):
            return

        src = self.canon(response.url)

        # already parsed?
        if src in self.visited:
            return

        self.visited.add(src)
        if len(self.visited) >= self.max_nodes:
            raise CloseSpider(reason="max_nodes_reached")

        # extract and follow same-domain links; record edges
        links = response.css("a::attr(href)").getall()
        for href in links:
            abs_url = urljoin(response.url, href)
            if not abs_url.startswith("http"):
                continue
            if not self.same_domain(abs_url):
                continue
            dst = self.canon(abs_url)
            self.edges.add((src, dst))
            # schedule new request (dont_filter to avoid duplicate filter fighting our canon set)
            if dst not in self.visited:
                yield scrapy.Request(abs_url, callback=self.parse, dont_filter=True)

    def closed(self, reason):
        # dump edges to GML
        G = nx.DiGraph()
        G.add_edges_from(self.edges)
        nx.write_gml(G, self.out_gml)
        self.logger.info(f"Wrote GML to {self.out_gml} with {G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")

# ---------- Helper to run scrapy inside your CLI ----------
def crawl_to_gml(crawler_txt: str, out_gml: str):
    n, domain, pages = read_txt_crawler(crawler_txt)

    # Ensure start URLs are absolute and within domain
    starts = []
    for u in pages:
        if not u.startswith("http"):
            u = "https://" + u.lstrip("/")
        if urlparse(u).netloc.lower() != domain.lower():
            # skip seeds outside the domain
            continue
        starts.append(u)

    if not starts:
        raise RuntimeError("No valid start URLs inside the specified domain.")

    process = CrawlerProcess()  # uses settings from DomainSpider.custom_settings
    process.crawl(DomainSpider,
                  start_urls=starts,
                  allowed_domain=domain,
                  max_nodes=n,
                  out_gml=out_gml)
    process.start()  # blocks until finished
