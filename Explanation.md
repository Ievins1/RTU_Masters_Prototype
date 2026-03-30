# Backend Explanation

This file explains every file inside the `backend` folder so it is easier to understand where each part of the logic lives and how the full processing flow works.

## High-Level Structure

The backend is organized into:

- container setup files
- dependency definition
- FastAPI application files
- service modules that implement the thesis logic

The main runtime flow is:

1. Request enters FastAPI
2. Request body is validated with Pydantic schemas
3. Input is preprocessed
4. OpenAI is called for structured API extraction
5. Fallback extraction is used if OpenAI is unavailable
6. OpenAPI specification is built
7. Specification is validated
8. Human-readable documentation is generated
9. Response is returned to the frontend

## File-by-File Explanation

### `backend/Dockerfile`

Purpose:
- Defines how the backend container is built.

What it does:
- Uses `python:3.12-slim` as the base image
- Sets `/app` as the working directory
- Copies `requirements.txt`
- Installs Python dependencies
- Copies the application source code
- Starts the FastAPI app with `uvicorn`

Why it matters:
- This is what makes the backend runnable inside Docker.

### `backend/requirements.txt`

Purpose:
- Lists Python dependencies needed by the backend.

Main packages:
- `fastapi`: API framework
- `uvicorn`: ASGI server for FastAPI
- `pydantic`: request/response validation
- `pydantic-settings`: environment variable loading from `.env`
- `PyYAML`: YAML export for OpenAPI
- `openapi-spec-validator`: OpenAPI validation
- `openai`: official OpenAI SDK

Why it matters:
- If something is missing here, the backend container cannot install or run correctly.

### `backend/app/__init__.py`

Purpose:
- Marks `app` as a Python package.

What it does:
- Nothing functionally by itself.

Why it matters:
- It allows imports like `from app.config import Settings`.

### `backend/app/config.py`

Purpose:
- Central configuration loading for the backend.

What it contains:
- `Settings` class
- `get_settings()` cached loader

Important fields:
- `app_name`
- `app_env`
- `app_host`
- `app_port`
- `cors_origins`
- `openai_api_key`
- `openai_model`
- `openai_timeout_seconds`

How it works:
- `Settings` inherits from `BaseSettings`
- `.env` values are loaded automatically
- for example:
  - `OPENAI_API_KEY` -> `openai_api_key`
  - `OPENAI_MODEL` -> `openai_model`

Why it matters:
- This is the single source of truth for environment-driven configuration.

### `backend/app/main.py`

Purpose:
- Entry point of the FastAPI application.

What it does:
- Loads settings
- Creates the FastAPI app
- Configures CORS
- Exposes `/health`
- Exposes `POST /api/v1/generate`

Important endpoint:
- `POST /api/v1/generate`

What happens there:
- Receives validated input
- Calls the pipeline
- Returns the full generation result

Why it matters:
- This is the backend’s public API surface.

### `backend/app/schemas.py`

Purpose:
- Defines request and response models for FastAPI.

Classes inside:
- `GenerateRequest`
- `ValidationSummary`
- `GenerateResponse`

What they do:
- `GenerateRequest` validates incoming frontend data
- `ValidationSummary` standardizes validation result format
- `GenerateResponse` defines the structure returned to the frontend

Why it matters:
- Keeps API request/response format explicit and safe.

### `backend/app/services/__init__.py`

Purpose:
- Marks the `services` folder as a Python package.

Why it matters:
- Allows service module imports cleanly.

### `backend/app/services/preprocess.py`

Purpose:
- Handles preprocessing of user input before AI extraction.

Main idea:
- Requirements text and code fragments are processed differently.

Important functions:
- `ascii_slug()`
- `normalize_text()`
- `split_sentences()`
- `tokenize()`
- `lemmatize_token()`
- `preprocess_requirements()`
- `preprocess_code()`
- `preprocess_input()`

Requirements path:
- Normalizes text
- Splits into sentences
- Tokenizes each sentence
- Produces a structured intermediate representation

Code path:
- Normalizes text
- Scans for route patterns like `@app.get(...)`
- Extracts function signatures
- Extracts classes

