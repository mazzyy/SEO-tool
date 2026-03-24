"""SERP Rank Tracker -- Real Google results via Custom Search API or Playwright stealth scraping.

Strategy (tried in order):
1. Google Custom Search JSON API (free 100 queries/day, most reliable)
2. Playwright stealth headless browser (free, no limit, but Google may CAPTCHA)
3. AI estimation fallback (always works, but not real data)
"""

import asyncio
import json
import logging
import os
import random
from urllib.parse import urlparse, quote_plus

import httpx
from .ai_client import ask_ai_json

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# TIER 1 — Google Custom Search JSON API  (most reliable, free 100/day)
# ═══════════════════════════════════════════════════════════════════════
# To enable:  set GOOGLE_API_KEY  and  GOOGLE_CSE_ID  in .env
# Create at:  https://programmablesearchengine.google.com
#             https://console.cloud.google.com/apis/credentials

async def _google_api_search(keyword: str, num: int = 10) -> list[dict] | None:
    """Use the official Google Custom Search JSON API. Returns None if not configured."""
    api_key = os.getenv("GOOGLE_API_KEY")
    cse_id = os.getenv("GOOGLE_CSE_ID")
    if not api_key or not cse_id:
        return None  # not configured → skip this tier

    url = (
        f"https://www.googleapis.com/customsearch/v1"
        f"?key={api_key}&cx={cse_id}&q={quote_plus(keyword)}&num={min(num, 10)}"
    )
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url)
        if r.status_code != 200:
            logger.warning("Google API HTTP %d for '%s'", r.status_code, keyword)
            return None
        data = r.json()
        return [
            {
                "url": item.get("link", ""),
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in data.get("items", [])
        ]
    except Exception as exc:
        logger.warning("Google API error for '%s': %s", keyword, exc)
        return None


# ═══════════════════════════════════════════════════════════════════════
# TIER 2 — Playwright stealth headless browser  (free, unlimited)
# ═══════════════════════════════════════════════════════════════════════

# Realistic user-agent pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# CAPTCHA / block indicators
CAPTCHA_INDICATORS = ["/sorry/", "detected unusual traffic", "captcha", "recaptcha",
                      "our systems have detected", "automated queries"]

# JS snippet that extracts organic results from Google SERP
_EXTRACT_JS = """() => {
    const results = [];
    // Strategy 1: h3 inside an <a> tag (modern Google)
    document.querySelectorAll('a h3').forEach(h3 => {
        const a = h3.closest('a');
        if (a && a.href && a.href.startsWith('http') && !a.href.includes('google.com')) {
            results.push({ url: a.href, title: h3.innerText, snippet: '' });
        }
    });
    // Strategy 2: div.g with nested link (classic Google)
    if (results.length === 0) {
        document.querySelectorAll('div.g').forEach(div => {
            const a = div.querySelector('a[href]');
            const h3 = div.querySelector('h3');
            if (a && a.href.startsWith('http') && !a.href.includes('google.com')) {
                results.push({
                    url: a.href,
                    title: h3 ? h3.innerText : '',
                    snippet: ''
                });
            }
        });
    }
    // Strategy 3: any <a data-ved> with h3 (fallback)
    if (results.length === 0) {
        document.querySelectorAll('a[data-ved]').forEach(a => {
            const h3 = a.querySelector('h3');
            if (h3 && a.href.startsWith('http') && !a.href.includes('google.com')) {
                results.push({ url: a.href, title: h3.innerText, snippet: '' });
            }
        });
    }
    // Deduplicate by URL
    const seen = new Set();
    return results.filter(r => {
        if (seen.has(r.url)) return false;
        seen.add(r.url);
        return true;
    });
}"""


async def _playwright_search(keyword: str, max_pages: int = 1) -> dict:
    """Scrape Google with Playwright stealth browser.

    Returns:
        {"results": [...], "captcha": False}  on success
        {"results": [],    "captcha": True}   if CAPTCHA detected
    """
    try:
        from playwright.async_api import async_playwright
        from playwright_stealth import Stealth
    except ImportError:
        logger.warning("Playwright not installed — skipping browser scrape.")
        return {"results": [], "captcha": False, "error": "playwright_not_installed"}

    num_results = max_pages * 10
    search_url = (
        f"https://www.google.com/search?q={quote_plus(keyword)}"
        f"&num={num_results}&hl=en"
    )

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
            )
            ctx = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                locale="en-US",
                viewport={"width": 1280, "height": 800},
            )
            stealth = Stealth()
            page = await ctx.new_page()
            await stealth.apply_stealth_async(page)

            await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(3000)

            # Handle cookie consent popups
            for btn_text in ["Accept all", "Reject all", "I agree", "Accept"]:
                try:
                    btn = page.locator(f'button:has-text("{btn_text}")')
                    if await btn.count() > 0:
                        await btn.first.click()
                        await page.wait_for_timeout(2000)
                        break
                except Exception:
                    pass

            # Check for CAPTCHA block
            current_url = page.url
            page_content = await page.content()
            is_captcha = any(
                ind in current_url.lower() or ind in page_content.lower()
                for ind in CAPTCHA_INDICATORS
            )

            if is_captcha:
                await browser.close()
                return {"results": [], "captcha": True}

            # Extract organic results
            results = await page.evaluate(_EXTRACT_JS)
            await browser.close()
            return {"results": results, "captcha": False}

    except Exception as exc:
        logger.warning("Playwright error for '%s': %s", keyword, exc)
        return {"results": [], "captcha": False, "error": str(exc)}


