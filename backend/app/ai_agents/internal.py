import json
import re
from typing import Any, Dict

from app.config import Settings


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences from model output before JSON parsing."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
    return text.strip()


def truncate_text(value: str, limit: int) -> str:
    """Trim long text so the model receives only the most relevant leading context."""
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "\n...[truncated]"


def compact_preprocessing_result(preprocessing_result: Dict[str, Any]) -> Dict[str, Any]:
    """Shrink preprocessing output into a lightweight summary for the model prompt."""
    if "sentences" in preprocessing_result:
        return {
            "requested_input_type": preprocessing_result.get("requested_input_type"),
            "detected_input_type": preprocessing_result.get("detected_input_type"),
            "sentence_count": preprocessing_result.get("sentence_count", 0),
            "steps": preprocessing_result.get("steps", []),
            "sentences": preprocessing_result.get("sentences", [])[:8],
        }

    return {
        "requested_input_type": preprocessing_result.get("requested_input_type"),
        "detected_input_type": preprocessing_result.get("detected_input_type"),
        "line_count": preprocessing_result.get("line_count", 0),
        "steps": preprocessing_result.get("steps", []),
        "routes": preprocessing_result.get("routes", [])[:10],
        "functions": preprocessing_result.get("functions", [])[:10],
        "classes": preprocessing_result.get("classes", [])[:10],
    }


def build_extraction_prompt(
    input_type: str,
    model_choice: str,
    preprocessing_result: Dict[str, Any],
    raw_content: str,
    context_limit: int,
) -> str:
    """Build the shared extraction prompt for supported AI providers."""
    compact_preprocessing = compact_preprocessing_result(preprocessing_result)
    compact_content = truncate_text(raw_content, context_limit)
    effective_input_type = preprocessing_result.get("detected_input_type", input_type)

    return (
        "<system_role>\n"
        "You are an API analysis assistant used in a method for generating OpenAPI specifications from requirements text or code fragments.\n"
        "Your job is to transform the input into a structured, OpenAPI-ready intermediate result.\n"
        "Be conservative, explicit, and faithful to the source.\n"
        "</system_role>\n\n"
        "<method>\n"
        "Follow these stages in order:\n"
        "Stage 1: classify whether the input is API-related.\n"
        "Stage 2: identify API operations, resources, parameters, request data, and likely response fields.\n"
        "Stage 3: normalize them into REST-oriented structures only when the normalization is strongly justified.\n"
        "Stage 4: record uncertainty as assumptions or warnings instead of inventing unsupported details.\n"
        "</method>\n\n"
        "<classification_rules>\n"
        "Treat the input as API-related only if it describes endpoints, operations, resources, requests, responses, data exchange, controller logic, route definitions, or backend functionality that clearly implies an API.\n"
        "If the input is a general question, arithmetic, casual conversation, or a domain statement without API behavior, set is_api_related=false.\n"
        "If is_api_related=false, do not invent endpoints, keep endpoints empty, explain briefly in reason, and keep warnings minimal.\n"
        "</classification_rules>\n\n"
        "<extraction_rules>\n"
        "Extract only information that is explicit or strongly implied.\n"
        "Prefer REST semantics when the source describes CRUD-like operations.\n"
        "Use plural resource paths when a clear resource can be inferred, but do not treat standard REST normalization as a warning by default.\n"
        "If the source says 'by id' or clearly refers to a single entity identifier, model it as a path parameter.\n"
        "Use POST for create, GET for retrieval, DELETE for deletion, and PUT for update unless the source clearly indicates partial update semantics, in which case use PATCH.\n"
        "Keep path/query parameters separate from request body fields.\n"
        "If response fields are incomplete, include only the most defensible fields.\n"
        "Write summary and description texts in the same language as the input.\n"
        "</extraction_rules>\n\n"
        "<uncertainty_policy>\n"
        "Use assumptions only when a reasonable implementation choice is necessary to complete the structure.\n"
        "Use warnings only when ambiguity materially affects the API contract or when the input is too weak for confident extraction.\n"
        "Do not produce noisy or repetitive assumptions/warnings.\n"
        "Prefer empty arrays over commentary that adds little value.\n"
        "</uncertainty_policy>\n\n"
        "<few_shot_examples>\n"
        "Example A input: 'What is 2+2?'\n"
        "Example A output pattern: is_api_related=false, endpoints=[]\n\n"
        "Example B input: 'User creates a profile with name, email and password. User gets profile by id.'\n"
        "Example B output pattern: is_api_related=true with a POST profile endpoint and a GET profile-by-id endpoint.\n\n"
        "Example C input: '@app.get(\"/orders/{id}\")\\ndef get_order(id: str): ...'\n"
        "Example C output pattern: is_api_related=true with a GET /orders/{id} endpoint and id path parameter.\n"
        "</few_shot_examples>\n\n"
        "<output_contract>\n"
        "Return only valid JSON with exactly this structure and no extra keys:\n"
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
        f"Selected model choice: {model_choice}\n\n"
        "Preprocessing result:\n"
        f"{json.dumps(compact_preprocessing, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "Original content:\n"
        f"{compact_content}\n"
        "</context>\n"
    )


def resolve_model_choice(settings: Settings, model_choice: str) -> Dict[str, str]:
    """Map a UI model choice to the provider and concrete model name."""
    catalog = {
        "gpt_default": {"provider": "openai", "model": settings.openai_model},
        "gpt_fast": {"provider": "openai", "model": settings.openai_fast_model},
        "claude_balanced": {"provider": "anthropic", "model": settings.anthropic_balanced_model},
        "claude_fast": {"provider": "anthropic", "model": settings.anthropic_fast_model},
        "claude_advanced": {"provider": "anthropic", "model": settings.anthropic_advanced_model},
    }
    return catalog.get(model_choice, catalog["gpt_default"])
