"""SERP Rank Tracker — Uses AI to analyze keyword rankings."""

import asyncio
from .ai_client import ask_ai


SYSTEM_PROMPT = """You are an SEO SERP rank analysis tool. You will be given a target URL and keywords.

For EACH keyword, analyze and report:
KEYWORD: [keyword]
RANK: [estimated position or "Not found in top 50"]
PAGE: [which Google page]
SNIPPET: [likely title/snippet if found]
COMPETING_URLS: [3-5 URLs likely ranking above target]
---

After all keywords provide:
SUMMARY:
- Overall visibility score (0-100)
- Quick wins
- Recommendations per keyword"""


async def analyze(url: str, keywords: list[str]) -> str:
    kw_list = ", ".join(f'"{k}"' for k in keywords if k.strip())
    user_msg = (
        f"Target URL: {url}\n"
        f"Keywords to check: {kw_list}\n\n"
        "Analyze where the target URL likely ranks for each keyword based on your "
        "knowledge of the web. Check each keyword and report rankings."
    )
    return await asyncio.to_thread(ask_ai, SYSTEM_PROMPT, user_msg)
