"""UI/UX Analysis — Programmatic checks + AI for subjective analysis."""

import asyncio
from .scraper import fetch_page, parse_html
from .ai_client import ask_ai


def _extract_ux_data(html: str, soup) -> dict:
    """Extract accessibility and UX data points programmatically."""
    data = {}

    # Images without alt text
    images = soup.find_all("img")
    no_alt = [img.get("src", "?")[:80] for img in images if not img.get("alt")]
    data["total_images"] = len(images)
    data["images_missing_alt"] = len(no_alt)
    data["missing_alt_examples"] = no_alt[:5]

    # Headings hierarchy
    headings = {}
    for level in range(1, 7):
        tags = soup.find_all(f"h{level}")
        if tags:
            headings[f"h{level}"] = [t.get_text(strip=True)[:60] for t in tags[:5]]
    data["headings"] = headings
    data["h1_count"] = len(soup.find_all("h1"))

    # Viewport meta
    viewport = soup.find("meta", attrs={"name": "viewport"})
    data["has_viewport"] = viewport is not None
    data["viewport_content"] = viewport.get("content", "") if viewport else ""

    # Forms without labels
    forms = soup.find_all("form")
    inputs = soup.find_all("input")
    labels = soup.find_all("label")
    data["form_count"] = len(forms)
    data["input_count"] = len(inputs)
    data["label_count"] = len(labels)

    # ARIA attributes
    aria_elements = soup.find_all(attrs={"role": True})
    aria_labels = soup.find_all(attrs={"aria-label": True})
    data["aria_roles"] = len(aria_elements)
    data["aria_labels"] = len(aria_labels)

    # Links
    links = soup.find_all("a")
    empty_links = [a for a in links if not a.get_text(strip=True) and not a.find("img")]
    data["total_links"] = len(links)
    data["empty_links"] = len(empty_links)

    # Button / CTA detection
    buttons = soup.find_all("button")
    cta_links = [a for a in links if any(w in a.get_text(strip=True).lower() for w in
                 ["sign up", "get started", "buy", "subscribe", "contact", "try", "start", "learn more"])]
    data["button_count"] = len(buttons)
    data["cta_count"] = len(buttons) + len(cta_links)

    # Color contrast - check for inline styles with low contrast (basic)
    data["inline_styles"] = len(soup.find_all(style=True))

    return data


def _compute_scores(data: dict) -> dict:
    """Compute category scores 0-100 from programmatic data."""
    scores = {}

    # 1. Visual Hierarchy (based on heading structure)
    vh = 50
    if data["h1_count"] == 1:
        vh += 25
    elif data["h1_count"] > 1:
        vh += 10
    heading_levels = len(data["headings"])
    vh += min(heading_levels * 8, 25)
    scores["visual_hierarchy"] = min(vh, 100)

    # 2. Navigation (links + CTAs)
    nav = 40
    if data["total_links"] >= 5:
        nav += 15
    if data["total_links"] >= 10:
        nav += 10
    if data["cta_count"] >= 1:
        nav += 20
    if data["cta_count"] >= 3:
        nav += 10
    if data["empty_links"] == 0:
        nav += 5
    scores["navigation"] = min(nav, 100)

    # 3. Mobile Responsiveness
    mobile = 30
    if data["has_viewport"]:
        mobile += 40
    if "width=device-width" in data.get("viewport_content", ""):
        mobile += 15
    if "initial-scale" in data.get("viewport_content", ""):
        mobile += 15
    scores["mobile_responsiveness"] = min(mobile, 100)

    # 4. Accessibility
    acc = 30
    if data["aria_roles"] > 0:
        acc += 15
    if data["aria_roles"] >= 5:
        acc += 10
    if data["aria_labels"] > 0:
        acc += 10
    if data["aria_labels"] >= 3:
        acc += 5
    if data["images_missing_alt"] == 0 and data["total_images"] > 0:
        acc += 15
    elif data["total_images"] == 0:
        acc += 10
    if data["input_count"] > 0 and data["label_count"] >= data["input_count"]:
        acc += 15
    elif data["input_count"] == 0:
        acc += 5
    scores["accessibility"] = min(acc, 100)

    # 5. Content Readability
    cr = 40
    if data["h1_count"] == 1:
        cr += 15
    total_headings = sum(len(v) for v in data["headings"].values())
    cr += min(total_headings * 5, 25)
    if data["total_images"] > 0:
        cr += 10
    if data["total_links"] >= 3:
        cr += 10
    scores["content_readability"] = min(cr, 100)

    # 6. Trust & Conversion
    tc = 20
    if data["cta_count"] >= 1:
        tc += 25
    if data["cta_count"] >= 3:
        tc += 10
    if data["total_images"] > 0:
        tc += 10
    if data["form_count"] > 0:
        tc += 15
    if data["button_count"] >= 2:
        tc += 10
    if data["total_links"] >= 5:
        tc += 10
    scores["trust_conversion"] = min(tc, 100)

    # Overall score (weighted average)
    weights = {
        "visual_hierarchy": 0.15,
        "navigation": 0.20,
        "mobile_responsiveness": 0.20,
        "accessibility": 0.20,
        "content_readability": 0.10,
        "trust_conversion": 0.15,
    }
    overall = sum(scores[k] * weights[k] for k in weights)
    scores["overall"] = round(overall)

    return scores


