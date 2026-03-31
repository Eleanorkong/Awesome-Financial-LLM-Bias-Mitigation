"""Multi-provider LLM client using LiteLLM + Instructor for structured outputs."""

from __future__ import annotations

import asyncio
import os
from typing import TypeVar

import instructor
import litellm
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# Suppress litellm debug logs
litellm.set_verbose = False

# Retry config for rate limits
MAX_RATE_LIMIT_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 10


# ---------------------------------------------------------------------------
# Supported model presets (user can also enter custom model strings)
# ---------------------------------------------------------------------------

MODEL_PRESETS: dict[str, list[str]] = {
    "Anthropic": [
        "anthropic/claude-sonnet-4-6",
        "anthropic/claude-opus-4-6",
        "anthropic/claude-sonnet-4-5",
        "anthropic/claude-haiku-4-5",
    ],
    "OpenAI": [
        "openai/gpt-5.4",
        "openai/gpt-5.4-mini",
        "openai/gpt-4.1",
        "openai/gpt-4.1-mini",
        "openai/gpt-4.1-nano",
        "openai/o4-mini",
        "openai/o3",
        "openai/o3-pro",
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
    ],
    "Google": [
        "gemini/gemini-2.5-pro",
        "gemini/gemini-2.5-flash",
        "gemini/gemini-2.5-flash-lite",
        "gemini/gemini-3.1-pro-preview",
        "gemini/gemini-3-flash-preview",
    ],
    "Ollama (Local)": [
        "ollama/qwen3",
        "ollama/deepseek-r1",
        "ollama/phi4-reasoning",
        "ollama/llama3.3",
        "ollama/qwen2.5",
        "ollama/mistral-large",
    ],
}


def get_env_key_name(provider: str) -> str | None:
    """Return the environment variable name for the given provider's API key."""
    mapping = {
        "Anthropic": "ANTHROPIC_API_KEY",
        "OpenAI": "OPENAI_API_KEY",
        "Google": "GEMINI_API_KEY",
    }
    return mapping.get(provider)


def set_api_key(provider: str, key: str) -> None:
    """Set the API key for a provider in the environment."""
    env_name = get_env_key_name(provider)
    if env_name and key:
        os.environ[env_name] = key


async def structured_completion(
    model: str,
    system_prompt: str,
    user_prompt: str,
    response_model: type[T],
    temperature: float = 0.1,
    max_retries: int = 2,
) -> T:
    """Call an LLM and parse the response into a Pydantic model.

    Includes automatic retry with exponential backoff for rate limit errors.
    """
    is_gemini = "gemini" in model.lower()

    # Gemini: use JSON mode (not TOOLS) and merge system into user message
    # because Gemini handles system role inconsistently
    mode = instructor.Mode.JSON if is_gemini else instructor.Mode.TOOLS
    client = instructor.from_litellm(litellm.acompletion, mode=mode)

    if is_gemini:
        messages = [
            {"role": "user", "content": f"{system_prompt}\n\n---\n\n{user_prompt}"},
        ]
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    for attempt in range(MAX_RATE_LIMIT_RETRIES):
        try:
            return await client.chat.completions.create(
                model=model,
                messages=messages,
                response_model=response_model,
                temperature=temperature,
                max_retries=max_retries,
            )
        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = "rate_limit" in err_str or "429" in str(e) or "quota" in err_str
            if is_rate_limit and attempt < MAX_RATE_LIMIT_RETRIES - 1:
                wait = INITIAL_BACKOFF_SECONDS * (2 ** attempt)
                print(f"Rate limited, retrying in {wait}s (attempt {attempt + 1})...")
                await asyncio.sleep(wait)
            else:
                raise
