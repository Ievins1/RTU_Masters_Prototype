import re
import unicodedata
from typing import Any, Dict, List

KNOWN_FIELDS = {
    "id": "integer",
    "email": "string",
    "name": "string",
    "password": "string",
    "description": "string",
    "amount": "number",
    "price": "number",
    "active": "boolean",
}


def ascii_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")


def normalize_text(content: str) -> str:
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t]+", " ", content).strip()


def split_sentences(content: str) -> List[str]:
    return [segment.strip() for segment in re.split(r"(?<=[.!?])\s+|\n+", content) if segment.strip()]


def tokenize(sentence: str) -> List[str]:
    cleaned = re.sub(r"[^\w\s/-]", " ", sentence.lower(), flags=re.UNICODE)
    return [token for token in cleaned.split() if token]


def lemmatize_token(token: str) -> str:
    return ascii_slug(token)


def preprocess_requirements(content: str) -> Dict[str, Any]:
    normalized = normalize_text(content)
    sentences = split_sentences(normalized)
    structured_sentences = [
        {
            "sentence": sentence,
            "tokens": tokenize(sentence),
            "normalized_tokens": [lemmatize_token(token) for token in tokenize(sentence)],
        }
        for sentence in sentences
    ]

    return {
        "normalized_text": normalized,
        "sentence_count": len(sentences),
        "sentences": structured_sentences,
        "steps": [
            "text normalization",
            "sentence segmentation",
            "tokenization",
            "structured representation",
        ],
    }


ROUTE_PATTERNS = [
    re.compile(r"@(?:app|router)\.(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]"),
    re.compile(r"(?:app|router)\.(get|post|put|patch|delete)\(['\"]([^'\"]+)['\"]"),
]


def preprocess_code(content: str) -> Dict[str, Any]:
    normalized = normalize_text(content)
    lines = [line for line in normalized.split("\n") if line.strip()]
    discovered_routes: List[Dict[str, str]] = []

    for line in lines:
        for pattern in ROUTE_PATTERNS:
            match = pattern.search(line)
            if not match:
                continue
            if pattern.pattern.startswith("@"):
                method, path = match.group(1).upper(), match.group(2)
            else:
                method, path = match.group(1).upper(), match.group(2)
            discovered_routes.append({"method": method, "path": path})

    function_signatures = re.findall(r"def\s+(\w+)\(([^)]*)\)", normalized)
    classes = re.findall(r"class\s+(\w+)", normalized)

    return {
        "normalized_text": normalized,
        "line_count": len(lines),
        "routes": discovered_routes,
        "functions": [{"name": name, "arguments": args} for name, args in function_signatures],
        "classes": classes,
        "steps": [
            "text normalization",
            "code structure scanning",
            "route detection",
            "function signature extraction",
            "structured representation",
        ],
    }


def preprocess_input(input_type: str, content: str) -> Dict[str, Any]:
    if input_type == "requirements":
        return preprocess_requirements(content)
    return preprocess_code(content)
