from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.schemas import GenerateRequest, GenerateResponse
from app.services.pipeline import run_pipeline

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Prototype implementing the thesis section 3 workflow for AI-assisted OpenAPI generation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    """Return a simple health response for container and service checks."""
    return {"status": "ok", "environment": settings.app_env}


@app.post("/api/v1/generate", response_model=GenerateResponse)
def generate_specification(request: GenerateRequest) -> dict:
    """Run the full generation pipeline for the submitted input."""
    response, _, _ = run_pipeline(request, settings)
    return response
