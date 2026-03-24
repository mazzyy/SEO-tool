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


def _format_ux_data(data: dict) -> str:
    lines = ["PROGRAMMATIC UX DATA", "=" * 40]

    lines.append(f"\n📱 RESPONSIVE DESIGN")
    lines.append(f"  Viewport meta: {'✅ Present' if data['has_viewport'] else '❌ Missing'}")
    if data['viewport_content']:
        lines.append(f"  Viewport content: {data['viewport_content']}")

    lines.append(f"\n🖼️ IMAGES")
    lines.append(f"  Total images: {data['total_images']}")
    lines.append(f"  Missing alt text: {data['images_missing_alt']}")
    if data['missing_alt_examples']:
        for ex in data['missing_alt_examples']:
            lines.append(f"    - {ex}")

    lines.append(f"\n📑 HEADING STRUCTURE")
    lines.append(f"  H1 tags: {data['h1_count']} {'✅' if data['h1_count'] == 1 else '⚠️ Should be exactly 1'}")
    for level, texts in data['headings'].items():
        lines.append(f"  {level}: {len(texts)} — {', '.join(texts[:3])}")

    lines.append(f"\n♿ ACCESSIBILITY")
    lines.append(f"  ARIA roles: {data['aria_roles']}")
    lines.append(f"  ARIA labels: {data['aria_labels']}")
    lines.append(f"  Forms: {data['form_count']} | Inputs: {data['input_count']} | Labels: {data['label_count']}")
    if data['input_count'] > data['label_count']:
        lines.append(f"  ⚠️ {data['input_count'] - data['label_count']} inputs may lack associated labels")

    lines.append(f"\n🔗 LINKS & CTAs")
    lines.append(f"  Total links: {data['total_links']}")
    lines.append(f"  Empty links (no text): {data['empty_links']}")
    lines.append(f"  CTAs detected: {data['cta_count']}")

    return "\n".join(lines)


SYSTEM_PROMPT = """You are an expert UI/UX auditor. You have been given programmatic analysis data from a website.
Using this data, provide a comprehensive UI/UX audit covering:

1. Visual Hierarchy — heading structure assessment
2. Navigation — link quality, CTA effectiveness
3. Mobile Responsiveness — viewport config
4. Accessibility — WCAG compliance based on alt texts, ARIA, form labels
5. Content Readability — heading hierarchy, structure
6. Trust Signals — CTA quality

For each issue found:
- Severity: 🔴 Critical / 🟡 Warning / 🟢 Minor
- Impact description
- Fix recommendation
- Priority (1-10)

End with an overall UI/UX score /100 and a prioritized action plan.
Be specific and reference the actual data provided."""


async def analyze(url: str, pages: list[str]) -> str:
    resp = await asyncio.to_thread(fetch_page, url)
    if resp is None:
        return f"Error: Could not fetch {url}. Check the URL and try again."

    soup = parse_html(resp.text)
    ux_data = _extract_ux_data(resp.text, soup)
    data_report = _format_ux_data(ux_data)

    page_str = ""
    if pages and any(p.strip() for p in pages):
        page_str = f"\nSpecific pages requested: {', '.join(p for p in pages if p.strip())}"

    result = await asyncio.to_thread(
        ask_ai,
        SYSTEM_PROMPT,
        f"Website: {url}{page_str}\n\nHere is the programmatic analysis data:\n\n{data_report}\n\n"
        "Please provide a comprehensive UI/UX audit based on this data.",
        3500,
    )

    return data_report + "\n\n" + "─" * 60 + "\nAI UI/UX ANALYSIS\n" + "─" * 60 + "\n\n" + result
