"""Full SEO Audit — Extensive programmatic checks + AI analysis."""

import asyncio
import re
from .scraper import fetch_page, fetch_text_file, parse_html
from .ai_client import ask_ai
from urllib.parse import urljoin


def _audit_technical(url: str, html: str, soup, response) -> dict:
    """Check technical SEO factors."""
    data = {}

    # HTTPS
    data["https"] = response.url.startswith("https")

    # Response time
    data["response_time_ms"] = round(response.elapsed.total_seconds() * 1000)

    # Status code
    data["status_code"] = response.status_code

    # Canonical tag
    canonical = soup.find("link", rel="canonical")
    data["canonical"] = canonical.get("href", "") if canonical else None

    # Robots meta
    robots_meta = soup.find("meta", attrs={"name": "robots"})
    data["robots_meta"] = robots_meta.get("content", "") if robots_meta else None

    # Hreflang
    hreflangs = soup.find_all("link", rel="alternate", hreflang=True)
    data["hreflang_count"] = len(hreflangs)

    # Structured data
    ld_json = soup.find_all("script", type="application/ld+json")
    data["structured_data_count"] = len(ld_json)

    # Page size
    data["page_size_kb"] = round(len(html) / 1024, 1)

    return data


def _audit_onpage(soup) -> dict:
    """Check on-page SEO factors."""
    data = {}

    # Title
    title = soup.find("title")
    data["title"] = title.get_text(strip=True) if title else None
    data["title_length"] = len(data["title"]) if data["title"] else 0

    # Meta description
    meta_desc = soup.find("meta", attrs={"name": "description"})
    data["meta_description"] = meta_desc.get("content", "") if meta_desc else None
    data["meta_desc_length"] = len(data["meta_description"]) if data["meta_description"] else 0

    # Headings
    for level in range(1, 7):
        tags = soup.find_all(f"h{level}")
        data[f"h{level}_count"] = len(tags)
        if tags:
            data[f"h{level}_texts"] = [t.get_text(strip=True)[:80] for t in tags[:5]]

    # Images
    images = soup.find_all("img")
    data["total_images"] = len(images)
    data["images_without_alt"] = len([i for i in images if not i.get("alt")])

    # Internal / external links
    links = soup.find_all("a", href=True)
    data["total_links"] = len(links)

    # Open Graph
    og_tags = soup.find_all("meta", property=re.compile(r"^og:"))
    data["og_tags"] = len(og_tags)

    # Twitter cards
    tw_tags = soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")})
    data["twitter_cards"] = len(tw_tags)

    return data


def _check_robots_txt(url: str) -> dict:
    """Fetch and analyze robots.txt."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    text = fetch_text_file(robots_url)
    data = {"exists": text is not None, "url": robots_url}
    if text:
        data["content_preview"] = text[:500]
        data["has_sitemap_ref"] = "sitemap" in text.lower()
        data["disallow_count"] = text.lower().count("disallow")
    return data


def _check_sitemap(url: str) -> dict:
    """Fetch and analyze sitemap.xml."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
    text = fetch_text_file(sitemap_url)
    data = {"exists": text is not None, "url": sitemap_url}
    if text:
        data["url_count"] = text.count("<loc>")
        data["has_lastmod"] = "<lastmod>" in text
    return data


