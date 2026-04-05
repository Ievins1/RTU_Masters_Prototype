from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    input_type: Literal["auto", "requirements", "code"] = "auto"
    model_choice: Literal["gpt_default", "gpt_fast", "claude_balanced", "claude_fast", "claude_advanced"] = "gpt_default"
    content: str = Field(min_length=1)
    api_title: str = Field(default="Generated API")
    api_version: str = Field(default="1.0.0")


class ValidationSummary(BaseModel):
    valid: bool
    schema_errors: List[str] = Field(default_factory=list)
    semantic_warnings: List[str] = Field(default_factory=list)


class GenerateResponse(BaseModel):
    preprocessing: Dict[str, Any]
    extracted_elements: Dict[str, Any]
    openapi_spec: Dict[str, Any]
    openapi_yaml: str
    documentation_markdown: str
    validation: ValidationSummary
    llm_used: bool
    llm_error: Optional[str] = None
