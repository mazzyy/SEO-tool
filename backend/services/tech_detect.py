"""Technology Detection — Mostly programmatic, AI only for summary."""

import asyncio
import re
from .scraper import fetch_page, parse_html
from .ai_client import ask_ai


# ── Signature patterns for common technologies ─────────────────

TECH_SIGNATURES = {
    # CMS / Frameworks
    "WordPress": {"meta": ["generator", "wordpress"], "scripts": ["wp-content", "wp-includes"]},
    "Shopify": {"meta": ["generator", "shopify"], "scripts": ["cdn.shopify.com"]},
    "Wix": {"scripts": ["static.parastorage.com", "wix.com"], "meta": ["generator", "wix"]},
    "Squarespace": {"scripts": ["squarespace.com"], "meta": ["generator", "squarespace"]},
    "Drupal": {"meta": ["generator", "drupal"], "scripts": ["drupal.js"]},
    "Joomla": {"meta": ["generator", "joomla"], "scripts": ["/media/jui/"]},
    # JS Frameworks
    "React": {"scripts": ["react.production.min", "react-dom", "reactjs"], "html_attrs": ["data-reactroot", "data-reactid", "__next"]},
    "Next.js": {"scripts": ["_next/static", "_next/data"], "html_attrs": ["__next"]},
    "Vue.js": {"scripts": ["vue.min.js", "vue.js", "vue.runtime"], "html_attrs": ["data-v-", "v-cloak"]},
    "Nuxt.js": {"scripts": ["_nuxt/"], "html_attrs": ["__nuxt"]},
    "Angular": {"scripts": ["angular.min.js", "zone.js", "polyfills"], "html_attrs": ["ng-version", "ng-app", "_ngcontent"]},
    "Svelte": {"scripts": ["svelte"], "html_attrs": ["svelte-"]},
    # CSS Frameworks
    "Bootstrap": {"scripts": ["bootstrap.min.js", "bootstrap.bundle"], "links": ["bootstrap.min.css", "bootstrap.css"]},
    "Tailwind CSS": {"links": ["tailwind"], "html_classes": ["flex", "items-center", "bg-", "text-", "px-", "py-"]},
    "Material UI": {"scripts": ["material-ui", "@mui"], "links": ["material"]},
    # JS Libraries
    "jQuery": {"scripts": ["jquery.min.js", "jquery-", "jquery.js"]},
    "GSAP": {"scripts": ["gsap.min.js", "gsap", "greensock"]},
    "Three.js": {"scripts": ["three.min.js", "three.js"]},
    "Lodash": {"scripts": ["lodash.min.js", "lodash.js"]},
    "D3.js": {"scripts": ["d3.min.js", "d3.js", "d3.v"]},
    # Analytics
    "Google Analytics": {"scripts": ["google-analytics.com/analytics", "googletagmanager.com", "gtag/js", "ga.js"]},
    "Google Tag Manager": {"scripts": ["googletagmanager.com/gtm"]},
    "Facebook Pixel": {"scripts": ["connect.facebook.net/en_US/fbevents"]},
    "Hotjar": {"scripts": ["static.hotjar.com"]},
    "Mixpanel": {"scripts": ["cdn.mxpnl.com", "mixpanel"]},
    "Segment": {"scripts": ["cdn.segment.com"]},
    # CDN / Performance
    "Cloudflare": {"headers": ["cf-ray", "cf-cache-status", "server:cloudflare"]},
    "Fastly": {"headers": ["x-served-by", "x-fastly"]},
    "Akamai": {"headers": ["x-akamai"]},
    # Others
    "Google Fonts": {"links": ["fonts.googleapis.com", "fonts.gstatic.com"]},
    "Font Awesome": {"links": ["font-awesome", "fontawesome"], "scripts": ["fontawesome"]},
    "Stripe": {"scripts": ["js.stripe.com"]},
    "Intercom": {"scripts": ["widget.intercom.io"]},
    "Drift": {"scripts": ["js.driftt.com"]},
    "Crisp": {"scripts": ["client.crisp.chat"]},
    "HubSpot": {"scripts": ["js.hs-scripts.com", "hubspot"]},
    "Zendesk": {"scripts": ["static.zdassets.com"]},
    "reCAPTCHA": {"scripts": ["google.com/recaptcha"]},
}