def _format_audit_data(url, tech, onpage, robots, sitemap) -> str:
    lines = [f"PROGRAMMATIC SEO AUDIT — {url}", "=" * 60]

    lines.append("\n### TECHNICAL SEO")
    lines.append(f"  HTTPS: {'✅' if tech['https'] else '❌ NOT SECURE'}")
    lines.append(f"  Status Code: {tech['status_code']}")
    lines.append(f"  Response Time: {tech['response_time_ms']}ms")
    lines.append(f"  Page Size: {tech['page_size_kb']} KB")
    lines.append(f"  Canonical: {tech['canonical'] or '❌ Missing'}")
    lines.append(f"  Robots Meta: {tech['robots_meta'] or 'Not set'}")
    lines.append(f"  Hreflang Tags: {tech['hreflang_count']}")
    lines.append(f"  Structured Data (JSON-LD): {tech['structured_data_count']}")

    lines.append("\n### ON-PAGE SEO")
    lines.append(f"  Title: {onpage['title'] or '❌ Missing'} ({onpage['title_length']} chars)")
    if onpage['title_length'] > 0:
        if onpage['title_length'] < 30:
            lines.append("    ⚠️ Title may be too short (< 30 chars)")
        elif onpage['title_length'] > 60:
            lines.append("    ⚠️ Title may be too long (> 60 chars)")
        else:
            lines.append("    ✅ Title length is good")

    lines.append(f"  Meta Description: {(onpage['meta_description'] or '❌ Missing')[:80]}...")
    lines.append(f"    Length: {onpage['meta_desc_length']} chars", )
    if onpage['meta_desc_length'] > 0:
        if onpage['meta_desc_length'] < 70:
            lines.append("    ⚠️ Meta description may be too short")
        elif onpage['meta_desc_length'] > 160:
            lines.append("    ⚠️ Meta description may be too long")

    for level in range(1, 4):
        count = onpage.get(f"h{level}_count", 0)
        texts = onpage.get(f"h{level}_texts", [])
        lines.append(f"  H{level}: {count} tags" + (f" — {', '.join(texts[:2])}" if texts else ""))
    if onpage["h1_count"] != 1:
        lines.append(f"    ⚠️ Should have exactly 1 H1 (found {onpage['h1_count']})")

    lines.append(f"  Images: {onpage['total_images']} total, {onpage['images_without_alt']} missing alt")
    lines.append(f"  Links: {onpage['total_links']}")
    lines.append(f"  Open Graph tags: {onpage['og_tags']}")
    lines.append(f"  Twitter Card tags: {onpage['twitter_cards']}")

    lines.append("\n### ROBOTS.TXT")
    lines.append(f"  Exists: {'✅' if robots['exists'] else '❌ Not found'}")
    if robots['exists']:
        lines.append(f"  Sitemap reference: {'✅' if robots.get('has_sitemap_ref') else '❌ Missing'}")
        lines.append(f"  Disallow rules: {robots.get('disallow_count', 0)}")

    lines.append("\n### SITEMAP.XML")
    lines.append(f"  Exists: {'✅' if sitemap['exists'] else '❌ Not found'}")
    if sitemap['exists']:
        lines.append(f"  URLs listed: {sitemap.get('url_count', 'N/A')}")
        lines.append(f"  Has lastmod: {'✅' if sitemap.get('has_lastmod') else '❌'}")

    return "\n".join(lines)


SYSTEM_PROMPT = """You are a comprehensive SEO auditor. You are given programmatic SEO audit data from a website.
Based on this data, produce a full audit report with scores for each section.

## FORMAT:
OVERALL SEO SCORE: [0-100]

### 1. TECHNICAL SEO (Score: X/100)
Analyze crawlability, indexation, HTTPS, speed, canonical, structured data.

### 2. ON-PAGE SEO (Score: X/100)
Analyze title, meta description, headings, images, linking, OG/Twitter.

### 3. CONTENT ANALYSIS (Score: X/100)
Estimate content quality, depth, E-E-A-T based on available data.

### 4. OFF-PAGE SEO (Score: X/100)
Estimate domain authority based on signals you can infer.

### 5. USER EXPERIENCE (Score: X/100)
Mobile readiness, page speed, accessibility.

## PRIORITIZED ACTION PLAN:
- 🔴 Quick Wins (this week) — with expected impact
- 🟡 Short-term (this month)
- 🟢 Long-term (this quarter)

Be specific, reference the actual data, and give actionable recommendations."""


async def full_audit(url: str) -> str:
    resp = await asyncio.to_thread(fetch_page, url)
    if resp is None:
        return f"Error: Could not fetch {url}. Check the URL and try again."

    soup = parse_html(resp.text)

    tech = _audit_technical(url, resp.text, soup, resp)
    onpage = _audit_onpage(soup)
    robots = await asyncio.to_thread(_check_robots_txt, url)
    sitemap = await asyncio.to_thread(_check_sitemap, url)

    data_report = _format_audit_data(url, tech, onpage, robots, sitemap)

    ai_analysis = await ask_ai(
        SYSTEM_PROMPT,
        f"Website: {url}\n\nHere is the programmatic audit data:\n\n{data_report}\n\n"
        "Produce a scored SEO audit with actionable recommendations.",
        4000,
    )

    return data_report + "\n\n" + "─" * 60 + "\nAI SEO ANALYSIS\n" + "─" * 60 + "\n\n" + ai_analysis
