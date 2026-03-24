"""Full SEO Audit — Extensive programmatic checks + AI analysis."""

import asyncio
import re
from .scraper import fetch_page, fetch_text_file, parse_html
from .ai_client import ask_ai
from urllib.parse import urlparse


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

    # Viewport
    viewport = soup.find("meta", attrs={"name": "viewport"})
    data["has_viewport"] = viewport is not None

    # Charset
    charset = soup.find("meta", charset=True)
    data["has_charset"] = charset is not None

    # Favicon
    favicon = soup.find("link", rel=re.compile(r"icon", re.I))
    data["has_favicon"] = favicon is not None

    # Language
    html_tag = soup.find("html")
    data["lang"] = html_tag.get("lang", None) if html_tag else None

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

    # Meta keywords
    meta_kw = soup.find("meta", attrs={"name": "keywords"})
    data["meta_keywords"] = meta_kw.get("content", "") if meta_kw else None

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
    data["images_without_dimensions"] = len([i for i in images if not i.get("width") and not i.get("height")])

    # Internal / external links
    links = soup.find_all("a", href=True)
    data["total_links"] = len(links)
    internal = [l for l in links if l["href"].startswith("/") or not l["href"].startswith("http")]
    external = [l for l in links if l["href"].startswith("http")]
    data["internal_links"] = len(internal)
    data["external_links"] = len(external)
    data["nofollow_links"] = len([l for l in links if "nofollow" in (l.get("rel") or [])])

    # Open Graph
    og_tags = soup.find_all("meta", property=re.compile(r"^og:"))
    data["og_tags"] = len(og_tags)
    og_title = soup.find("meta", property="og:title")
    data["og_title"] = og_title.get("content", "") if og_title else None
    og_desc = soup.find("meta", property="og:description")
    data["og_description"] = og_desc.get("content", "") if og_desc else None
    og_image = soup.find("meta", property="og:image")
    data["og_image"] = og_image.get("content", "") if og_image else None

    # Twitter cards
    tw_tags = soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")})
    data["twitter_cards"] = len(tw_tags)

    # Word count (rough)
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    data["word_count"] = len(text.split())

    return data


def _check_robots_txt(url: str) -> dict:
    """Fetch and analyze robots.txt."""
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
    parsed = urlparse(url)
    sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
    text = fetch_text_file(sitemap_url)
    data = {"exists": text is not None, "url": sitemap_url}
    if text:
        data["url_count"] = text.count("<loc>")
        data["has_lastmod"] = "<lastmod>" in text
    return data