Why it matters:
- This is where the selected input type starts changing backend behavior.

### `backend/app/services/ai_client.py`

Purpose:
- Talks to OpenAI using the official Python SDK.

Main function:
- `maybe_extract_with_llm()`

What it does:
- Checks whether OpenAI config exists
- Builds the extraction prompt
- Sends the request using `OpenAI().responses.create(...)`
- Reads the model output
- Parses JSON from the model response

Important design point:
- The model is not given only raw user text
- it also receives:
  - input type
  - preprocessing result
  - original content

Why it matters:
- This is the AI-powered extraction layer of the system.

### `backend/app/services/openapi_builder.py`

Purpose:
- Converts extracted API elements into a real OpenAPI structure.

Important functions:
- `_schema_for_type()`
- `_build_component_schema()`
- `build_openapi_spec()`

What it does:
- Creates `openapi`, `info`, `servers`, `paths`, and `components`
- Maps parameters into OpenAPI parameter objects
- Maps body data into request body schemas
- Builds response schemas

Why it matters:
- This is where extracted API meaning becomes formal OpenAPI output.

### `backend/app/services/docs.py`

Purpose:
- Generates human-readable documentation from the OpenAPI specification.

Main function:
- `build_markdown_docs()`

What it does:
- Reads the OpenAPI structure
- Builds Markdown documentation
- Lists endpoints
- Lists summaries and descriptions
- Lists parameters in a table
- Notes request body usage

Why it matters:
- This file is the documentation-generation layer, not just specification generation.

### `backend/app/services/validator.py`

Purpose:
- Validates generated OpenAPI output.

Main function:
- `validate_openapi()`

What it does:
- Uses `openapi-spec-validator`
- Collects schema errors
- Adds semantic warnings for some consistency problems

Current examples of checks:
- missing or invalid OpenAPI structure
- missing paths
- path parameters declared but not present in path template
- missing `operationId`

Why it matters:
- This is the quality-control layer after OpenAPI generation.

### `backend/app/services/pipeline.py`

Purpose:
- Orchestrates the whole backend generation flow.

Main function:
- `run_pipeline()`

What it does in order:
- preprocesses input
- calls OpenAI extraction
- uses fallback extraction if needed
- builds OpenAPI spec
- validates the result
- generates Markdown documentation
- serializes YAML output
- returns the full result bundle

Other functions in this file:
- helper functions for fallback extraction
- fallback logic for `requirements`
- fallback logic for `code`

Important note:
- This file is effectively the backbone of the full thesis prototype logic.

## Practical Flow Example

If the user sends requirements text:

1. `main.py` receives the request
2. `schemas.py` validates it
3. `pipeline.py` starts the process
4. `preprocess.py` runs the requirements preprocessing branch
5. `ai_client.py` asks OpenAI to extract API elements
6. `openapi_builder.py` creates the OpenAPI document
7. `validator.py` validates it
8. `docs.py` creates Markdown documentation
9. `pipeline.py` returns all outputs

If the user sends code:

1. same first steps
2. `preprocess.py` uses the code branch instead
3. route and function information are extracted differently
4. the rest of the pipeline stays the same

## Which Files You Will Most Likely Edit Often

If you continue developing this prototype, these files are the most important:

- `backend/app/services/ai_client.py`
  - for prompt logic and OpenAI behavior
- `backend/app/services/preprocess.py`
  - for better input handling
- `backend/app/services/openapi_builder.py`
  - for OpenAPI structure improvements
- `backend/app/services/validator.py`
  - for stronger validation rules
- `backend/app/services/docs.py`
  - for richer documentation output
- `backend/app/services/pipeline.py`
  - for overall orchestration logic

## Short Summary

If you want to remember the backend simply:

- `config.py` = settings
- `main.py` = API entrypoint
- `schemas.py` = request/response shape
- `preprocess.py` = input preparation
- `ai_client.py` = OpenAI call
- `openapi_builder.py` = specification creation
- `validator.py` = specification validation
- `docs.py` = documentation generation
- `pipeline.py` = full workflow coordinator
