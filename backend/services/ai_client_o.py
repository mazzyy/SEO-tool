"""
Shared AI client for all services.
Exports: ask_ai(system_prompt, user_content) -> str
         ask_ai_json(system_prompt, user_content) -> dict
Uses Azure OpenAI config from .env
"""

import os
import json
import logging

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

    if not api_key or not endpoint:
        logger.warning("Azure OpenAI not configured — AI features disabled")
        return None

    try:
        from openai import AzureOpenAI
        _client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-06-01"),
        )
        return _client
    except Exception as e:
        logger.warning(f"Could not init Azure OpenAI client: {e}")
        return None


async def ask_ai(system_prompt: str, user_content: str, max_tokens: int = 800) -> str:
    """
    Send a prompt to Azure OpenAI and return the text response.
    Returns empty string if AI is not configured or fails.
    """
    client = _get_client()
    if not client:
        return ""

    try:
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
        resp = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.warning(f"ask_ai failed: {e}")
        return ""


async def ask_ai_json(system_prompt: str, user_content: str, max_tokens: int = 800) -> dict:
    """
    Send a prompt to Azure OpenAI and parse the response as JSON.
    The system_prompt should instruct the model to return valid JSON.
    Returns empty dict if AI is not configured, fails, or returns invalid JSON.
    """
    client = _get_client()
    if not client:
        return {}

    try:
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
        resp = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        text = resp.choices[0].message.content or ""

        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning(f"ask_ai_json: invalid JSON response: {e}")
        return {}
    except Exception as e:
        logger.warning(f"ask_ai_json failed: {e}")
        return {}