def _compute_scores(tech: dict, onpage: dict, robots: dict, sitemap: dict) -> dict:
    """Compute scores for each SEO category (0-100)."""
    scores = {}

    # 1. Technical SEO
    ts = 0
    if tech["https"]:
        ts += 20
    if tech["status_code"] == 200:
        ts += 15
    if tech["response_time_ms"] < 1000:
        ts += 15
    elif tech["response_time_ms"] < 2000:
        ts += 8
    if tech["canonical"]:
        ts += 10
    if tech["structured_data_count"] > 0:
        ts += 10
    if tech["has_viewport"]:
        ts += 10
    if tech["has_charset"]:
        ts += 5
    if tech["has_favicon"]:
        ts += 5
    if tech["lang"]:
        ts += 5
    if tech["page_size_kb"] < 200:
        ts += 5
    scores["technical"] = min(ts, 100)

    # 2. On-Page SEO
    op = 0
    if onpage["title"] and 30 <= onpage["title_length"] <= 60:
        op += 15
    elif onpage["title"]:
        op += 8
    if onpage["meta_description"] and 70 <= onpage["meta_desc_length"] <= 160:
        op += 15
    elif onpage["meta_description"]:
        op += 8
    if onpage["h1_count"] == 1:
        op += 15
    elif onpage["h1_count"] > 0:
        op += 5
    if onpage.get("h2_count", 0) >= 2:
        op += 10
    if onpage["total_images"] > 0 and onpage["images_without_alt"] == 0:
        op += 10
    elif onpage["total_images"] > 0:
        op += 5
    if onpage["og_tags"] >= 3:
        op += 10
    elif onpage["og_tags"] > 0:
        op += 5
    if onpage["twitter_cards"] >= 2:
        op += 5
    if onpage["internal_links"] >= 3:
        op += 10
    if onpage["word_count"] >= 300:
        op += 10
    elif onpage["word_count"] >= 100:
        op += 5
    scores["on_page"] = min(op, 100)

    # 3. Content Quality
    cq = 20
    if onpage["word_count"] >= 1000:
        cq += 25
    elif onpage["word_count"] >= 500:
        cq += 15
    elif onpage["word_count"] >= 300:
        cq += 10
    total_headings = sum(onpage.get(f"h{i}_count", 0) for i in range(1, 7))
    if total_headings >= 5:
        cq += 15
    elif total_headings >= 3:
        cq += 10
    if onpage["total_images"] >= 3:
        cq += 10
    elif onpage["total_images"] >= 1:
        cq += 5
    if onpage["internal_links"] >= 5:
        cq += 10
    if onpage["external_links"] >= 1:
        cq += 5
    if onpage.get("meta_keywords"):
        cq += 5
    if tech["structured_data_count"] > 0:
        cq += 10
    scores["content"] = min(cq, 100)

    # 4. Crawlability & Indexation
    ci = 0
    if robots["exists"]:
        ci += 25
        if robots.get("has_sitemap_ref"):
            ci += 10
    if sitemap["exists"]:
        ci += 25
        if sitemap.get("url_count", 0) > 0:
            ci += 10
        if sitemap.get("has_lastmod"):
            ci += 5
    if tech["canonical"]:
        ci += 10
    if tech["robots_meta"] is None or "noindex" not in (tech["robots_meta"] or ""):
        ci += 15
    scores["crawlability"] = min(ci, 100)

    # 5. Social & Sharing
    ss = 0
    if onpage["og_tags"] >= 4:
        ss += 35
    elif onpage["og_tags"] >= 2:
        ss += 20
    elif onpage["og_tags"] >= 1:
        ss += 10
    if onpage["og_image"]:
        ss += 20
    if onpage["og_title"]:
        ss += 10
    if onpage["og_description"]:
        ss += 10
    if onpage["twitter_cards"] >= 3:
        ss += 25
    elif onpage["twitter_cards"] >= 1:
        ss += 15
    scores["social"] = min(ss, 100)

    # Overall
    weights = {"technical": 0.25, "on_page": 0.25, "content": 0.20, "crawlability": 0.15, "social": 0.15}
    scores["overall"] = round(sum(scores[k] * weights[k] for k in weights))

    return scores


