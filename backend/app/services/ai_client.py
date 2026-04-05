import json
import re
from typing import Any, Dict, Optional, Tuple

from openai import OpenAI
from openai import OpenAIError

from app.config import Settings


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences from model output before JSON parsing."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
    return text.strip()


def _truncate_text(value: str, limit: int) -> str:
    """Trim long text so the model receives only the most relevant leading context."""
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "\n...[truncated]"


def _compact_preprocessing_result(preprocessing_result: Dict[str, Any]) -> Dict[str, Any]:
    """Shrink preprocessing output into a lightweight summary for the model prompt."""
    if "sentences" in preprocessing_result:
        return {
            "sentence_count": preprocessing_result.get("sentence_count", 0),
            "steps": preprocessing_result.get("steps", []),
            "sentences": preprocessing_result.get("sentences", [])[:8],
        }

    return {
        "line_count": preprocessing_result.get("line_count", 0),
        "steps": preprocessing_result.get("steps", []),
        "routes": preprocessing_result.get("routes", [])[:10],
        "functions": preprocessing_result.get("functions", [])[:10],
        "classes": preprocessing_result.get("classes", [])[:10],
    }


def maybe_extract_with_llm(
    settings: Settings,
    input_type: str,
    generation_mode: str,
    preprocessing_result: Dict[str, Any],
    raw_content: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Call OpenAI to classify the input and extract API structure when configured."""
    if not settings.openai_api_key or not settings.openai_model:
        return None, None

    client = OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
    )

    compact_preprocessing = _compact_preprocessing_result(preprocessing_result)
    compact_content = _truncate_text(raw_content, settings.openai_context_char_limit)
    selected_model = settings.openai_fast_model if generation_mode == "fast" else settings.openai_model
    effective_input_type = preprocessing_result.get("detected_input_type", input_type)

    input_text = (
        "<task>\n"
        "Analyze the provided content and extract API design information for later OpenAPI generation.\n"
        "First decide whether the content is actually API-related.\n"
        "</task>\n\n"
        "<decision_policy>\n"
        "1. If the content is not about API behavior, is too vague, or is only a general question, set is_api_related=false.\n"
        "2. When is_api_related=false, do not invent endpoints, keep endpoints empty, explain the reason briefly, and add at most one warning.\n"
        "3. When is_api_related=true, extract only details that are explicit or strongly implied.\n"
        "4. Use standard REST normalization when appropriate without treating it as a warning by default.\n"
        "5. Do not add warnings for normal conventions such as plural resource paths, standard CRUD mapping, or using /{id} when the text clearly says 'by id'.\n"
        "6. Add assumptions or warnings only when the ambiguity materially changes the API contract.\n"
        "7. Keep assumptions and warnings short and few. Prefer empty arrays over noisy commentary.\n"
        "</decision_policy>\n\n"
        "<extraction_rules>\n"
        "- Prefer REST-style resources and HTTP methods.\n"
        "- Distinguish path/query parameters from request body fields.\n"
        "- Use PUT for update operations unless the source clearly indicates partial update semantics, in which case use PATCH.\n"
        "- If response fields are not fully specified, return only the most defensible fields.\n"
        "- Write summaries and descriptions in the same language as the input.\n"
        "</extraction_rules>\n\n"
        "<output_contract>\n"
        "Return only valid JSON with exactly this shape:\n"
        "{\n"
        '  "is_api_related": boolean,\n'
        '  "reason": string,\n'
        '  "summary": string,\n'
        '  "assumptions": [string],\n'
        '  "warnings": [string],\n'
        '  "endpoints": [\n'
        "    {\n"
        '      "path": string,\n'
        '      "method": "GET"|"POST"|"PUT"|"PATCH"|"DELETE",\n'
        '      "summary": string,\n'
        '      "description": string,\n'
        '      "operation_id": string,\n'
        '      "path_params": [{"name": string, "type": string, "required": true, "description": string}],\n'
        '      "query_params": [{"name": string, "type": string, "required": boolean, "description": string}],\n'
        '      "body_params": [{"name": string, "type": string, "required": boolean, "description": string}],\n'
        '      "response_fields": [{"name": string, "type": string, "description": string}]\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "</output_contract>\n\n"
        "<context>\n"
        f"Requested input type: {input_type}\n\n"
        f"Detected input type: {effective_input_type}\n\n"
        f"Generation mode: {generation_mode}\n\n"
        "Preprocessing result:\n"
        f"{json.dumps(compact_preprocessing, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "Original content:\n"
        f"{compact_content}\n"
        "</context>\n"
    )

    try:
        response = client.responses.create(
            model=selected_model,
            input=input_text,
        )
        content = _strip_code_fences(response.output_text or "")
        return json.loads(content), None
    except (OpenAIError, json.JSONDecodeError, TimeoutError) as exc:
        return None, str(exc)
