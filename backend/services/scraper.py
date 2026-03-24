"""Shared utility for fetching and parsing web pages."""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_page(url: str, timeout: int = 15) -> requests.Response | None:
    """Fetch a URL and return the Response, or None on error."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return resp
    except Exception:
        return None


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def normalize_url(base: str, href: str) -> str | None:
    """Resolve a relative href against a base URL, return absolute URL or None."""
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return None
    return urljoin(base, href)


def same_domain(url1: str, url2: str) -> bool:
    return urlparse(url1).netloc == urlparse(url2).netloc


def fetch_text_file(url: str) -> str | None:
    """Fetch a plain text file (robots.txt, sitemap.xml, etc.)."""
    resp = fetch_page(url)
    if resp is None:
        return None
    return resp.text
