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
    """Normalize text into a lowercase ASCII slug for stable identifiers."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_only.lower()).strip("-")


def normalize_text(content: str) -> str:
    """Clean line endings and repeated spaces before further processing."""
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t]+", " ", content).strip()


def split_sentences(content: str) -> List[str]:
    """Split normalized text into sentence-like units."""
    return [segment.strip() for segment in re.split(r"(?<=[.!?])\s+|\n+", content) if segment.strip()]


def tokenize(sentence: str) -> List[str]:
    """Break a sentence into simplified tokens."""
    cleaned = re.sub(r"[^\w\s/-]", " ", sentence.lower(), flags=re.UNICODE)
    return [token for token in cleaned.split() if token]


def lemmatize_token(token: str) -> str:
    """Reduce a token to a normalized slug form."""
    return ascii_slug(token)


def preprocess_requirements(content: str) -> Dict[str, Any]:
    """Prepare natural-language requirements for model analysis."""
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
    """Prepare source code input by extracting routes and structural hints."""
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
        "detected_input_type": "code",
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


def detect_input_type(content: str) -> str:
    """Heuristically detect whether the input looks more like code or requirements text."""
    normalized = normalize_text(content)

    strong_code_markers = [
        r"@(?:app|router)\.(?:get|post|put|patch|delete)\(",
        r"\bdef\s+\w+\(",
        r"\bclass\s+\w+",
        r"\b(?:const|let|var|function)\s+\w+",
        r"\b(?:public|private|protected)\s+\w+",
        r"\{[^{}]*\}",
    ]

    score = 0
    for pattern in strong_code_markers:
        if re.search(pattern, normalized):
            score += 1

    if normalized.count("\n") >= 3 and any(symbol in normalized for symbol in ["(", ")", "{", "}", ";"]):
        score += 1

    return "code" if score >= 2 else "requirements"


def classify_input_relevance(content: str, detected_input_type: str) -> Dict[str, str]:
    """Classify only clearly non-API input locally and leave the rest to the model."""
    normalized = normalize_text(content)
    lowered = normalized.lower()

    non_api_patterns = [
        r"^\s*what\s+is\s+\d+\s*[\+\-\*/]\s*\d+\s*\??\s*$",
        r"^\s*\d+\s*[\+\-\*/]\s*\d+\s*=?\s*$",
        r"^\s*hello[!.]?\s*$",
        r"^\s*hi[!.]?\s*$",
        r"^\s*hey[!.]?\s*$",
        r"^\s*thanks?[!.]?\s*$",
    ]

    if detected_input_type == "code":
        return {
            "relevance": "uncertain",
            "reason": "The input looks like code and should be evaluated by the model.",
        }

    if any(re.match(pattern, lowered) for pattern in non_api_patterns):
        return {
            "relevance": "non_api",
            "reason": "The input looks like a general question or arithmetic expression rather than an API description.",
        }

    if len(normalized) <= 3:
        return {
            "relevance": "non_api",
            "reason": "The input is too short to evaluate as an API description.",
        }

    return {
        "relevance": "uncertain",
        "reason": "The input should be evaluated by the model instead of local hardcoded rules.",
    }


def preprocess_input(input_type: str, content: str) -> Dict[str, Any]:
    """Dispatch preprocessing based on the selected input type."""
    effective_input_type = detect_input_type(content) if input_type == "auto" else input_type

    if effective_input_type == "requirements":
        result = preprocess_requirements(content)
    else:
        result = preprocess_code(content)

    result["relevance_classification"] = classify_input_relevance(content, effective_input_type)
    result["detected_input_type"] = effective_input_type
    result["requested_input_type"] = input_type
    return result