def _generate_issues(tech: dict, onpage: dict, robots: dict, sitemap: dict) -> list:
    """Generate detailed issues from audit data."""
    issues = []

    # Technical
    if not tech["https"]:
        issues.append({"section": "Technical", "severity": "critical", "title": "No HTTPS", "detail": "Site is not served over HTTPS. This hurts rankings, trust, and security.", "fix": "Install an SSL certificate and redirect HTTP to HTTPS.", "priority": 1})
    if tech["status_code"] != 200:
        issues.append({"section": "Technical", "severity": "critical", "title": f"HTTP Status {tech['status_code']}", "detail": f"Page returned status code {tech['status_code']} instead of 200.", "fix": "Investigate and fix the server response to return 200 OK.", "priority": 1})
    if tech["response_time_ms"] > 3000:
        issues.append({"section": "Technical", "severity": "critical", "title": f"Slow Response ({tech['response_time_ms']}ms)", "detail": "Server response time exceeds 3 seconds. Google recommends under 200ms TTFB.", "fix": "Optimize server configuration, enable caching, use a CDN.", "priority": 2})
    elif tech["response_time_ms"] > 1000:
        issues.append({"section": "Technical", "severity": "warning", "title": f"Moderate Response Time ({tech['response_time_ms']}ms)", "detail": "Server response is over 1 second. Aim for under 500ms.", "fix": "Enable server-side caching, optimize database queries, consider a CDN.", "priority": 4})
    if not tech["canonical"]:
        issues.append({"section": "Technical", "severity": "warning", "title": "Missing Canonical Tag", "detail": "No canonical URL specified. This can cause duplicate content issues.", "fix": "Add <link rel=\"canonical\" href=\"...\"> to prevent duplicate content.", "priority": 3})
    if tech["structured_data_count"] == 0:
        issues.append({"section": "Technical", "severity": "info", "title": "No Structured Data", "detail": "No JSON-LD structured data found. Structured data enables rich snippets.", "fix": "Add Schema.org JSON-LD markup (Organization, WebPage, FAQPage, etc.).", "priority": 5})
    if not tech["has_viewport"]:
        issues.append({"section": "Technical", "severity": "critical", "title": "Missing Viewport Meta", "detail": "Page lacks viewport meta tag. Mobile rendering will be broken.", "fix": "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">.", "priority": 1})
    if not tech["has_favicon"]:
        issues.append({"section": "Technical", "severity": "info", "title": "No Favicon", "detail": "No favicon detected. Favicons improve brand recognition in browser tabs.", "fix": "Add <link rel=\"icon\" href=\"/favicon.ico\"> to the page head.", "priority": 6})
    if not tech["lang"]:
        issues.append({"section": "Technical", "severity": "warning", "title": "Missing Language Attribute", "detail": "HTML tag has no lang attribute. This helps search engines and screen readers.", "fix": "Add lang=\"en\" (or appropriate language) to the <html> tag.", "priority": 4})
    if tech["page_size_kb"] > 500:
        issues.append({"section": "Technical", "severity": "warning", "title": f"Large Page Size ({tech['page_size_kb']}KB)", "detail": "Page HTML exceeds 500KB. Large pages load slower.", "fix": "Minify HTML, remove unnecessary scripts/styles, lazy-load content.", "priority": 4})

    # On-Page
    if not onpage["title"]:
        issues.append({"section": "On-Page", "severity": "critical", "title": "Missing Title Tag", "detail": "No title tag found. The title tag is the most important on-page SEO element.", "fix": "Add a descriptive, keyword-rich <title> tag (30-60 characters).", "priority": 1})
    elif onpage["title_length"] < 30:
        issues.append({"section": "On-Page", "severity": "warning", "title": f"Short Title ({onpage['title_length']} chars)", "detail": f"Title \"{onpage['title']}\" is too short. Aim for 30-60 characters.", "fix": "Expand the title with your primary keyword and a value proposition.", "priority": 3})
    elif onpage["title_length"] > 60:
        issues.append({"section": "On-Page", "severity": "warning", "title": f"Long Title ({onpage['title_length']} chars)", "detail": f"Title may be truncated in search results. Keep under 60 characters.", "fix": "Shorten the title while keeping the primary keyword near the beginning.", "priority": 3})

    if not onpage["meta_description"]:
        issues.append({"section": "On-Page", "severity": "critical", "title": "Missing Meta Description", "detail": "No meta description found. This is critical for click-through rates.", "fix": "Add a compelling meta description (70-160 characters) with target keywords.", "priority": 1})
    elif onpage["meta_desc_length"] < 70:
        issues.append({"section": "On-Page", "severity": "warning", "title": f"Short Meta Description ({onpage['meta_desc_length']} chars)", "detail": "Meta description is too short. Aim for 70-160 characters.", "fix": "Expand the description to include your value proposition and CTA.", "priority": 3})
    elif onpage["meta_desc_length"] > 160:
        issues.append({"section": "On-Page", "severity": "warning", "title": f"Long Meta Description ({onpage['meta_desc_length']} chars)", "detail": "Meta description will be truncated. Keep under 160 characters.", "fix": "Trim to 155-160 characters. Put the most important info first.", "priority": 4})

    if onpage["h1_count"] == 0:
        issues.append({"section": "On-Page", "severity": "critical", "title": "Missing H1 Tag", "detail": "No H1 heading found. Each page should have exactly one H1.", "fix": "Add a clear H1 that includes your primary keyword.", "priority": 1})
    elif onpage["h1_count"] > 1:
        issues.append({"section": "On-Page", "severity": "warning", "title": f"Multiple H1 Tags ({onpage['h1_count']})", "detail": "Multiple H1 tags dilute topical focus. Best practice: exactly one H1.", "fix": "Keep one H1 and demote others to H2.", "priority": 3})

    if onpage["images_without_alt"] > 0:
        issues.append({"section": "On-Page", "severity": "warning", "title": f"{onpage['images_without_alt']} Images Missing Alt Text", "detail": "Images without alt text hurt accessibility and SEO image rankings.", "fix": "Add descriptive, keyword-relevant alt text to all images.", "priority": 3})

    if onpage["og_tags"] == 0:
        issues.append({"section": "Social", "severity": "warning", "title": "No Open Graph Tags", "detail": "Missing Open Graph tags means poor social media sharing previews.", "fix": "Add og:title, og:description, og:image, and og:url meta tags.", "priority": 4})

    if onpage["twitter_cards"] == 0:
        issues.append({"section": "Social", "severity": "info", "title": "No Twitter Card Tags", "detail": "Missing Twitter Card tags. Tweets won't show rich link previews.", "fix": "Add twitter:card, twitter:title, twitter:description, twitter:image meta tags.", "priority": 5})

    if onpage["word_count"] < 300:
        issues.append({"section": "Content", "severity": "warning", "title": f"Thin Content ({onpage['word_count']} words)", "detail": "Less than 300 words. Thin content struggles to rank.", "fix": "Expand content to 800+ words with valuable, relevant information.", "priority": 3})

    if onpage["internal_links"] < 3:
        issues.append({"section": "On-Page", "severity": "warning", "title": f"Few Internal Links ({onpage['internal_links']})", "detail": "Low internal linking reduces crawlability and link equity distribution.", "fix": "Add internal links to key pages using descriptive anchor text.", "priority": 4})

    # Crawlability
    if not robots["exists"]:
        issues.append({"section": "Crawlability", "severity": "warning", "title": "Missing robots.txt", "detail": "No robots.txt file found. Search engines need guidance on what to crawl.", "fix": "Create a robots.txt file with appropriate directives and sitemap reference.", "priority": 3})
    elif not robots.get("has_sitemap_ref"):
        issues.append({"section": "Crawlability", "severity": "info", "title": "No Sitemap in robots.txt", "detail": "robots.txt doesn't reference a sitemap. Helps search engines discover pages.", "fix": "Add Sitemap: https://yourdomain.com/sitemap.xml to robots.txt.", "priority": 5})

    if not sitemap["exists"]:
        issues.append({"section": "Crawlability", "severity": "warning", "title": "Missing sitemap.xml", "detail": "No sitemap found. Sitemaps help search engines discover and index pages.", "fix": "Generate an XML sitemap and submit it via Google Search Console.", "priority": 3})

    issues.sort(key=lambda x: x["priority"])
    return issues


def _build_check_items(tech: dict, onpage: dict, robots: dict, sitemap: dict) -> list:
    """Build a list of all check items with pass/fail status for the checklist view."""
    checks = []

    def add(section, name, passed, value="", detail=""):
        checks.append({"section": section, "name": name, "passed": passed, "value": value, "detail": detail})

    # Technical
    add("Technical", "HTTPS", tech["https"], "✅ Secure" if tech["https"] else "❌ Not Secure")
    add("Technical", "Status Code", tech["status_code"] == 200, str(tech["status_code"]))
    add("Technical", "Response Time", tech["response_time_ms"] < 1000, f"{tech['response_time_ms']}ms")
    add("Technical", "Page Size", tech["page_size_kb"] < 500, f"{tech['page_size_kb']}KB")
    add("Technical", "Canonical Tag", bool(tech["canonical"]), tech["canonical"] or "Missing")
    add("Technical", "Viewport Meta", tech["has_viewport"])
    add("Technical", "Charset", tech["has_charset"])
    add("Technical", "Favicon", tech["has_favicon"])
    add("Technical", "Language Attr", bool(tech["lang"]), tech["lang"] or "Missing")
    add("Technical", "Structured Data", tech["structured_data_count"] > 0, f"{tech['structured_data_count']} schemas")
    add("Technical", "Hreflang", tech["hreflang_count"] > 0 or True, f"{tech['hreflang_count']} tags", "Optional for multi-language sites")

    # On-Page
    add("On-Page", "Title Tag", bool(onpage["title"]), onpage["title"] or "Missing")
    add("On-Page", "Title Length", 30 <= onpage["title_length"] <= 60, f"{onpage['title_length']} chars (30-60 ideal)")
    add("On-Page", "Meta Description", bool(onpage["meta_description"]), (onpage["meta_description"] or "Missing")[:80])
    add("On-Page", "Meta Desc Length", 70 <= onpage["meta_desc_length"] <= 160, f"{onpage['meta_desc_length']} chars (70-160 ideal)")
    add("On-Page", "H1 Tag", onpage["h1_count"] == 1, f"{onpage['h1_count']} found (1 ideal)")
    add("On-Page", "H2 Tags", onpage.get("h2_count", 0) >= 2, f"{onpage.get('h2_count', 0)} found")
    add("On-Page", "Image Alt Text", onpage["images_without_alt"] == 0, f"{onpage['images_without_alt']}/{onpage['total_images']} missing")
    add("On-Page", "Internal Links", onpage["internal_links"] >= 3, f"{onpage['internal_links']} found")
    add("On-Page", "Word Count", onpage["word_count"] >= 300, f"{onpage['word_count']} words")

    # Social
    add("Social", "Open Graph", onpage["og_tags"] >= 3, f"{onpage['og_tags']} tags")
    add("Social", "OG Image", bool(onpage.get("og_image")))
    add("Social", "Twitter Cards", onpage["twitter_cards"] >= 2, f"{onpage['twitter_cards']} tags")

    # Crawlability
    add("Crawlability", "robots.txt", robots["exists"])
    add("Crawlability", "Sitemap in robots", robots.get("has_sitemap_ref", False))
    add("Crawlability", "sitemap.xml", sitemap["exists"])
    if sitemap["exists"]:
        add("Crawlability", "Sitemap URLs", (sitemap.get("url_count", 0) or 0) > 0, f"{sitemap.get('url_count', 0)} URLs")
        add("Crawlability", "Sitemap Lastmod", sitemap.get("has_lastmod", False))

    return checks


SYSTEM_PROMPT = """You are a senior SEO consultant. Given audit scores and data, provide a concise but powerful executive analysis:

1. EXECUTIVE SUMMARY (2-3 sentences about overall SEO health)
2. TOP 3 PRIORITY FIXES (specific, actionable, with expected impact)
3. QUICK WINS (things that can be done today)
4. COMPETITIVE EDGE TIPS (2-3 advanced recommendations)

Keep total response under 400 words. Be specific, reference actual scores. No generic advice."""


async def full_audit(url: str) -> dict:
    resp = await asyncio.to_thread(fetch_page, url)
    if resp is None:
        return {"error": f"Could not fetch {url}. Check the URL and try again."}

    soup = parse_html(resp.text)

    tech = _audit_technical(url, resp.text, soup, resp)
    onpage = _audit_onpage(soup)
    robots = await asyncio.to_thread(_check_robots_txt, url)
    sitemap = await asyncio.to_thread(_check_sitemap, url)

    scores = _compute_scores(tech, onpage, robots, sitemap)
    issues = _generate_issues(tech, onpage, robots, sitemap)
    checks = _build_check_items(tech, onpage, robots, sitemap)

    result = {
        "url": url,
        "scores": scores,
        "issues": issues,
        "checks": checks,
        "data": {
            "technical": tech,
            "on_page": onpage,
            "robots": robots,
            "sitemap": sitemap,
        },
        "issue_counts": {
            "critical": len([i for i in issues if i["severity"] == "critical"]),
            "warning": len([i for i in issues if i["severity"] == "warning"]),
            "info": len([i for i in issues if i["severity"] == "info"]),
        },
        "check_summary": {
            "passed": len([c for c in checks if c["passed"]]),
            "failed": len([c for c in checks if not c["passed"]]),
            "total": len(checks),
        },
    }

    # AI analysis
    try:
        score_text = ", ".join(f"{k}: {v}/100" for k, v in scores.items())
        issue_text = f"{result['issue_counts']['critical']} critical, {result['issue_counts']['warning']} warnings, {result['issue_counts']['info']} info"
        ai_text = await ask_ai(
            SYSTEM_PROMPT,
            f"Website: {url}\nScores: {score_text}\nIssues: {issue_text}\nChecks passed: {result['check_summary']['passed']}/{result['check_summary']['total']}\n"
            f"Key data: HTTPS={tech['https']}, title_len={onpage['title_length']}, meta_desc_len={onpage['meta_desc_length']}, "
            f"h1_count={onpage['h1_count']}, word_count={onpage['word_count']}, images={onpage['total_images']}, "
            f"alt_missing={onpage['images_without_alt']}, internal_links={onpage['internal_links']}, "
            f"og_tags={onpage['og_tags']}, structured_data={tech['structured_data_count']}, "
            f"robots={robots['exists']}, sitemap={sitemap['exists']}, response_ms={tech['response_time_ms']}",
            1200,
        )
        result["ai_analysis"] = ai_text
    except Exception:
        pass

    return result
