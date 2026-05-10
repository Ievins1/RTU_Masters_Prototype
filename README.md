# Generative AI-Assisted Automation of API Specification and Documentation
- Thesis author: Rihards Ievins
- Scientific supervisor: Oksana Nikiforova

## Used directories
 - backend: Contains everything related to backend functionality including AI integration
 - frontend: Contains everything related to frontend functionality

 ## Requirements
- Docker must be installed on the local machine
- Docker Compose must be available
- A `.env` file must be created in the project root directory

## Environment configuration
Create a `.env` file in the main project directory and define the required environment variables there.

Example structure:

```env
APP_ENV=development
BACKEND_PORT=8000
FRONTEND_PORT=8080

OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5.4
OPENAI_FAST_MODEL=gpt-5.4-mini

ANTHROPIC_API_KEY=your_anthropic_api_key
ANTHROPIC_BALANCED_MODEL=claude-sonnet-4-6
ANTHROPIC_FAST_MODEL=claude-haiku-4-5
ANTHROPIC_ADVANCED_MODEL=claude-opus-4-6
```

## Running the prototype
To build and start the prototype, run the following command in the main project directory:

```bash
docker compose up --build
```

After the containers are launched and running open in browser: `http://localhost:8080`

 
## Testing scenario results
In thesis 4th chapter was defined used tests and their results. Results are available in two files:
- `4_Testing_results.xlsx` - as regulas Excel (.xlsx) file
- `4_Testing_results_2.csv` - as .csv file