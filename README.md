# RTU_Masters_Prototype

Containerized prototype for AI-assisted OpenAPI specification and documentation generation

The application accepts a single input area and automatically detects whether the content is closer to:

1. Requirements text
2. Code fragment

The implemented processing flow is:

1. Input collection
2. Preprocessing
3. AI-based extraction of API elements
4. OpenAPI generation
5. Validation
6. Human-readable documentation generation

## Stack

- `backend`: FastAPI API for preprocessing, OpenAI interaction, OpenAPI generation, validation, and documentation generation
- `frontend`: static UI served by Nginx
- `docker-compose.yml`: launches the whole solution with Docker

## Environment

Set the following values in `.env`:

- `OPENAI_API_KEY`: your OpenAI API key
- `OPENAI_MODEL`: default OpenAI model, for example `gpt-5.4`
- `OPENAI_FAST_MODEL`: faster OpenAI model, for example `gpt-5.4-mini`
- `OPENAI_TIMEOUT_SECONDS`: OpenAI request timeout
- `ANTHROPIC_API_KEY`: your Anthropic API key
- `ANTHROPIC_BALANCED_MODEL`: balanced Claude model, for example `claude-sonnet-4-6`
- `ANTHROPIC_FAST_MODEL`: faster Claude model, for example `claude-haiku-4-5`
- `ANTHROPIC_ADVANCED_MODEL`: advanced Claude model, for example `claude-opus-4-6`
- `ANTHROPIC_TIMEOUT_SECONDS`: Anthropic request timeout

The backend supports both the official OpenAI Python SDK and the official Anthropic Python SDK.

If the selected provider is not configured, the system still runs, but it falls back to a much simpler heuristic mode. That fallback is mainly useful for structural testing, not for high-quality semantic extraction from natural language.

## Main Output

The system returns:

- generated OpenAPI specification in JSON and YAML form
- generated human-readable API documentation
- preprocessing details
- extracted API elements
- validation results

## Run

```bash
docker compose up --build
```

Frontend: `http://localhost:8080`

Backend health: `http://localhost:8000/health`

## Main Endpoint

The main backend endpoint is:

- `POST /api/v1/generate`

It accepts:

- `input_type`: `requirements` or `code`
- `model_choice`: selected OpenAI or Claude model profile
- `content`: user input
- `api_title`: title for the generated API
- `api_version`: version for the generated API

## Notes

- The backend automatically detects whether the submitted content looks like natural-language requirements or code and then uses the corresponding preprocessing branch.
- The `Documentation` tab in the UI displays documentation generated from the produced OpenAPI structure.
- For a backend file-by-file explanation, see [Explanation.md](/Users/rihardsievins/Documents/RTU%20-%20Magistrs/Magistra%20Darbs/Mag_prototips/RTU_Masters_Prototype/Explanation.md).
