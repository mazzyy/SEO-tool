"""Performance & Lighthouse — Uses Google PageSpeed Insights API (free) + AI summary."""

import asyncio
import httpx
from .ai_client import ask_ai

import os

PAGESPEED_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


async def _fetch_pagespeed(url: str, strategy: str = "mobile") -> tuple[dict | None, str | None]:
    """Call Google PageSpeed Insights API with optional API key."""
    api_key = os.getenv("GOOGLE_API_KEY")
    params = {
        "url": url,
        "strategy": strategy,
        "category": ["performance", "accessibility", "best-practices", "seo"],
    }
    if api_key:
        params["key"] = api_key

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(PAGESPEED_API, params=params)
            
            if resp.status_code == 200:
                return resp.json(), None
            elif resp.status_code == 429:
                return None, "Rate limit exceeded (429). Please add a GOOGLE_API_KEY to your backend/.env file to increase your quota."
            elif resp.status_code == 400:
                return None, f"Bad request (400). Google could not fetch the URL: {resp.text[:100]}"
            elif resp.status_code == 500:
                return None, "Google PageSpeed API internal server error (500)."
            else:
                return None, f"HTTP Error {resp.status_code} from PageSpeed API."
    except Exception as e:
        return None, f"Connection error: {str(e)}"
    return None, "Unknown error."


def _extract_metrics(data: dict) -> dict:
    """Extract key metrics from PageSpeed Insights response."""
    metrics = {}

    # Lighthouse scores
    cats = data.get("lighthouseResult", {}).get("categories", {})
    for cat_id, cat_data in cats.items():
        metrics[f"score_{cat_id}"] = round((cat_data.get("score", 0) or 0) * 100)

    # Core Web Vitals from field data
    loading = data.get("loadingExperience", {})
    field_metrics = loading.get("metrics", {})
    for metric_name, metric_data in field_metrics.items():
        percentile = metric_data.get("percentile")
        category = metric_data.get("category", "N/A")
        if percentile is not None:
            metrics[f"field_{metric_name}"] = {"value": percentile, "rating": category}

    # Lab data from Lighthouse
    audits = data.get("lighthouseResult", {}).get("audits", {})
    lab_metrics = {
        "first-contentful-paint": "FCP",
        "largest-contentful-paint": "LCP",
        "total-blocking-time": "TBT",
        "cumulative-layout-shift": "CLS",
        "speed-index": "Speed Index",
        "interactive": "TTI",
        "server-response-time": "TTFB",
    }
    for audit_id, label in lab_metrics.items():
        audit_data = audits.get(audit_id, {})
        if audit_data:
            metrics[f"lab_{label}"] = {
                "value": audit_data.get("displayValue", "N/A"),
                "score": round((audit_data.get("score", 0) or 0) * 100),
            }

    # Opportunities (areas for improvement)
    opportunities = []
    for audit_id, audit_data in audits.items():
        if audit_data.get("details", {}).get("type") == "opportunity":
            saving = audit_data.get("details", {}).get("overallSavingsMs", 0)
            if saving and saving > 0:
                opportunities.append({
                    "title": audit_data.get("title", audit_id),
                    "savings_ms": round(saving),
                    "description": audit_data.get("description", "")[:120],
                })

    opportunities.sort(key=lambda x: x["savings_ms"], reverse=True)
    metrics["opportunities"] = opportunities[:10]

    return metrics


def _format_metrics(url: str, mobile: dict | None, desktop: dict | None) -> str:
    lines = [f"PERFORMANCE ANALYSIS — {url}", "=" * 60]

    for strategy, data in [("MOBILE", mobile), ("DESKTOP", desktop)]:
        if not data:
            lines.append(f"\n### {strategy}: ❌ Could not fetch data")
            continue

        lines.append(f"\n### {strategy} SCORES")
        for key in ["score_performance", "score_accessibility", "score_best-practices", "score_seo"]:
            if key in data:
                score = data[key]
                label = key.replace("score_", "").replace("-", " ").title()
                emoji = "🟢" if score >= 90 else "🟡" if score >= 50 else "🔴"
                lines.append(f"  {emoji} {label}: {score}/100")

        # Lab metrics
        lines.append(f"\n  LAB METRICS:")
        for key, val in data.items():
            if key.startswith("lab_"):
                label = key.replace("lab_", "")
                score = val.get("score", 0)
                emoji = "🟢" if score >= 90 else "🟡" if score >= 50 else "🔴"
                lines.append(f"    {emoji} {label}: {val['value']} (score: {score})")

        # Field metrics
        field_found = False
        for key, val in data.items():
            if key.startswith("field_"):
                if not field_found:
                    lines.append(f"\n  FIELD DATA (Real Users):")
                    field_found = True
                label = key.replace("field_", "")
                lines.append(f"    {label}: {val['value']} ({val['rating']})")

        if not field_found:
            lines.append(f"\n  FIELD DATA: No real-user data available")

        # Opportunities
        if data.get("opportunities"):
            lines.append(f"\n  TOP OPTIMIZATION OPPORTUNITIES:")
            for opp in data["opportunities"][:5]:
                lines.append(f"    ⚡ {opp['title']} — save ~{opp['savings_ms']}ms")

    return "\n".join(lines)


SYSTEM_PROMPT = """You are a web performance optimization expert. Given a PageSpeed Insights performance report,
provide actionable recommendations. Focus on:

1. Core Web Vitals improvement strategies
2. Specific optimization steps for the worst-scoring areas
3. Quick wins vs long-term investments
4. Mobile vs desktop priority

Keep recommendations specific and actionable. Reference the actual scores and metrics provided."""


async def check(url: str) -> str:
    # Fetch both mobile and desktop data in parallel
    mobile_result, desktop_result = await asyncio.gather(
        _fetch_pagespeed(url, "mobile"),
        _fetch_pagespeed(url, "desktop"),
    )

    mobile_data, mobile_err = mobile_result
    desktop_data, desktop_err = desktop_result

    mobile_metrics = _extract_metrics(mobile_data) if mobile_data else None
    desktop_metrics = _extract_metrics(desktop_data) if desktop_data else None

    # If both failed, return a single descriptive error
    if mobile_metrics is None and desktop_metrics is None:
        err_msg = mobile_err or desktop_err or "Unknown error."
        return (
            f"Could not fetch performance data for {url}.\n\n"
            f"Error details: {err_msg}\n\n"
            "This can happen if:\n"
            "- The URL is not publicly accessible\n"
            "- Google's PageSpeed API is temporarily unavailable or hit a rate limit\n"
            "- The page takes too long to load\n\n"
            "Please verify the URL and your API keys, then try again."
        )

    # We might have partial data (e.g., mobile succeeded but desktop failed), which we handle here.
    report = _format_metrics(url, mobile_metrics, desktop_metrics)

    # AI only for recommendations summary
    try:
        ai_recs = await ask_ai(
            SYSTEM_PROMPT,
            f"Here is the performance report:\n\n{report}\n\n"
            "Provide specific, prioritized recommendations to improve these scores.",
            1500,
        )
        return report + "\n\n" + "─" * 60 + "\nAI RECOMMENDATIONS\n" + "─" * 60 + "\n\n" + ai_recs
    except Exception:
        return report
