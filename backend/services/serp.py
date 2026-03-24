"""
SERP Rank Tracker — services/serp.py

2-Tier real Google ranking system:
  Tier 1: Serper.dev API  (free 2,500 queries — add SERPER_API_KEY to .env)
  Tier 2: Direct Google scraping with httpx + BeautifulSoup
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
async def _serper_search(keyword: str, num_results: int = 100) -> Optional[list[dict]]:
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json={"q": keyword, "num": min(num_results, 100)},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for i, item in enumerate(data.get("organic", []), start=1):
            results.append({
                "position": item.get("position", i),
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })
        logger.info(f"[Serper] Got {len(results)} results for '{keyword}'")
        return results

    except Exception as e:
        logger.warning(f"[Serper] Failed for '{keyword}': {e}")
        return None


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


async def _google_scrape(keyword: str, num_pages: int = 5) -> Optional[list[dict]]:
    all_results = []
    position = 1

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

                logger.info(f"[Scrape] Page {page + 1}: {page_count} results")
                if page_count == 0:
                    break

            except Exception as e:
                logger.warning(f"[Scrape] Error on page {page + 1}: {e}")
                if page == 0:
                    return None
                break

    return all_results if all_results else None


# ---------------------------------------------------------------------------
# Main: analyze(url, keywords, max_pages) -> str
# ---------------------------------------------------------------------------
async def analyze(url: str, keywords: list[str], max_pages: int = 5) -> str:
    url = _ensure_url(url)
    keywords = [k.strip() for k in keywords if k.strip()]

    if not keywords:
        return "❌ No keywords provided."

    keyword_results = []
    data_source = "unknown"

    for i, keyword in enumerate(keywords):
        if i > 0:
            await asyncio.sleep(random.uniform(0.5, 1.5))

        search_results = None
        source = None

        # Tier 1: Serper.dev
        search_results = await _serper_search(keyword, num_results=max_pages * 10)
        if search_results:
            source = "serper_api"
        else:
            # Tier 2: Direct scraping
            search_results = await _google_scrape(keyword, num_pages=max_pages)
            if search_results:
                source = "google_scrape"

        if not search_results:
            keyword_results.append({
                "keyword": keyword,
                "found": False,
                "position": None,
                "page": None,
                "url_matched": None,
                "total_scanned": 0,
                "top_competitors": [],
                "source": "none",
                "captcha": True,
            })
            continue

        data_source = source

        # Find target in results
        found_pos = None
        matched_url = None
        for r in search_results:
            if _domain_match(r["link"], url):
                found_pos = r["position"]
                matched_url = r["link"]
                break

        # Top competitors
        competitors = []
        for r in search_results[:10]:
            if not _domain_match(r["link"], url):
                competitors.append({
                    "position": r["position"],
                    "title": r["title"],
                    "url": r["link"],
                    "snippet": r["snippet"],
                })

        keyword_results.append({
            "keyword": keyword,
            "found": found_pos is not None,
            "position": found_pos,
            "page": ((found_pos - 1) // 10) + 1 if found_pos else None,
            "url_matched": matched_url,
            "total_scanned": len(search_results),
            "top_competitors": competitors[:5],
            "source": source,
            "captcha": False,
        })

    # ── Visibility Score ──
    total_kw = len(keyword_results)
    if total_kw == 0:
        visibility = 0
    else:
        score = 0
        for r in keyword_results:
            if r["found"] and r["position"]:
                pos = r["position"]
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

    # ── Format Report ──
    lines = []
    lines.append(f"🎯 Target: {url}")
    lines.append(f"📊 Visibility Score: {visibility}/100")
    lines.append(f"🔑 Keywords Ranking: {sum(1 for r in keyword_results if r['found'])}/{total_kw}")
    lines.append(f"📡 Data Source: {data_source}")
    lines.append("")
    lines.append("=" * 60)

    for kr in keyword_results:
        kw = kr["keyword"]
        lines.append("")
        lines.append(f"🔎 Keyword: \"{kw}\"")

        if kr["captcha"]:
            lines.append("   ⚠️  Could not fetch Google results.")
            lines.append("   💡 Add SERPER_API_KEY to .env for reliable results (free 2,500 queries at serper.dev)")
            continue

        if kr["found"]:
            pos = kr["position"]
            page = kr["page"]
            matched = kr["url_matched"]
            emoji = "🥇" if pos == 1 else "🥈" if pos == 2 else "🥉" if pos == 3 else "📍"
            lines.append(f"   {emoji} Position #{pos} (Page {page})")
            lines.append(f"   🔗 Matched: {matched}")
        else:
            scanned = kr["total_scanned"]
            lines.append(f"   ❌ Not found in top {scanned} results")

        if kr["top_competitors"]:
            lines.append("   👥 Top Competitors:")
            for comp in kr["top_competitors"][:3]:
                lines.append(f"      #{comp['position']} {comp['url']}")
                if comp["title"]:
                    lines.append(f"         {comp['title']}")

    lines.append("")
    lines.append("=" * 60)
    lines.append("")
    lines.append("💡 Quick Insights:")

    for kr in keyword_results:
        if kr["captcha"]:
            continue
        kw = kr["keyword"]
        if kr["found"]:
            pos = kr["position"]
            if pos == 1:
                lines.append(f"   ✅ \"{kw}\": #1 — Maintain with fresh content & backlinks")
            elif pos <= 3:
                lines.append(f"   🔥 \"{kw}\": #{pos} — Close to #1! Optimize title/meta, add internal links")
            elif pos <= 10:
                lines.append(f"   📈 \"{kw}\": #{pos} — Page 1. Improve content depth & earn backlinks")
            elif pos <= 20:
                lines.append(f"   ⚡ \"{kw}\": #{pos} — Page 2. Quick win — improve on-page SEO to break into page 1")
            else:
                lines.append(f"   🔧 \"{kw}\": #{pos} — Needs significant content & authority building")
        else:
            lines.append(f"   🚀 \"{kw}\": Not ranking — Create targeted content for this keyword")

    report = "\n".join(lines)

    # ── AI Enhancement (uses shared ai_client) ──
    ai_insights = await ask_ai(
        "You are an SEO consultant. Analyze the SERP ranking data and provide:\n"
        "1) A brief summary of the site's search visibility\n"
        "2) Top 3-5 prioritized quick wins to improve rankings\n"
        "Be specific, reference actual positions/keywords. Keep it under 250 words.",
        report,
    )
    if ai_insights:
        report += "\n\n" + "=" * 60
        report += "\n🤖 AI Strategic Insights:\n" + "=" * 60 + "\n"
        report += ai_insights

    return report
