from typing import Any, Dict, List

from openapi_spec_validator import validate_spec
from openapi_spec_validator.validation.exceptions import OpenAPIValidationError


def validate_openapi(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Validate OpenAPI structure and collect additional semantic warnings."""
    schema_errors: List[str] = []
    semantic_warnings: List[str] = []

    try:
        validate_spec(spec)
    except OpenAPIValidationError as exc:
        schema_errors.append(str(exc))

    if "paths" not in spec or not spec["paths"]:
        semantic_warnings.append("No API paths were generated.")

    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            for parameter in operation.get("parameters", []):
                if parameter["in"] == "path" and f"{{{parameter['name']}}}" not in path:
                    semantic_warnings.append(
                        f"Path parameter '{parameter['name']}' is declared for {method.upper()} {path} but not present in the path template."
                    )

            if not operation.get("operationId"):
                semantic_warnings.append(f"Operation {method.upper()} {path} is missing operationId.")

    return {
        "valid": not schema_errors,
        "schema_errors": schema_errors,
        "semantic_warnings": semantic_warnings,
    }
