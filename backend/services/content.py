"""Content Analysis — Programmatic readability & keyword analysis + AI for quality."""

import asyncio
import re
from collections import Counter
from .scraper import fetch_page, parse_html
from .ai_client import ask_ai

try:
    import textstat
    HAS_TEXTSTAT = True
except ImportError:
    HAS_TEXTSTAT = False


def _extract_content(soup) -> dict:
    """Extract and analyze page content."""
    data = {}

    # Remove script/style elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # Get main text
    text = soup.get_text(separator=" ", strip=True)
    data["full_text"] = text
    data["word_count"] = len(text.split())
    data["char_count"] = len(text)

    # Sentence count
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    data["sentence_count"] = len(sentences)

    # Paragraph count (from original soup)
    paragraphs = soup.find_all("p")
    data["paragraph_count"] = len(paragraphs)

    # Average sentence length
    if sentences:
        avg_words = sum(len(s.split()) for s in sentences) / len(sentences)
        data["avg_sentence_length"] = round(avg_words, 1)
    else:
        data["avg_sentence_length"] = 0

    # Readability scores
    if HAS_TEXTSTAT and len(text) > 100:
        data["flesch_reading_ease"] = textstat.flesch_reading_ease(text)
        data["flesch_kincaid_grade"] = textstat.flesch_kincaid_grade(text)
        data["gunning_fog"] = textstat.gunning_fog(text)
        data["automated_readability"] = textstat.automated_readability_index(text)
        data["reading_time_min"] = round(data["word_count"] / 200, 1)
    else:
        data["reading_time_min"] = round(data["word_count"] / 200, 1)

    # Heading structure
    headings = []
    for level in range(1, 7):
        for tag in soup.find_all(f"h{level}"):
            headings.append({"level": level, "text": tag.get_text(strip=True)[:80]})
    data["headings"] = headings

    # Lists
    data["list_count"] = len(soup.find_all(["ul", "ol"]))

    # Links
    remaining_soup = soup  # After decomposing nav/header/footer
    links = remaining_soup.find_all("a", href=True)
    internal = [l for l in links if not l["href"].startswith("http") or l["href"].startswith("/")]
    external = [l for l in links if l["href"].startswith("http")]
    data["internal_links"] = len(internal)
    data["external_links"] = len(external)

    return data


def _analyze_keywords(text: str, target_keywords: str = "") -> dict:
    """Analyze keyword density and distribution."""
    # Clean text
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    total = len(words)
    if total == 0:
        return {"total_words": 0}

    # Stop words to exclude
    stop_words = {
        "the", "and", "for", "are", "but", "not", "you", "all", "can", "had", "her",
        "was", "one", "our", "out", "has", "have", "been", "from", "this", "that",
        "they", "with", "will", "each", "make", "like", "into", "them", "than",
        "most", "some", "very", "when", "what", "your", "more", "about", "which",
        "their", "would", "there", "been", "other", "also", "just", "only", "could",
        "those", "after", "these",
    }

    filtered = [w for w in words if w not in stop_words]
    word_freq = Counter(filtered).most_common(20)

    kw_data = {
        "total_words": total,
        "top_words": [{"word": w, "count": c, "density": round(c / total * 100, 2)} for w, c in word_freq],
    }

    # Check target keywords
    if target_keywords.strip():
        targets = [kw.strip().lower() for kw in target_keywords.split(",") if kw.strip()]
        kw_data["target_analysis"] = []
        text_lower = text.lower()
        for kw in targets:
            count = text_lower.count(kw)
            kw_words = len(kw.split())
            density = round(count / (total / kw_words) * 100, 2) if total > 0 else 0
            kw_data["target_analysis"].append({
                "keyword": kw,
                "occurrences": count,
                "density": density,
                "in_headings": any(kw in h["text"].lower() for h in []),
            })

    return kw_data


