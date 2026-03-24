"""Thin wrapper around Azure OpenAI. Used only where AI reasoning is needed."""

import os
from openai import AzureOpenAI

_client = None


def _get_client() -> AzureOpenAI:
    global _client
    if _client is None:
        _client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        )
    return _client


def ask_ai(system_prompt: str, user_message: str, max_tokens: int = 4000) -> str:
    """Send a chat completion request and return the text response."""
    client = _get_client()
    response = client.chat.completions.create(
        model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content
