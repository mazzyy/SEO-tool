"""
SERP Rank Tracker — services/serp.py

2-Tier real Google ranking system:
  Tier 1: Serper.dev API  (free 2,500 queries — add SERPER_API_KEY to .env)
  Tier 2: Direct Google scraping with httpx + BeautifulSoup

Returns structured JSON for the frontend dashboard with:
  - Full competitor list (all results, not just top 5)
  - Deep page analysis for top competitors (word count, headings, meta, content structure)
  - AI-powered strategic insights
"""

import os
import re
import random
import asyncio
import logging
from urllib.parse import urlparse, parse_qs
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from .ai_client import ask_ai

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# User-Agent rotation
# ---------------------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9",
    "en-US,en;q=0.9,de;q=0.8",
]


def _random_headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }


# ---------------------------------------------------------------------------
# URL matching
# ---------------------------------------------------------------------------
def _normalize_url(url: str) -> str:
    url = url.lower().strip()
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"^www\.", "", url)
    return url.rstrip("/")


def _domain_match(result_url: str, target_url: str) -> bool:
    norm_result = _normalize_url(result_url)
    norm_target = _normalize_url(target_url)

    if norm_result == norm_target or norm_result.startswith(norm_target):
        return True

    target_domain = urlparse(f"https://{norm_target}").netloc.replace("www.", "")
    result_domain = urlparse(f"https://{norm_result}").netloc.replace("www.", "")
    return bool(target_domain and target_domain == result_domain)


def _ensure_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


