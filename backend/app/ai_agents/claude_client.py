import json
from typing import Any, Dict, Optional, Tuple

from anthropic import Anthropic
from anthropic import APIError

from app.ai_agents.internal import build_extraction_prompt, strip_code_fences
from app.config import Settings


def extract_with_claude(
    settings: Settings,
    selection: Dict[str, str],
    input_type: str,
    preprocessing_result: Dict[str, Any],
    raw_content: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Extract API structure through the official Anthropic SDK."""
    if not settings.anthropic_api_key:
        return None, None

    client = Anthropic(
        api_key=settings.anthropic_api_key,
        timeout=settings.anthropic_timeout_seconds,
    )

    prompt = build_extraction_prompt(
        input_type,
        selection["model"],
        preprocessing_result,
        raw_content,
        settings.anthropic_context_char_limit,
    )

    try:
        message = client.messages.create(
            model=selection["model"],
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        text_parts = [block.text for block in message.content if getattr(block, "type", "") == "text"]
        content = strip_code_fences("\n".join(text_parts))
        return json.loads(content), None
    except (APIError, json.JSONDecodeError, TimeoutError) as exc:
        return None, str(exc)
