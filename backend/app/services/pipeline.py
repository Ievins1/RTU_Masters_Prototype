import re
from typing import Any, Dict, List, Tuple

import yaml

from app.ai_agents import maybe_extract_with_llm
from app.config import Settings
from app.schemas import GenerateRequest
from app.services.docs import build_markdown_docs
from app.services.openapi_builder import build_openapi_spec
from app.services.preprocess import KNOWN_FIELDS, ascii_slug, preprocess_input
from app.services.validator import validate_openapi


def _pluralize_resource(resource: str) -> str:
    """Convert a singular resource hint into a simple plural path segment."""
    if resource.endswith("js"):
        return resource[:-1] + "i"
    if resource.endswith("s") or resource.endswith("i"):
        return resource
    return f"{resource}s"


def _infer_type(name: str) -> str:
    """Infer a basic OpenAPI type from a known field name."""
    return KNOWN_FIELDS.get(name.lower(), "string")


def _operation_id(method: str, path: str) -> str:
    """Create a stable operationId from an HTTP method and path."""
    clean = path.strip("/").replace("{", "").replace("}", "").replace("/", "_").replace("-", "_")
    clean = clean or "root"
    return f"{method.lower()}_{clean}"


def _extract_fields_from_sentence(sentence: str) -> List[Dict[str, Any]]:
    """Extract quoted or explicitly marked field-like identifiers from text."""
    candidates = re.findall(r"`([^`]+)`|\"([^\"]+)\"|'([^']+)'", sentence)
    fields = []
    seen = set()
    for candidate_group in candidates:
        candidate = next(part for part in candidate_group if part)
        slug = ascii_slug(candidate).replace("-", "_")
        if not slug or slug in seen:
            continue
        if re.fullmatch(r"[a-z_][a-z0-9_]*", slug):
            fields.append(
                {
                    "name": slug,
                    "type": _infer_type(slug),
                    "required": True,
                    "description": f"Explicit field identifier found in input: {candidate}",
                }
            )
            seen.add(slug)
    return fields


def _extract_explicit_method(sentence: str) -> str:
    """Read an explicit HTTP method from a sentence when present."""
    match = re.search(r"\b(GET|POST|PUT|PATCH|DELETE)\b", sentence, flags=re.IGNORECASE)
    return match.group(1).upper() if match else "POST"


def _extract_explicit_path(sentence: str, index: int) -> str:
    """Read an explicit API path from text or fall back to a generic one."""
    match = re.search(r"(/[A-Za-z0-9_\-/{}/:]+)", sentence)
    if match:
        return match.group(1).replace(":id", "{id}")
    return f"/operations/{index}"


def _extract_path_params(path: str) -> List[Dict[str, Any]]:
    """Extract path parameter definitions from a path template."""
    params = []
    names = re.findall(r"{([^}]+)}", path)
    for name in names:
        params.append(
            {
                "name": name,
                "type": "integer" if name.lower() == "id" else "string",
                "required": True,
                "description": f"Path parameter {name}.",
            }
        )
    return params


def _fallback_from_requirements(preprocessed: Dict[str, Any]) -> Dict[str, Any]:
    """Build a minimal extraction result from requirements without LLM support."""
    endpoints = []

    for index, item in enumerate(preprocessed.get("sentences", []), start=1):
        method = _extract_explicit_method(item["sentence"])
        path = _extract_explicit_path(item["sentence"], index)
        path_params = _extract_path_params(path)
        body_params = _extract_fields_from_sentence(item["sentence"])
        response_fields = [{"name": "result", "type": "string", "description": "Generated operation result"}]

        if method == "GET":
            body_params = []
        if method == "DELETE":
            body_params = []
            response_fields = []

        endpoint = {
            "path": path,
            "method": method,
            "summary": f"Requirement-derived operation {index}",
            "description": (
                "Generated from natural-language input without model-based semantic extraction. "
                f"Original sentence: {item['sentence']}"
            ),
            "operation_id": _operation_id(method, path),
            "path_params": path_params,
            "query_params": [],
            "body_params": body_params,
            "response_fields": response_fields or [{"name": "message", "type": "string", "description": "Operation result"}],
        }
        endpoints.append(endpoint)

    return {
        "is_api_related": True,
        "reason": "Fallback mode assumes the user intends to describe API-related behavior.",
        "summary": "Language-agnostic fallback extraction from requirements text.",
        "assumptions": ["The input is interpreted as API-related because the fallback mode cannot classify intent robustly."],
        "warnings": [],
        "endpoints": endpoints,
    }