# ---------------------------------------------------------------------------
# Tier 1: Serper.dev API
# ---------------------------------------------------------------------------
async def _serper_search(keyword: str, num_pages: int = 10, target_url: str = "") -> Optional[list[dict]]:
    """
    Query Serper.dev API, paginating through `num_pages` Google result pages.
    If target_url is provided, stops searching once the target is found
    (but always completes the current page to get full results for that page).
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return None

    all_results = []
    position = 1
    target_found = False

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for page_num in range(1, num_pages + 1):
                resp = await client.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                    json={"q": keyword, "num": 10, "page": page_num},
                )
                resp.raise_for_status()
                data = resp.json()

                organic = data.get("organic", [])
                if not organic:
                    break

                for item in organic:
                    link = item.get("link", "")
                    all_results.append({
                        "position": item.get("position", position),
                        "title": item.get("title", ""),
                        "link": link,
                        "snippet": item.get("snippet", ""),
                    })
                    position += 1

                    # Check if we found the target URL
                    if target_url and _domain_match(link, target_url):
                        target_found = True

                logger.info(f"[Serper] Page {page_num}: {len(organic)} results for '{keyword}'")

                # Stop early if target was found on this page
                if target_found:
                    logger.info(f"[Serper] Target found on page {page_num}, stopping search early (saved {num_pages - page_num} API calls)")
                    break

                if page_num < num_pages:
                    await asyncio.sleep(0.3)

        logger.info(f"[Serper] Total: {len(all_results)} results across {page_num if all_results else 0} pages for '{keyword}'")
        return all_results if all_results else None

    except Exception as e:
        logger.warning(f"[Serper] Failed for '{keyword}': {e}")
        return all_results if all_results else None


# ---------------------------------------------------------------------------
# Tier 2: Direct Google scraping
# ---------------------------------------------------------------------------
def _extract_real_url(href: str) -> Optional[str]:
    if href.startswith("/url?"):
        parsed = parse_qs(urlparse(href).query)
        if "q" in parsed:
            return parsed["q"][0]
    if href.startswith("http") and "google.com" not in href:
        return href
    return None


def _is_captcha(html: str) -> bool:
    signals = [
        "detected unusual traffic",
        "our systems have detected",
        "/recaptcha/",
        "captcha",
        "sorry/index",
        "unusual traffic from your computer",
    ]
    html_lower = html.lower()
    return any(s in html_lower for s in signals)


async def _google_scrape(keyword: str, num_pages: int = 10, target_url: str = "") -> Optional[list[dict]]:
    """
    Direct Google scraping fallback.
    If target_url is provided, stops after the page where the target is found.
    """
    all_results = []
    position = 1
    target_found = False

    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for page in range(num_pages):
            start = page * 10

            if page > 0:
                await asyncio.sleep(random.uniform(1.5, 3.5))

            params = {
                "q": keyword,
                "start": str(start),
                "num": "10",
                "hl": "en",
                "gl": "us",
            }

            try:
                resp = await client.get(
                    "https://www.google.com/search",
                    params=params,
                    headers=_random_headers(),
                )

                if resp.status_code == 429:
                    logger.warning(f"[Scrape] Rate limited on page {page + 1}")
                    break

                html = resp.text

                if _is_captcha(html):
                    logger.warning(f"[Scrape] CAPTCHA detected on page {page + 1}")
                    if page == 0:
                        return None
                    break

                soup = BeautifulSoup(html, "lxml")
                result_divs = soup.select("div.g")
                if not result_divs and page == 0:
                    result_divs = soup.select("div[data-sokoban-container]")

                page_count = 0
                for div in result_divs:
                    a_tag = div.select_one("a[href]")
                    if not a_tag:
                        continue

                    href = a_tag.get("href", "")
                    link = _extract_real_url(href)
                    if not link:
                        if href.startswith("http") and "google.com" not in href:
                            link = href
                        else:
                            continue

                    title_tag = a_tag.select_one("h3")
                    title = title_tag.get_text(strip=True) if title_tag else ""

                    snippet = ""
                    for sel in [
                        "div[data-sncf]", "div.VwiC3b", "span.aCOpRe",
                        "div[style='-webkit-line-clamp:2']",
                    ]:
                        snip_el = div.select_one(sel)
                        if snip_el:
                            snippet = snip_el.get_text(strip=True)
                            break

                    if not snippet:
                        all_text = div.get_text(" ", strip=True)
                        if title and title in all_text:
                            snippet = all_text.replace(title, "").strip()[:200]

                    all_results.append({
                        "position": position,
                        "title": title,
                        "link": link,
                        "snippet": snippet[:300],
                    })
                    position += 1
                    page_count += 1

                    # Check if we found the target
                    if target_url and _domain_match(link, target_url):
                        target_found = True

                logger.info(f"[Scrape] Page {page + 1}: {page_count} results")

                # Stop early if target found
                if target_found:
                    logger.info(f"[Scrape] Target found on page {page + 1}, stopping early")
                    break

                if page_count == 0:
                    break

            except Exception as e:
                logger.warning(f"[Scrape] Error on page {page + 1}: {e}")
                if page == 0:
                    return None
                break

    return all_results if all_results else None


# ---------------------------------------------------------------------------
# Deep competitor page analysis
# ---------------------------------------------------------------------------
async def _analyze_competitor_page(url: str) -> dict:
    """
    Fetch a competitor page and extract SEO-relevant signals:
    word count, headings structure, meta tags, content type, schema markup, etc.
    """
    result = {
        "url": url,
        "domain": urlparse(url).netloc.replace("www.", ""),
        "analyzed": False,
        "word_count": 0,
        "headings": {"h1": [], "h2": [], "h3": []},
        "meta_title": "",
        "meta_description": "",
        "meta_keywords": "",
        "has_schema_markup": False,
        "schema_types": [],
        "internal_links": 0,
        "external_links": 0,
        "images": 0,
        "images_without_alt": 0,
        "has_canonical": False,
        "canonical_url": "",
        "content_type": "unknown",
        "has_og_tags": False,
        "has_twitter_cards": False,
        "page_title_length": 0,
        "meta_desc_length": 0,
        "error": None,
    }

    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
            resp = await client.get(url, headers=_random_headers())
            if resp.status_code != 200:
                result["error"] = f"HTTP {resp.status_code}"
                return result

            html = resp.text
            soup = BeautifulSoup(html, "lxml")
            result["analyzed"] = True

            # --- Word count ---
            body = soup.find("body")
            if body:
                # Remove script/style tags
                for tag in body.find_all(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                text = body.get_text(" ", strip=True)
                words = text.split()
                result["word_count"] = len(words)

            # --- Headings ---
            for level in ["h1", "h2", "h3"]:
                tags = soup.find_all(level)
                result["headings"][level] = [t.get_text(strip=True)[:120] for t in tags[:10]]

            # --- Meta tags ---
            title_tag = soup.find("title")
            if title_tag:
                result["meta_title"] = title_tag.get_text(strip=True)[:200]
                result["page_title_length"] = len(result["meta_title"])

            meta_desc = soup.find("meta", attrs={"name": re.compile(r"description", re.I)})
            if meta_desc:
                result["meta_description"] = (meta_desc.get("content", "") or "")[:300]
                result["meta_desc_length"] = len(result["meta_description"])

            meta_kw = soup.find("meta", attrs={"name": re.compile(r"keywords", re.I)})
            if meta_kw:
                result["meta_keywords"] = (meta_kw.get("content", "") or "")[:300]

            # --- Canonical ---
            canonical = soup.find("link", attrs={"rel": "canonical"})
            if canonical:
                result["has_canonical"] = True
                result["canonical_url"] = (canonical.get("href", "") or "")[:200]

            # --- Open Graph / Twitter Cards ---
            if soup.find("meta", attrs={"property": re.compile(r"^og:", re.I)}):
                result["has_og_tags"] = True
            if soup.find("meta", attrs={"name": re.compile(r"^twitter:", re.I)}):
                result["has_twitter_cards"] = True

            # --- Schema Markup ---
            schema_scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
            if schema_scripts:
                result["has_schema_markup"] = True
                for script in schema_scripts[:5]:
                    try:
                        import json
                        data = json.loads(script.string or "")
                        if isinstance(data, dict) and "@type" in data:
                            result["schema_types"].append(data["@type"])
                        elif isinstance(data, list):
                            for item in data[:3]:
                                if isinstance(item, dict) and "@type" in item:
                                    result["schema_types"].append(item["@type"])
                    except Exception:
                        pass

            # --- Links ---
            domain = urlparse(url).netloc
            all_links = soup.find_all("a", href=True)
            for a in all_links:
                href = a.get("href", "")
                if href.startswith(("http://", "https://")):
                    link_domain = urlparse(href).netloc
                    if link_domain == domain or link_domain == f"www.{domain}":
                        result["internal_links"] += 1
                    else:
                        result["external_links"] += 1
                elif href.startswith("/"):
                    result["internal_links"] += 1

            # --- Images ---
            images = soup.find_all("img")
            result["images"] = len(images)
            result["images_without_alt"] = sum(1 for img in images if not img.get("alt"))

            # --- Content type detection ---
            if result["word_count"] > 2000:
                result["content_type"] = "long-form article"
            elif result["word_count"] > 800:
                result["content_type"] = "standard article"
            elif result["word_count"] > 300:
                result["content_type"] = "short content/landing page"
            else:
                result["content_type"] = "thin content/tool page"

            if soup.find("table"):
                result["content_type"] += " + data tables"
            if soup.find(["ul", "ol"], class_=re.compile(r"faq|question|accordion", re.I)) or \
               soup.find(attrs={"class": re.compile(r"faq|question|accordion", re.I)}):
                result["content_type"] += " + FAQ"

    except Exception as e:
        result["error"] = str(e)[:200]

    return result


# ---------------------------------------------------------------------------
# Main: analyze(url, keywords, max_pages) -> dict (structured JSON)
# ---------------------------------------------------------------------------
async def analyze(url: str, keywords: list[str], max_pages: int = 10) -> dict:
    url = _ensure_url(url)
    keywords = [k.strip() for k in keywords if k.strip()]

    if not keywords:
        return {
            "visibility_score": 0,
            "keywords": [],
            "all_results": [],
            "competitor_analysis": [],
            "quick_wins": ["Add target keywords to track"],
            "summary": "No keywords provided.",
            "data_source": "none",
        }

    keyword_data = []
    all_serp_results = {}  # keyword -> full list of results
    data_source = "unknown"

    for i, keyword in enumerate(keywords):
        if i > 0:
            await asyncio.sleep(random.uniform(0.5, 1.5))

        search_results = None
        source = None

        # Tier 1: Serper.dev (stops early if target found)
        search_results = await _serper_search(keyword, num_pages=max_pages, target_url=url)
        if search_results:
            source = "serper_api"
        else:
            # Tier 2: Direct scraping (stops early if target found)
            search_results = await _google_scrape(keyword, num_pages=max_pages, target_url=url)
            if search_results:
                source = "google_scrape"

        if not search_results:
            keyword_data.append({
                "keyword": keyword,
                "found": False,
                "rank": -1,
                "page": None,
                "snippet": "",
                "total_scanned": 0,
                "competing_urls": [],
                "all_competitors": [],
                "source": "none",
                "captcha": True,
            })
            continue

        data_source = source
        all_serp_results[keyword] = search_results

        # Find target in results
        found_pos = None
        matched_url = None
        matched_snippet = ""
        for r in search_results:
            if _domain_match(r["link"], url):
                found_pos = r["position"]
                matched_url = r["link"]
                matched_snippet = r.get("snippet", "")
                break

        # ALL competitors (not just top 5)
        all_competitors = []
        competing_urls = []
        for r in search_results:
            if not _domain_match(r["link"], url):
                comp_entry = {
                    "position": r["position"],
                    "title": r["title"],
                    "url": r["link"],
                    "domain": urlparse(r["link"]).netloc.replace("www.", ""),
                    "snippet": r["snippet"],
                    "page": ((r["position"] - 1) // 10) + 1,
                }
                all_competitors.append(comp_entry)
                competing_urls.append(r["link"])

        keyword_data.append({
            "keyword": keyword,
            "found": found_pos is not None,
            "rank": found_pos if found_pos else -1,
            "page": ((found_pos - 1) // 10) + 1 if found_pos else None,
            "snippet": matched_snippet,
            "url_matched": matched_url,
            "total_scanned": len(search_results),
            "competing_urls": competing_urls[:10],  # top 10 URLs for the card
            "all_competitors": all_competitors,  # ALL competitors with full details
            "source": source,
            "captcha": False,
        })

    # ── Visibility Score ──
    total_kw = len(keyword_data)
    if total_kw == 0:
        visibility = 0
    else:
        score = 0
        for r in keyword_data:
            if r["found"] and r["rank"] and r["rank"] > 0:
                pos = r["rank"]
                if pos == 1:
                    score += 100
                elif pos <= 3:
                    score += 80
                elif pos <= 5:
                    score += 60
                elif pos <= 10:
                    score += 40
                elif pos <= 20:
                    score += 20
                elif pos <= 50:
                    score += 5
        visibility = round(score / total_kw, 1)

    # ── Deep competitor analysis (top 5 unique domains across all keywords) ──
    seen_domains = set()
    top_competitor_urls = []
    for kd in keyword_data:
        for comp in kd.get("all_competitors", []):
            domain = comp["domain"]
            if domain not in seen_domains and len(top_competitor_urls) < 5:
                seen_domains.add(domain)
                top_competitor_urls.append(comp["url"])

    # Fetch and analyze top competitor pages concurrently
    competitor_analysis = []
    if top_competitor_urls:
        tasks = [_analyze_competitor_page(comp_url) for comp_url in top_competitor_urls]
        competitor_analysis = await asyncio.gather(*tasks, return_exceptions=False)
        competitor_analysis = [
            ca if isinstance(ca, dict) else {"url": top_competitor_urls[i], "analyzed": False, "error": str(ca)}
            for i, ca in enumerate(competitor_analysis)
        ]

    # ── Generate Quick Wins ──
    quick_wins = []
    for kr in keyword_data:
        if kr.get("captcha"):
            continue
        kw = kr["keyword"]
        if kr["found"]:
            pos = kr["rank"]
            if pos == 1:
                quick_wins.append(f'"{kw}" is #1 — Maintain with fresh content updates and backlink building')
            elif pos <= 3:
                quick_wins.append(f'"{kw}" is #{pos} — Close to #1! Optimize title tag, add internal links, and improve content depth')
            elif pos <= 10:
                quick_wins.append(f'"{kw}" is #{pos} on Page 1 — Improve content comprehensiveness, earn more backlinks, optimize meta description for CTR')
            elif pos <= 20:
                quick_wins.append(f'"{kw}" is #{pos} (Page 2) — Quick win! Strengthen on-page SEO, add FAQ section, build topic authority')
            else:
                quick_wins.append(f'"{kw}" is #{pos} — Needs significant content depth improvement and authority building')
        else:
            quick_wins.append(f'"{kw}" — Not ranking. Create a comprehensive, targeted article (2000+ words) optimized for this keyword')

    # ── AI Enhancement ──
    # Build a text summary for AI to analyze
    text_report = f"Target: {url}\nVisibility: {visibility}/100\n"
    for kd in keyword_data:
        text_report += f"\nKeyword: {kd['keyword']}"
        if kd["found"]:
            text_report += f" — Rank #{kd['rank']} (Page {kd['page']})"
        else:
            text_report += f" — Not found in top {kd['total_scanned']} results"
        if kd.get("all_competitors"):
            text_report += "\nTop competitors:\n"
            for comp in kd["all_competitors"][:5]:
                text_report += f"  #{comp['position']} {comp['url']} — {comp['title']}\n"

    if competitor_analysis:
        text_report += "\n\nCompetitor Page Analysis:\n"
        for ca in competitor_analysis:
            if ca.get("analyzed"):
                text_report += f"\n{ca['domain']}:"
                text_report += f"\n  Word count: {ca['word_count']}"
                text_report += f"\n  Content type: {ca['content_type']}"
                text_report += f"\n  H1: {', '.join(ca['headings']['h1'][:3])}"
                text_report += f"\n  Schema: {', '.join(ca['schema_types']) if ca['schema_types'] else 'None'}"
                text_report += f"\n  Meta title: {ca['meta_title'][:80]}"

    ai_summary = await ask_ai(
        "You are an expert SEO consultant. Analyze the SERP ranking data and competitor page analysis. Provide:\n"
        "1) A concise summary of the site's search visibility (2-3 sentences)\n"
        "2) Top 3-5 specific, actionable recommendations to outrank competitors\n"
        "3) What the top-ranking pages are doing well that the target site should emulate\n"
        "Reference actual positions, keywords, competitor content strategies. Keep it under 350 words.\n"
        "Do NOT use markdown headers or bullet points — write in flowing paragraphs.",
        text_report,
    )

    return {
        "visibility_score": visibility,
        "keywords": keyword_data,
        "competitor_analysis": [ca for ca in competitor_analysis if isinstance(ca, dict)],
        "quick_wins": quick_wins,
        "summary": ai_summary or f"Your site has a visibility score of {visibility}/100. {sum(1 for k in keyword_data if k['found'])}/{total_kw} keywords are ranking.",
        "data_source": data_source,
        "total_results_scanned": sum(kd["total_scanned"] for kd in keyword_data),
        "pages_searched": max_pages,
    }
