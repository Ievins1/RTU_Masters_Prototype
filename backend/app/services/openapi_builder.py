from copy import deepcopy
from typing import Any, Dict, List


def _schema_for_type(type_name: str) -> Dict[str, Any]:
    """Map a simple extracted type name to an OpenAPI schema snippet."""
    normalized = (type_name or "string").lower()
    if normalized in {"int", "integer"}:
        return {"type": "integer"}
    if normalized in {"float", "double", "number", "decimal"}:
        return {"type": "number"}
    if normalized in {"bool", "boolean"}:
        return {"type": "boolean"}
    if normalized in {"array", "list"}:
        return {"type": "array", "items": {"type": "string"}}
    return {"type": "string"}


def _build_component_schema(name: str, fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build an object schema from extracted field metadata."""
    properties = {}
    required = []
    for field in fields:
        properties[field["name"]] = {
            **_schema_for_type(field.get("type", "string")),
            "description": field.get("description", ""),
        }
        if field.get("required"):
            required.append(field["name"])

    schema: Dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def build_openapi_spec(extracted: Dict[str, Any], title: str, version: str, server_url: str) -> Dict[str, Any]:
    """Convert extracted API elements into a full OpenAPI document."""
    spec: Dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": title,
            "version": version,
            "description": extracted.get("summary") or "OpenAPI specification generated from requirements or source code.",
        },
        "servers": [{"url": server_url}],
        "paths": {},
        "components": {"schemas": {}},
    }

    for endpoint in extracted.get("endpoints", []):
        path = endpoint["path"]
        method = endpoint["method"].lower()
        path_item = spec["paths"].setdefault(path, {})

        parameters = []
        for location_key, location in (("path_params", "path"), ("query_params", "query")):
            for item in endpoint.get(location_key, []):
                parameters.append(
                    {
                        "name": item["name"],
                        "in": location,
                        "required": item.get("required", location == "path"),
                        "description": item.get("description", ""),
                        "schema": _schema_for_type(item.get("type", "string")),
                    }
                )

        operation: Dict[str, Any] = {
            "summary": endpoint.get("summary", "").strip() or endpoint["operation_id"],
            "description": endpoint.get("description", "").strip() or endpoint.get("summary", ""),
            "operationId": endpoint["operation_id"],
            "parameters": parameters,
            "responses": {},
        }

        body_params = endpoint.get("body_params", [])
        if body_params:
            schema_name = f"{endpoint['operation_id']}Request"
            spec["components"]["schemas"][schema_name] = _build_component_schema(schema_name, body_params)
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                    }
                },
            }

        response_fields = endpoint.get("response_fields") or [{"name": "message", "type": "string", "description": "Operation result"}]
        response_schema_name = f"{endpoint['operation_id']}Response"
        response_fields_with_required = [deepcopy(field) for field in response_fields]
        for field in response_fields_with_required:
            field.setdefault("required", True)
        spec["components"]["schemas"][response_schema_name] = _build_component_schema(response_schema_name, response_fields_with_required)

        status_code = "201" if endpoint["method"] == "POST" else "204" if endpoint["method"] == "DELETE" else "200"
        response_description = {
            "201": "Resource created successfully.",
            "204": "Resource deleted successfully.",
            "200": "Request completed successfully.",
        }[status_code]

        response_content = {}
        if status_code != "204":
            response_content = {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{response_schema_name}"}
                }
            }

        operation["responses"][status_code] = {
            "description": response_description,
            **({"content": response_content} if response_content else {}),
        }

        path_item[method] = operation

    return spec