# ═══════════════════════════════════════════════════════════════════════
# TIER 3 — AI Estimation Fallback
# ═══════════════════════════════════════════════════════════════════════

AI_FALLBACK_PROMPT = """You are an SEO SERP rank analysis tool. You MUST respond with valid JSON only.

Given a target URL and keywords, estimate where the target URL ranks on Google.

Return this exact JSON structure (no markdown, no code fences, pure JSON):
{
  "keywords": [
    {
      "keyword": "the keyword",
      "rank": 12,
      "page": 2,
      "found": true,
      "snippet": "Title or snippet of the ranking result",
      "competing_urls": ["url1", "url2", "url3"]
    }
  ],
  "visibility_score": 65,
  "quick_wins": ["Actionable suggestion 1", "Actionable suggestion 2"],
  "summary": "Overall analysis paragraph here."
}

Rules:
- If found, rank is the numeric position (1-based).
- If not found, rank should be -1 and found should be false.
- visibility_score is 0-100 based on how many keywords rank well.
- quick_wins should contain 2-5 actionable improvement suggestions.
- competing_urls should list 3-5 URLs that outrank the target for that keyword."""


async def _ai_fallback(url: str, keywords: list[str], max_pages: int) -> dict:
    """Full AI estimation when both API and scraping fail."""
    kw_list = ", ".join(f'"{k}"' for k in keywords)
    user_msg = (
        f"Target URL: {url}\n"
        f"Keywords to check: {kw_list}\n"
        f"Maximum Google pages to search: {max_pages} (top {max_pages * 10} results)\n\n"
        "Provide your best estimation based on your knowledge."
    )
    try:
        raw = await asyncio.to_thread(ask_ai_json, AI_FALLBACK_PROMPT, user_msg)
        result = json.loads(raw)
        for kw in result.get("keywords", []):
            kw["data_source"] = "ai_estimation"
        result["data_source"] = "ai_estimation"
        result["captcha_detected"] = True
        result["captcha_message"] = (
            "⚠️ Google temporarily blocked automated searches from this server. "
            "The ranking data shown is an AI estimation, not live Google data. "
            "To get real results, configure a Google Custom Search API key in your .env file "
            "(GOOGLE_API_KEY and GOOGLE_CSE_ID). It's free for 100 queries/day. "
            "See: https://programmablesearchengine.google.com"
        )
        return result
    except Exception:
        return {
            "keywords": [],
            "visibility_score": 0,
            "quick_wins": [],
            "summary": "Both Google scraping and AI analysis failed. Please try again later.",
            "captcha_detected": True,
            "data_source": "error",
        }


# ═══════════════════════════════════════════════════════════════════════
# AI Analysis — generate insights from REAL data
# ═══════════════════════════════════════════════════════════════════════

AI_ANALYSIS_PROMPT = """You are an SEO analyst. Given real Google SERP ranking data for a target URL,
generate actionable insights. Respond with valid JSON only (no markdown, no code fences).

{
  "quick_wins": ["Actionable suggestion 1", "Actionable suggestion 2", ...],
  "summary": "Overall analysis paragraph."
}

Rules:
- quick_wins: 2-5 specific, actionable SEO improvement suggestions based on the data.
- summary: a concise paragraph summarizing the ranking performance."""


async def _generate_ai_analysis(target_url: str, keyword_results: list[dict]) -> dict:
    """Use AI to generate insights from real ranking data."""
    data_text = json.dumps({"target_url": target_url, "results": keyword_results}, indent=2)
    user_msg = f"Here is the real Google SERP data:\n\n{data_text}\n\nProvide your analysis."
    try:
        raw = await asyncio.to_thread(ask_ai_json, AI_ANALYSIS_PROMPT, user_msg)
        analysis = json.loads(raw)
        return {
            "quick_wins": analysis.get("quick_wins", []),
            "summary": analysis.get("summary", ""),
        }
    except Exception as exc:
        logger.warning("AI analysis failed: %s", exc)
        return {"quick_wins": [], "summary": "AI analysis unavailable."}


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def _domain_match(url1: str, url2: str) -> bool:
    """Check if two URLs share the same root domain."""
    try:
        d1 = urlparse(url1).netloc.replace("www.", "").lower()
        d2 = urlparse(url2).netloc.replace("www.", "").lower()
        return d1 and d2 and d1 == d2
    except Exception:
        return False