def _format_content_report(url: str, content_data: dict, kw_data: dict) -> str:
    lines = [f"CONTENT ANALYSIS REPORT — {url}", "=" * 60]

    lines.append(f"\n### CONTENT METRICS")
    lines.append(f"  Word Count: {content_data['word_count']}")
    lines.append(f"  Character Count: {content_data['char_count']}")
    lines.append(f"  Sentences: {content_data['sentence_count']}")
    lines.append(f"  Paragraphs: {content_data['paragraph_count']}")
    lines.append(f"  Avg Sentence Length: {content_data['avg_sentence_length']} words")
    lines.append(f"  Reading Time: ~{content_data['reading_time_min']} minutes")
    lines.append(f"  Lists: {content_data['list_count']}")
    lines.append(f"  Internal Links: {content_data['internal_links']}")
    lines.append(f"  External Links: {content_data['external_links']}")

    # Readability
    if "flesch_reading_ease" in content_data:
        fre = content_data["flesch_reading_ease"]
        if fre >= 80:
            level = "Easy (6th grade)"
        elif fre >= 60:
            level = "Standard (8th-9th grade)"
        elif fre >= 40:
            level = "Difficult (college)"
        else:
            level = "Very Difficult (graduate)"

        lines.append(f"\n### READABILITY SCORES")
        lines.append(f"  Flesch Reading Ease: {fre} — {level}")
        lines.append(f"  Flesch-Kincaid Grade: {content_data['flesch_kincaid_grade']}")
        lines.append(f"  Gunning Fog Index: {content_data['gunning_fog']}")
        lines.append(f"  Automated Readability: {content_data['automated_readability']}")

    # Heading structure
    if content_data["headings"]:
        lines.append(f"\n### HEADING STRUCTURE")
        for h in content_data["headings"][:15]:
            indent = "  " * h["level"]
            lines.append(f"  {indent}H{h['level']}: {h['text']}")

    # Keyword analysis
    lines.append(f"\n### KEYWORD DENSITY (Top 20)")
    for kw in kw_data.get("top_words", []):
        bar = "█" * min(int(kw["density"] * 10), 20)
        lines.append(f"  {kw['word']:20s} {kw['count']:4d}x ({kw['density']}%) {bar}")

    # Target keyword analysis
    if kw_data.get("target_analysis"):
        lines.append(f"\n### TARGET KEYWORD ANALYSIS")
        for tk in kw_data["target_analysis"]:
            status = "✅" if tk["occurrences"] > 0 else "❌"
            lines.append(f"  {status} \"{tk['keyword']}\": {tk['occurrences']} occurrences ({tk['density']}%)")
            if tk["density"] > 3:
                lines.append(f"      ⚠️ Possible keyword stuffing (> 3%)")
            elif tk["density"] < 0.5 and tk["occurrences"] > 0:
                lines.append(f"      ⚠️ Low density, consider increasing usage")
            elif tk["occurrences"] == 0:
                lines.append(f"      ⚠️ Keyword not found — consider adding it")

    return "\n".join(lines)


SYSTEM_PROMPT = """You are an SEO content strategist. Given a programmatic content analysis report,
provide expert analysis of:

1. Content Quality Assessment (E-E-A-T score estimate)
2. Content gaps compared to typical top-ranking pages for this niche
3. Semantic keyword suggestions (LSI keywords)
4. Featured snippet opportunities
5. Content improvement recommendations (specific rewrites, additions)

Be specific and reference the actual data. Keep it actionable."""


async def analyze(url: str, target_keywords: str = "") -> str:
    resp = await asyncio.to_thread(fetch_page, url)
    if resp is None:
        return f"Error: Could not fetch {url}. Check the URL and try again."

    soup = parse_html(resp.text)
    content_data = _extract_content(soup)
    kw_data = _analyze_keywords(content_data.get("full_text", ""), target_keywords)

    report = _format_content_report(url, content_data, kw_data)

    # AI for quality analysis and gap recommendations
    ai_analysis = await ask_ai(
        SYSTEM_PROMPT,
        f"Content analysis:\n\n{report}\n\n"
        f"First 500 chars of page content: {content_data.get('full_text', '')[:500]}\n\n"
        "Provide quality assessment, content gaps, and optimization recommendations.",
        2500,
    )

    return report + "\n\n" + "─" * 60 + "\nAI CONTENT STRATEGY\n" + "─" * 60 + "\n\n" + ai_analysis
