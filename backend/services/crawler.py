"""Site Crawler — Fully programmatic BFS crawler, AI only for summary."""

import asyncio
from collections import deque
from urllib.parse import urlparse, urljoin
from .scraper import fetch_page, fetch_text_file, parse_html, same_domain, normalize_url, HEADERS
from .ai_client import ask_ai
import requests


async def _crawl_site(start_url: str, max_depth: int = 3, max_pages: int = 50) -> dict:
    """BFS crawl the site, returning discovered pages and link data."""
    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc

    visited = {}  # url -> {status, title, depth, links_out, word_count}
    broken_links = []
    redirect_chains = []
    queue = deque([(start_url, 0)])  # (url, depth)
    seen = {start_url}

    def _process_page(url, depth):
        page_data = {"url": url, "depth": depth}
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
            page_data["status"] = resp.status_code

            # Check for redirects
            if resp.history:
                redirect_chains.append({
                    "from": url,
                    "to": resp.url,
                    "hops": len(resp.history),
                })

            if resp.status_code >= 400:
                broken_links.append({"url": url, "status": resp.status_code, "depth": depth})
                return page_data, []

            if "text/html" not in resp.headers.get("content-type", ""):
                return page_data, []

            soup = parse_html(resp.text)
            title_tag = soup.find("title")
            page_data["title"] = title_tag.get_text(strip=True)[:80] if title_tag else "(no title)"

            # Word count
            text = soup.get_text(separator=" ", strip=True)
            page_data["word_count"] = len(text.split())

            # Extract links for further crawling
            child_urls = []
            for a_tag in soup.find_all("a", href=True):
                href = normalize_url(url, a_tag["href"])
                if href and same_domain(start_url, href):
                    # Strip fragment and query for dedup while crawling
                    clean = urlparse(href)._replace(fragment="", query="").geturl()
                    child_urls.append(clean)

            page_data["links_out"] = len(child_urls)
            return page_data, child_urls

        except Exception as e:
            page_data["status"] = "Error"
            page_data["error"] = str(e)[:80]
            return page_data, []

    while queue and len(visited) < max_pages:
        url, depth = queue.popleft()
        if depth > max_depth:
            continue

        page_data, child_urls = await asyncio.to_thread(_process_page, url, depth)
        visited[url] = page_data

        if depth < max_depth:
            for child in child_urls:
                if child not in seen and len(seen) < max_pages * 2:
                    seen.add(child)
                    queue.append((child, depth + 1))

    return {
        "pages": list(visited.values()),
        "broken_links": broken_links,
        "redirect_chains": redirect_chains,
        "total_discovered": len(seen),
        "total_crawled": len(visited),
    }


def _analyze_robots_txt(url: str) -> str:
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    text = fetch_text_file(robots_url)
    if text is None:
        return "robots.txt: ❌ Not found"
    lines = [
        "robots.txt: ✅ Found",
        f"  URL: {robots_url}",
        f"  Sitemap referenced: {'✅' if 'sitemap' in text.lower() else '❌ No'}",
        f"  Disallow rules: {text.lower().count('disallow')}",
        f"  Content preview:\n    {text[:300]}",
    ]
    return "\n".join(lines)


def _analyze_sitemap(url: str) -> str:
    parsed = urlparse(url)
    sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
    text = fetch_text_file(sitemap_url)
    if text is None:
        return "sitemap.xml: ❌ Not found"
    url_count = text.count("<loc>")
    has_lastmod = "<lastmod>" in text
    lines = [
        "sitemap.xml: ✅ Found",
        f"  URL: {sitemap_url}",
        f"  URLs listed: {url_count}",
        f"  Has lastmod dates: {'✅' if has_lastmod else '❌'}",
        f"  Has priority: {'✅' if '<priority>' in text else '❌'}",
    ]
    return "\n".join(lines)


def _format_crawl_results(url: str, crawl_data: dict, robots_info: str, sitemap_info: str) -> str:
    pages = crawl_data["pages"]
    lines = [f"SITE CRAWL REPORT — {url}", "=" * 60]

    lines.append(f"\n### CRAWL SUMMARY")
    lines.append(f"  Total URLs discovered: {crawl_data['total_discovered']}")
    lines.append(f"  Pages crawled: {crawl_data['total_crawled']}")
    lines.append(f"  Broken links found: {len(crawl_data['broken_links'])}")
    lines.append(f"  Redirect chains: {len(crawl_data['redirect_chains'])}")

    # Depth distribution
    depth_dist = {}
    for p in pages:
        d = p.get("depth", 0)
        depth_dist[d] = depth_dist.get(d, 0) + 1
    lines.append(f"\n  DEPTH DISTRIBUTION:")
    for d in sorted(depth_dist):
        lines.append(f"    Level {d}: {depth_dist[d]} pages")

    # Page inventory
    lines.append(f"\n### PAGE INVENTORY")
    for p in pages[:30]:
        status_emoji = "✅" if p.get("status") == 200 else "⚠️" if p.get("status", 0) < 400 else "❌"
        title = p.get("title", "N/A")
        wc = p.get("word_count", "?")
        lines.append(f"  {status_emoji} [{p.get('status', '?')}] {p['url'][:70]}")
        lines.append(f"       Title: {title} | Words: {wc} | Depth: {p['depth']} | Links: {p.get('links_out', 0)}")

    # Broken links
    if crawl_data["broken_links"]:
        lines.append(f"\n### BROKEN LINKS")
        for bl in crawl_data["broken_links"]:
            lines.append(f"  ❌ [{bl['status']}] {bl['url']}")

    # Redirects
    if crawl_data["redirect_chains"]:
        lines.append(f"\n### REDIRECT CHAINS")
        for rc in crawl_data["redirect_chains"][:10]:
            lines.append(f"  🔄 {rc['from'][:50]} → {rc['to'][:50]} ({rc['hops']} hops)")

    # Deep pages (3+ clicks)
    deep_pages = [p for p in pages if p.get("depth", 0) >= 3]
    if deep_pages:
        lines.append(f"\n### ⚠️ DEEP PAGES (3+ levels)")
        for p in deep_pages[:10]:
            lines.append(f"  Level {p['depth']}: {p['url'][:70]}")

    lines.append(f"\n### ROBOTS.TXT")
    lines.append(robots_info)

    lines.append(f"\n### SITEMAP")
    lines.append(sitemap_info)

    return "\n".join(lines)


SYSTEM_PROMPT = """You are a site architecture analyst. Given crawl data, provide:
1. Architecture assessment (navigation depth, orphan pages, link equity)
2. Top 5 structural issues found
3. Prioritized recommendations for improving site crawlability and SEO
Keep it concise and actionable. Reference actual data."""


async def crawl(url: str, depth: int = 3) -> str:
    max_depth = min(depth, 5)

    crawl_data = await _crawl_site(url, max_depth=max_depth, max_pages=50)
    robots_info = await asyncio.to_thread(_analyze_robots_txt, url)
    sitemap_info = await asyncio.to_thread(_analyze_sitemap, url)

    report = _format_crawl_results(url, crawl_data, robots_info, sitemap_info)

    # AI summary only if we have enough data
    if crawl_data["total_crawled"] >= 3:
        try:
            ai_summary = await ask_ai(
                SYSTEM_PROMPT,
                f"Crawl report:\n\n{report}\n\nProvide architecture assessment and recommendations.",
                1500,
            )
            return report + "\n\n" + "─" * 60 + "\nAI ARCHITECTURE ANALYSIS\n" + "─" * 60 + "\n\n" + ai_summary
        except Exception:
            pass

    return report