def _fallback_from_code(preprocessed: Dict[str, Any]) -> Dict[str, Any]:
    """Build a minimal extraction result from code without LLM support."""
    endpoints = []
    routes = preprocessed.get("routes", [])

    if routes:
        for route in routes:
            path = route["path"]
            method = route["method"]
            path_params = []
            for name in re.findall(r"{([^}]+)}|:([A-Za-z_]\w*)", path):
                param_name = next(part for part in name if part)
                path_params.append(
                    {
                        "name": param_name,
                        "type": "integer" if param_name == "id" else "string",
                        "required": True,
                        "description": f"Path parameter extracted from source code: {param_name}",
                    }
                )

            endpoints.append(
                {
                    "path": path.replace(":id", "{id}"),
                    "method": method,
                    "summary": f"{method} {path}",
                    "description": "Generated from detected route definition in source code.",
                    "operation_id": _operation_id(method, path),
                    "path_params": path_params,
                    "query_params": [],
                    "body_params": [] if method == "GET" else [{"name": "payload", "type": "string", "required": False, "description": "Request payload"}],
                    "response_fields": [{"name": "message", "type": "string", "description": "Operation result"}],
                }
            )

    if not endpoints:
        functions = preprocessed.get("functions", [])
        for function in functions[:3]:
            name = ascii_slug(function["name"]).replace("-", "_")
            path = f"/{name}"
            body_params = []
            for raw_arg in [part.strip() for part in function.get("arguments", "").split(",") if part.strip() and part.strip() != "self"]:
                arg_name = raw_arg.split(":")[0].split("=")[0].strip()
                if not arg_name:
                    continue
                body_params.append(
                    {
                        "name": arg_name,
                        "type": _infer_type(arg_name),
                        "required": "=" not in raw_arg,
                        "description": f"Parameter extracted from function signature: {arg_name}",
                    }
                )
            endpoints.append(
                {
                    "path": path,
                    "method": "POST",
                    "summary": f"Invoke {function['name']}",
                    "description": "Generated from function signature analysis.",
                    "operation_id": _operation_id("POST", path),
                    "path_params": [],
                    "query_params": [],
                    "body_params": body_params,
                    "response_fields": [{"name": "result", "type": "string", "description": "Function result"}],
                }
            )

    return {
        "is_api_related": True,
        "reason": "Fallback code analysis detected route or function structures that may represent API behavior.",
        "summary": "Fallback heuristic extraction from source code.",
        "assumptions": [],
        "warnings": [],
        "endpoints": endpoints,
    }


def _fallback_extraction(input_type: str, preprocessed: Dict[str, Any]) -> Dict[str, Any]:
    """Choose the correct fallback extraction strategy for the input type."""
    if input_type == "requirements":
        return _fallback_from_requirements(preprocessed)
    return _fallback_from_code(preprocessed)


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    """Remove duplicate warning strings while preserving the original order."""
    seen = set()
    result = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def _non_api_result(preprocessing: Dict[str, Any]) -> Dict[str, Any]:
    """Build a minimal extraction result for inputs rejected before AI generation."""
    classification = preprocessing.get("relevance_classification", {})
    reason = classification.get("reason", "The input was classified as non-API-related.")
    return {
        "is_api_related": False,
        "reason": reason,
        "summary": "No API specification was generated because the input does not appear to describe API behavior.",
        "assumptions": [],
        "warnings": [reason],
        "endpoints": [],
    }


def run_pipeline(request: GenerateRequest, settings: Settings) -> Tuple[Dict[str, Any], bool, str | None]:
    """Execute preprocessing, extraction, generation, validation, and documentation steps."""
    preprocessing = preprocess_input(request.input_type, request.content)
    relevance = preprocessing.get("relevance_classification", {}).get("relevance")

    llm_result = None
    llm_error = None
    if relevance == "non_api":
        extracted = _non_api_result(preprocessing)
    else:
        llm_result, llm_error = maybe_extract_with_llm(
            settings,
            request.input_type,
            request.model_choice,
            preprocessing,
            request.content,
        )
        extracted = llm_result or _fallback_extraction(request.input_type, preprocessing)
    extracted.setdefault("is_api_related", True)
    extracted.setdefault("reason", "")
    extracted.setdefault("summary", "Generated API extraction result.")
    extracted.setdefault("assumptions", [])
    extracted.setdefault("warnings", [])
    extracted.setdefault("endpoints", [])

    spec = build_openapi_spec(extracted, request.api_title, request.api_version, "http://localhost:8000")
    validation = validate_openapi(spec)

    if not extracted.get("is_api_related", True):
        validation["semantic_warnings"].append(
            f"Input classified as non-API-related. Reason: {extracted.get('reason') or 'No reason provided.'}"
        )

    for warning in extracted.get("warnings", []):
        validation["semantic_warnings"].append(warning)

    for assumption in extracted.get("assumptions", []):
        validation["semantic_warnings"].append(f"Assumption: {assumption}")

    if request.input_type == "requirements" and llm_result is None:
        validation["semantic_warnings"].append(
            "Natural-language semantic extraction is limited without an LLM configuration. "
            "The fallback only uses explicit HTTP methods, route-like paths, and quoted identifiers."
        )

    validation["semantic_warnings"] = _dedupe_preserve_order(validation["semantic_warnings"])
    documentation = build_markdown_docs(spec)
    yaml_output = yaml.safe_dump(spec, sort_keys=False, allow_unicode=True)

    response = {
        "preprocessing": preprocessing,
        "extracted_elements": extracted,
        "openapi_spec": spec,
        "openapi_yaml": yaml_output,
        "documentation_markdown": documentation,
        "validation": validation,
        "llm_used": llm_result is not None,
        "llm_error": llm_error,
    }
    return response, llm_result is not None, llm_error
