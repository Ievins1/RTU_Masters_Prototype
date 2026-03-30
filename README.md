# RTU_Masters_Prototype

Containerized prototype for AI-assisted OpenAPI specification and documentation generation

The application supports two main input modes:

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
- `OPENAI_MODEL`: model name, for example `gpt-5.4`
- `OPENAI_TIMEOUT_SECONDS`: request timeout for the SDK client

The backend uses the official OpenAI Python SDK and the Responses API.

If OpenAI variables are not provided, the system still runs, but it falls back to a much simpler heuristic mode. That fallback is mainly useful for structural testing, not for high-quality semantic extraction from natural language.

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
- `content`: user input
- `api_title`: title for the generated API
- `api_version`: version for the generated API

## Notes

- Requirements text and code fragments are currently processed through different preprocessing branches.
- The `Documentation` tab in the UI displays documentation generated from the produced OpenAPI structure.
- For a backend file-by-file explanation, see [Explanation.md](/Users/rihardsievins/Documents/RTU%20-%20Magistrs/Magistra%20Darbs/Mag_prototips/RTU_Masters_Prototype/Explanation.md).
