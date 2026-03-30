import json
import re
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI
from openai import OpenAIError

from app.config import Settings


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
    return text.strip()


def maybe_extract_with_llm(
    settings: Settings,
    input_type: str,
    preprocessing_result: Dict[str, Any],
    raw_content: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not settings.openai_api_key or not settings.openai_model:
        return None, None

    client = OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
    )

    input_text = (
        "You are extracting API design elements for OpenAPI generation.\n"
        "Return only valid JSON with this shape:\n"
        "{\n"
        '  "summary": string,\n'
        '  "endpoints": [\n'
        "    {\n"
        '      "path": string,\n'
        '      "method": "GET"|"POST"|"PUT"|"PATCH"|"DELETE",\n'
        '      "summary": string,\n'
        '      "description": string,\n'
        '      "operation_id": string,\n'
        '      "path_params": [{"name": string, "type": string, "required": true, "description": string}],\n'
        '      "query_params": [{"name": string, "type": string, "required": bool, "description": string}],\n'
        '      "body_params": [{"name": string, "type": string, "required": bool, "description": string}],\n'
        '      "response_fields": [{"name": string, "type": string, "description": string}]\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Prefer REST-style paths. Use the input language as needed, but keep the JSON structure exact.\n\n"
        f"Input type: {input_type}\n"
        f"Preprocessing result:\n{json.dumps(preprocessing_result, ensure_ascii=False, indent=2)}\n\n"
        f"Original content:\n{raw_content}\n"
    )

    try:
        response = client.responses.create(
            model=settings.openai_model,
            input=input_text,
        )
        content = _strip_code_fences(response.output_text or "")
        return json.loads(content), None
    except (OpenAIError, json.JSONDecodeError, TimeoutError) as exc:
        return None, str(exc)