def _find_rank(results: list[dict], target_url: str) -> dict:
    """Find the target URL's position in a list of search results."""
    competing = []
    for idx, r in enumerate(results, start=1):
        if _domain_match(r["url"], target_url) or target_url.rstrip("/") in r["url"]:
            return {
                "rank": idx,
                "page": (idx - 1) // 10 + 1,
                "found": True,
                "snippet": r.get("title", "") or r.get("snippet", ""),
                "competing_urls": competing[:5],
            }
        competing.append(r["url"])
    return {
        "rank": -1,
        "page": None,
        "found": False,
        "snippet": "",
        "competing_urls": [r["url"] for r in results[:5]],
    }


def _calculate_visibility(keyword_results: list[dict], max_pages: int) -> int:
    """Visibility score 0-100 based on rank positions."""
    if not keyword_results:
        return 0
    max_pos = max_pages * 10
    total = 0
    for kw in keyword_results:
        if kw.get("found") and kw.get("rank", -1) > 0:
            total += max(0, (max_pos - kw["rank"] + 1) / max_pos) * 100
    return round(total / len(keyword_results))


# ═══════════════════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════════════════

async def analyze(url: str, keywords: list[str], max_pages: int = 5) -> dict:
    """Rank-check each keyword on Google. Tries API → Playwright → AI fallback."""
    clean_keywords = [k.strip() for k in keywords if k.strip()]
    if not clean_keywords:
        return {
            "keywords": [], "visibility_score": 0, "quick_wins": [],
            "summary": "No keywords provided.",
            "captcha_detected": False, "data_source": "none",
        }

    keyword_results = []
    captcha_count = 0
    data_source = "google_api"  # will be updated per actual source used

    for i, keyword in enumerate(clean_keywords):
        # Random delay between keywords (2-5s) to be respectful
        if i > 0:
            delay = random.uniform(2.0, 5.0)
            logger.info("Waiting %.1fs before next keyword...", delay)
            await asyncio.sleep(delay)

        # ── TIER 1: Google Custom Search API ──
        api_results = await _google_api_search(keyword, num=max_pages * 10)
        if api_results is not None and len(api_results) > 0:
            rank_info = _find_rank(api_results, url)
            keyword_results.append({
                "keyword": keyword,
                **rank_info,
                "data_source": "google_api",
            })
            continue

        # ── TIER 2: Playwright stealth browser ──
        data_source = "google_scrape"
        pw_result = await _playwright_search(keyword, max_pages)

        if pw_result.get("captcha"):
            captcha_count += 1
            keyword_results.append({
                "keyword": keyword,
                "rank": -1, "page": None, "found": False,
                "snippet": "", "competing_urls": [],
                "data_source": "captcha_blocked",
            })
            continue

        if pw_result["results"]:
            rank_info = _find_rank(pw_result["results"], url)
            keyword_results.append({
                "keyword": keyword,
                **rank_info,
                "data_source": "google_scrape",
            })
            continue

        # No results from Playwright (but no CAPTCHA either)
        keyword_results.append({
            "keyword": keyword,
            "rank": -1, "page": None, "found": False,
            "snippet": "", "competing_urls": [],
            "data_source": "google_scrape",
        })

    # ── If ALL keywords were CAPTCHA-blocked, fall back to AI ──
    if captcha_count == len(clean_keywords):
        logger.warning("All keywords blocked by CAPTCHA. Falling back to AI.")
        return await _ai_fallback(url, clean_keywords, max_pages)

    # ── Calculate visibility from real data ──
    real = [r for r in keyword_results if r["data_source"] != "captcha_blocked"]
    visibility = _calculate_visibility(real, max_pages)

    # ── AI analysis for quick_wins + summary ──
    analysis = await _generate_ai_analysis(url, keyword_results)

    any_captcha = captcha_count > 0
    captcha_msg = ""
    if any_captcha:
        blocked = [r["keyword"] for r in keyword_results if r["data_source"] == "captcha_blocked"]
        captcha_msg = (
            f" ⚠️ Google blocked {len(blocked)} keyword(s): {', '.join(blocked)}. "
            "Try again later or set up a Google Custom Search API key for reliable results."
        )

    return {
        "keywords": keyword_results,
        "visibility_score": visibility,
        "quick_wins": analysis.get("quick_wins", []),
        "summary": analysis.get("summary", "") + captcha_msg,
        "captcha_detected": any_captcha,
        "captcha_message": (
            "⚠️ Google temporarily blocked some automated searches. "
            "For reliable results, configure GOOGLE_API_KEY and GOOGLE_CSE_ID in your .env file. "
            "Free for 100 queries/day: https://programmablesearchengine.google.com"
        ) if any_captcha else None,
        "data_source": data_source if not any_captcha else "partial",
    }
