from typing import Any, Dict, Optional, Tuple

from app.ai_agents.claude_client import extract_with_claude
from app.ai_agents.internal import resolve_model_choice
from app.ai_agents.openai_client import extract_with_openai
from app.config import Settings


def maybe_extract_with_llm(
    settings: Settings,
    input_type: str,
    model_choice: str,
    preprocessing_result: Dict[str, Any],
    raw_content: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Route extraction to the selected AI provider and model."""
    selection = resolve_model_choice(settings, model_choice)

    if selection["provider"] == "openai":
        return extract_with_openai(settings, selection, input_type, preprocessing_result, raw_content)

    if selection["provider"] == "anthropic":
        return extract_with_claude(settings, selection, input_type, preprocessing_result, raw_content)

    return None, f"Unsupported model choice: {model_choice}"