def _detect_from_html(html: str, soup, response) -> dict[str, dict]:
    """Detect technologies from HTML content, headers, and parsed soup."""
    detected = {}
    html_lower = html.lower()
    all_scripts = " ".join(
        (tag.get("src", "") + " " + (tag.string or "")) for tag in soup.find_all("script")
    ).lower()
    all_links = " ".join(tag.get("href", "") for tag in soup.find_all("link")).lower()
    all_attrs = str(soup)
    headers_lower = {k.lower(): v.lower() for k, v in response.headers.items()}

    for tech_name, sigs in TECH_SIGNATURES.items():
        confidence = "Low"
        matches = []

        # Check script src / inline
        for pattern in sigs.get("scripts", []):
            if pattern.lower() in all_scripts:
                matches.append(f"script: {pattern}")

        # Check link href
        for pattern in sigs.get("links", []):
            if pattern.lower() in all_links:
                matches.append(f"link: {pattern}")

        # Check meta tags
        for i in range(0, len(sigs.get("meta", [])), 2):
            if i + 1 < len(sigs.get("meta", [])):
                attr_name = sigs["meta"][i]
                attr_val = sigs["meta"][i + 1]
                meta_tag = soup.find("meta", attrs={"name": attr_name})
                if meta_tag and attr_val in (meta_tag.get("content", "")).lower():
                    matches.append(f"meta[{attr_name}]")

        # Check HTML attributes
        for attr in sigs.get("html_attrs", []):
            if attr.lower() in all_attrs.lower():
                matches.append(f"attr: {attr}")

        # Check headers
        for hdr in sigs.get("headers", []):
            if ":" in hdr:
                key, val = hdr.split(":", 1)
                if key.strip() in headers_lower and val.strip() in headers_lower[key.strip()]:
                    matches.append(f"header: {hdr}")
            elif hdr in headers_lower:
                matches.append(f"header: {hdr}")

        if matches:
            if len(matches) >= 3:
                confidence = "High"
            elif len(matches) >= 2:
                confidence = "Medium"
            detected[tech_name] = {"confidence": confidence, "evidence": matches}

    # ── Extra detections ────────────────────────────
    # SSL
    if response.url.startswith("https"):
        detected["HTTPS/SSL"] = {"confidence": "High", "evidence": ["URL uses HTTPS"]}

    # Detect server from header
    server = headers_lower.get("server", "")
    if server:
        detected[f"Server: {response.headers.get('server', server)}"] = {
            "confidence": "High",
            "evidence": [f"Server header: {server}"],
        }

    # Detect X-Powered-By
    powered = headers_lower.get("x-powered-by", "")
    if powered:
        detected[f"Powered-By: {response.headers.get('X-Powered-By', powered)}"] = {
            "confidence": "High",
            "evidence": [f"X-Powered-By: {powered}"],
        }

    # Detect Open Graph
    og_tags = soup.find_all("meta", property=re.compile(r"^og:"))
    if og_tags:
        detected["Open Graph"] = {
            "confidence": "High",
            "evidence": [f"{len(og_tags)} OG tags found"],
        }

    # Detect Schema.org / JSON-LD
    ld_scripts = soup.find_all("script", type="application/ld+json")
    if ld_scripts:
        detected["Schema.org / JSON-LD"] = {
            "confidence": "High",
            "evidence": [f"{len(ld_scripts)} structured data blocks"],
        }

    return detected


def _format_results(detected: dict[str, dict], url: str) -> str:
    """Format detected technologies into a readable report."""
    lines = [f"TECHNOLOGY DETECTION REPORT — {url}", "=" * 60, ""]

    categories = {
        "CMS / Framework": ["WordPress", "Shopify", "Wix", "Squarespace", "Drupal", "Joomla"],
        "JavaScript Framework": ["React", "Next.js", "Vue.js", "Nuxt.js", "Angular", "Svelte"],
        "CSS Framework": ["Bootstrap", "Tailwind CSS", "Material UI"],
        "JavaScript Library": ["jQuery", "GSAP", "Three.js", "Lodash", "D3.js"],
        "Analytics & Tracking": ["Google Analytics", "Google Tag Manager", "Facebook Pixel", "Hotjar", "Mixpanel", "Segment"],
        "CDN & Performance": ["Cloudflare", "Fastly", "Akamai"],
        "UI & Design": ["Google Fonts", "Font Awesome"],
        "Third-Party Services": ["Stripe", "Intercom", "Drift", "Crisp", "HubSpot", "Zendesk", "reCAPTCHA"],
        "SEO & Metadata": ["Open Graph", "Schema.org / JSON-LD"],
        "Security": ["HTTPS/SSL"],
    }

    for cat_name, tech_names in categories.items():
        found = [(t, detected[t]) for t in tech_names if t in detected]
        # Also include server/powered-by in their own section
        if cat_name == "CDN & Performance":
            for key in detected:
                if key.startswith("Server:") or key.startswith("Powered-By:"):
                    found.append((key, detected[key]))

        if found:
            lines.append(f"### {cat_name}")
            for name, info in found:
                lines.append(f"  • {name}  [Confidence: {info['confidence']}]")
                lines.append(f"    Evidence: {', '.join(info['evidence'])}")
            lines.append("")

    total = len(detected)
    lines.append(f"TOTAL TECHNOLOGIES DETECTED: {total}")
    return "\n".join(lines)


async def detect(url: str) -> str:
    """Main entry point: scrape the page then optionally ask AI for a summary."""
    resp = await asyncio.to_thread(fetch_page, url)
    if resp is None:
        return f"Error: Could not fetch {url}. Check the URL and try again."

    soup = parse_html(resp.text)
    detected = _detect_from_html(resp.text, soup, resp)
    report_text = _format_results(detected, url)

    # Only call AI if we want a polished summary on top of raw detection
    if len(detected) >= 3:
        try:
            summary = await asyncio.to_thread(
                ask_ai,
                "You are a web technology analyst. Given a raw technology detection report, "
                "add brief SEO impact notes for each detected technology and provide 3-5 "
                "actionable recommendations. Keep it concise.",
                f"Here is the detection report:\n\n{report_text}\n\nAdd SEO impact notes and recommendations.",
                1500,
            )
            return report_text + "\n\n" + "─" * 60 + "\nAI ANALYSIS & SEO IMPACT\n" + "─" * 60 + "\n\n" + summary
        except Exception:
            pass  # If AI fails, return raw report

    return report_text