def _generate_issues(data: dict, scores: dict) -> list:
    """Generate specific issues with severity and recommendations."""
    issues = []

    # Visual Hierarchy
    if data["h1_count"] == 0:
        issues.append({"category": "Visual Hierarchy", "severity": "critical", "title": "Missing H1 Tag", "description": "No H1 heading found. Every page needs exactly one H1 for SEO and accessibility.", "fix": "Add a clear, descriptive H1 tag as the main heading.", "priority": 1})
    elif data["h1_count"] > 1:
        issues.append({"category": "Visual Hierarchy", "severity": "warning", "title": f"Multiple H1 Tags ({data['h1_count']})", "description": "Multiple H1 tags dilute heading hierarchy. Best practice is exactly one H1 per page.", "fix": "Keep one primary H1 and convert others to H2 or lower.", "priority": 3})
    if len(data["headings"]) <= 2:
        issues.append({"category": "Visual Hierarchy", "severity": "warning", "title": "Shallow Heading Structure", "description": f"Only {len(data['headings'])} heading levels used. A rich hierarchy (H1→H4) helps scannability and SEO.", "fix": "Add descriptive H2/H3/H4 subheadings to break content into scannable sections.", "priority": 4})

    # Navigation
    if data["cta_count"] == 0:
        issues.append({"category": "Navigation", "severity": "critical", "title": "No CTAs Detected", "description": "No call-to-action buttons or links found. Visitors have no clear next step.", "fix": "Add a prominent primary CTA above the fold (e.g., 'Get Started', 'Sign Up').", "priority": 1})
    if data["empty_links"] > 0:
        issues.append({"category": "Navigation", "severity": "warning", "title": f"{data['empty_links']} Empty Links", "description": "Links without visible text are inaccessible and confusing.", "fix": "Add descriptive text or aria-labels to all links.", "priority": 3})
    if data["total_links"] < 3:
        issues.append({"category": "Navigation", "severity": "warning", "title": "Very Few Links", "description": f"Only {data['total_links']} links found. Limited navigation hurts usability.", "fix": "Add navigation menu, footer links, and internal content links.", "priority": 4})

    # Mobile
    if not data["has_viewport"]:
        issues.append({"category": "Mobile", "severity": "critical", "title": "Missing Viewport Meta Tag", "description": "Without viewport meta, the page won't display correctly on mobile devices.", "fix": "Add <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"> to the <head>.", "priority": 1})

    # Accessibility
    if data["aria_roles"] == 0 and data["aria_labels"] == 0:
        issues.append({"category": "Accessibility", "severity": "warning", "title": "No ARIA Landmarks", "description": "No ARIA roles or labels detected. Screen reader users can't navigate efficiently.", "fix": "Add landmark roles (banner, navigation, main, contentinfo) and aria-labels to key elements.", "priority": 3})
    if data["images_missing_alt"] > 0:
        issues.append({"category": "Accessibility", "severity": "warning", "title": f"{data['images_missing_alt']} Images Missing Alt Text", "description": "Images without alt text are invisible to screen readers and hurt SEO.", "fix": "Add descriptive alt attributes to all informational images.", "priority": 2})
    if data["input_count"] > data["label_count"]:
        missing = data["input_count"] - data["label_count"]
        issues.append({"category": "Accessibility", "severity": "warning", "title": f"{missing} Inputs Without Labels", "description": "Form inputs without labels are inaccessible. Users can't identify what to enter.", "fix": "Associate a <label> with every <input> using the 'for' attribute.", "priority": 2})

    # Content
    if data["total_images"] == 0:
        issues.append({"category": "Content", "severity": "info", "title": "No Images Found", "description": "Pages without images can feel sterile and reduce engagement. Visual content improves trust and conversion.", "fix": "Add relevant images (hero, screenshots, team photos) with descriptive alt text.", "priority": 5})

    # Trust
    if data["form_count"] == 0 and data["cta_count"] == 0:
        issues.append({"category": "Trust & Conversion", "severity": "critical", "title": "No Conversion Elements", "description": "No forms or CTAs detected. The page lacks any mechanism for user engagement or conversion.", "fix": "Add contact forms, newsletter signups, or clear action buttons.", "priority": 1})

    # Sort by priority
    issues.sort(key=lambda x: x["priority"])
    return issues


def _build_data_summary(data: dict) -> dict:
    """Build a concise data summary for the frontend cards."""
    return {
        "responsive": {
            "has_viewport": data["has_viewport"],
            "viewport_content": data["viewport_content"],
        },
        "images": {
            "total": data["total_images"],
            "missing_alt": data["images_missing_alt"],
            "examples": data["missing_alt_examples"],
        },
        "headings": {
            "h1_count": data["h1_count"],
            "structure": data["headings"],
            "total_levels": len(data["headings"]),
        },
        "accessibility": {
            "aria_roles": data["aria_roles"],
            "aria_labels": data["aria_labels"],
            "forms": data["form_count"],
            "inputs": data["input_count"],
            "labels": data["label_count"],
        },
        "links": {
            "total": data["total_links"],
            "empty": data["empty_links"],
            "ctas": data["cta_count"],
            "buttons": data["button_count"],
        },
    }


SYSTEM_PROMPT = """You are an expert UI/UX auditor. Given programmatic analysis data and scores, provide:
1. A concise executive summary (2-3 sentences about the overall UX quality)
2. Top 3 most impactful recommendations with specific implementation details
3. Quick wins that can be done today

Keep it concise and actionable. No more than 300 words total. Reference the actual scores."""


async def analyze(url: str, pages: list[str]) -> dict:
    resp = await asyncio.to_thread(fetch_page, url)
    if resp is None:
        return {"error": f"Could not fetch {url}. Check the URL and try again."}

    soup = parse_html(resp.text)
    ux_data = _extract_ux_data(resp.text, soup)
    scores = _compute_scores(ux_data)
    issues = _generate_issues(ux_data, scores)
    summary = _build_data_summary(ux_data)

    result = {
        "url": url,
        "scores": scores,
        "issues": issues,
        "summary": summary,
        "issue_counts": {
            "critical": len([i for i in issues if i["severity"] == "critical"]),
            "warning": len([i for i in issues if i["severity"] == "warning"]),
            "info": len([i for i in issues if i["severity"] == "info"]),
        },
    }

    # AI for concise recommendations
    try:
        report_text = f"Overall: {scores['overall']}/100, Visual Hierarchy: {scores['visual_hierarchy']}/100, Navigation: {scores['navigation']}/100, Mobile: {scores['mobile_responsiveness']}/100, Accessibility: {scores['accessibility']}/100, Content: {scores['content_readability']}/100, Trust: {scores['trust_conversion']}/100.\n"
        report_text += f"Issues: {len(issues)} total ({result['issue_counts']['critical']} critical, {result['issue_counts']['warning']} warnings).\n"
        report_text += f"Data: {ux_data['total_links']} links, {ux_data['cta_count']} CTAs, {ux_data['total_images']} images, {ux_data['h1_count']} H1s, ARIA roles: {ux_data['aria_roles']}, viewport: {ux_data['has_viewport']}"

        ai_text = await ask_ai(
            SYSTEM_PROMPT,
            f"Website: {url}\n\n{report_text}",
            800,
        )
        result["ai_recommendations"] = ai_text
    except Exception:
        pass

    return result
