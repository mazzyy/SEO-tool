"""Report Generator — Aggregates data from other services, uses AI for narrative."""

import asyncio
from .scraper import fetch_page, parse_html
from .ai_client import ask_ai
from . import tech_detect, audit, performance, content


async def _gather_data(url: str, sections: dict[str, bool]) -> str:
    """Collect raw data from relevant services based on selected sections."""
    data_parts = []

    # Always fetch the page first
    resp = await asyncio.to_thread(fetch_page, url)
    if resp is None:
        return f"Error: Could not fetch {url}."

    soup = parse_html(resp.text)

    # Gather technical data
    if sections.get("technical", True):
        tech_data = audit._audit_technical(url, resp.text, soup, resp)
        robots_data = await asyncio.to_thread(audit._check_robots_txt, url)
        sitemap_data = await asyncio.to_thread(audit._check_sitemap, url)
        data_parts.append(f"TECHNICAL SEO DATA:\n{tech_data}\nRobots: {robots_data}\nSitemap: {sitemap_data}")

    if sections.get("onpage", True):
        onpage_data = audit._audit_onpage(soup)
        data_parts.append(f"ON-PAGE SEO DATA:\n{onpage_data}")

    if sections.get("content", True):
        from . import content as content_svc
        content_data = content_svc._extract_content(parse_html(resp.text))
        kw_data = content_svc._analyze_keywords(content_data.get("full_text", ""))
        data_parts.append(
            f"CONTENT DATA:\n"
            f"Word count: {content_data['word_count']}, "
            f"Sentences: {content_data['sentence_count']}, "
            f"Reading time: {content_data['reading_time_min']}min, "
            f"Headings: {len(content_data['headings'])}, "
            f"Internal links: {content_data['internal_links']}, "
            f"External links: {content_data['external_links']}\n"
            f"Top keywords: {', '.join(k['word'] for k in kw_data.get('top_words', [])[:10])}"
        )

    if sections.get("performance", True):
        data_parts.append("PERFORMANCE: (PageSpeed Insights data requested separately)")

    if sections.get("uiux", True):
        from . import uiux
        ux_data = uiux._extract_ux_data(resp.text, soup)
        data_parts.append(
            f"UX DATA:\n"
            f"Images: {ux_data['total_images']} (missing alt: {ux_data['images_missing_alt']}), "
            f"H1 count: {ux_data['h1_count']}, "
            f"Viewport: {'Yes' if ux_data['has_viewport'] else 'No'}, "
            f"ARIA roles: {ux_data['aria_roles']}, "
            f"CTAs: {ux_data['cta_count']}, "
            f"Forms: {ux_data['form_count']}"
        )

    if sections.get("competitive", True):
        data_parts.append("COMPETITIVE: (requires separate competitive research)")

    return "\n\n---\n\n".join(data_parts)


SYSTEM_PROMPT = """You are a professional SEO report writer. Generate a polished, comprehensive SEO audit report.

# SEO AUDIT REPORT

## Executive Summary
Brief overview, overall health score (0-100), top 3 critical priorities.

## Detailed Sections (include only those marked as requested):

### Technical SEO
Crawlability, indexation, speed, HTTPS, structured data — with severity ratings.

### On-Page SEO
Meta tags, headings, images, internal linking — with page-by-page assessment.

### Content Analysis
Quality, gaps, keyword opportunities, content calendar suggestions.

### Performance & Core Web Vitals
Speed metrics, optimization opportunities, mobile performance.

### User Experience
Navigation, accessibility, conversion, mobile, design.

### Competitive Analysis
Competitor comparison of key areas, opportunity gaps.

## Priority Action Plan
🔴 Critical (Immediately) — with expected impact
🟡 Important (This Month)
🟢 Recommended (This Quarter)
🔵 Nice to Have

## Expected Impact Timeline
## KPIs to Track

Make it detailed, professional, and actionable. Base everything on the actual data provided."""


async def generate(url: str, sections: dict[str, bool]) -> str:
    if not sections:
        sections = {"technical": True, "onpage": True, "content": True,
                     "performance": True, "uiux": True, "competitive": True}

    raw_data = await _gather_data(url, sections)

    if raw_data.startswith("Error:"):
        return raw_data

    selected = [k for k, v in sections.items() if v]

    report = await ask_ai(
        SYSTEM_PROMPT,
        f"Generate a full SEO audit report for: {url}\n"
        f"Selected sections: {', '.join(selected)}\n\n"
        f"Here is the collected data:\n\n{raw_data}\n\n"
        "Generate the professional report based on this data.",
        4000,
    )

    return report
