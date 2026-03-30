from typing import Any, Dict, List


def build_markdown_docs(spec: Dict[str, Any]) -> str:
    info = spec.get("info", {})
    lines: List[str] = [
        f"# {info.get('title', 'Generated API')}",
        "",
        info.get("description", ""),
        "",
        "## Endpoints",
        "",
    ]

    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            lines.append(f"### `{method.upper()} {path}`")
            lines.append("")
            lines.append(operation.get("summary", ""))
            if operation.get("description"):
                lines.append("")
                lines.append(operation["description"])
            if operation.get("parameters"):
                lines.append("")
                lines.append("| Parameter | In | Type | Required | Description |")
                lines.append("|---|---|---|---|---|")
                for parameter in operation["parameters"]:
                    lines.append(
                        f"| {parameter['name']} | {parameter['in']} | {parameter['schema'].get('type', 'string')} | "
                        f"{'yes' if parameter['required'] else 'no'} | {parameter.get('description', '')} |"
                    )
            if operation.get("requestBody"):
                lines.append("")
                lines.append("Request body is expected in `application/json` format.")
            lines.append("")

    return "\n".join(lines).strip() + "\n"

