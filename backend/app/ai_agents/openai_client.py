import json
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI
from openai import OpenAIError

from app.ai_agents.internal import build_extraction_prompt, strip_code_fences
from app.config import Settings


def extract_with_openai(
    settings: Settings,
    selection: Dict[str, str],
    input_type: str,
    preprocessing_result: Dict[str, Any],
    raw_content: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Extract API structure through the official OpenAI SDK."""
    if not settings.openai_api_key:
        return None, None

    client = OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
    )

    prompt = build_extraction_prompt(
        input_type,
        selection["model"],
        preprocessing_result,
        raw_content,
        settings.openai_context_char_limit,
    )

    try:
        response = client.responses.create(
            model=selection["model"],
            input=prompt,
        )
        content = strip_code_fences(response.output_text or "")
        return json.loads(content), None
    except (OpenAIError, json.JSONDecodeError, TimeoutError) as exc:
        return None, str(exc)
