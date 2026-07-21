# Kindred AI

**Kindred AI** is a voice-first care companion prototype for older adults. It turns simple everyday requests into safe, understandable support: medication tracking, refill awareness, suspicious-message checks, family communication, household reminders, and factual web research.

The experience is intentionally calm and English-only. Anita speaks naturally; Kindred decides which specialist agent should handle the request and gives one concise, reassuring reply.

> This is a hackathon prototype. Calls, messages, orders, and purchases are recorded locally only. Kindred is not medical advice, emergency support, or a production authentication system.

## What it demonstrates

- Voice input with a clear review-and-send step and consistent text-to-speech output.
- A senior-friendly React Care Hub, family-admin page, local demo login, large guided actions, and live care information.
- Medication schedules, taken/missed dose tracking, stock awareness, and refill-request recording.
- Security inbox analysis: phone messages are stored, classified by an LLM, and elevated to alerts when suspicious.
- A phone book plus friendly family call/message requests.
- Household inventory, purchase-request recording, and reminders that appear and speak while the Care Hub is open.
- Live public-information answers through a dedicated research boundary.
- Langfuse tracing for agent routing, model calls, and MCP-backed workflows.

## Architecture

```text
User (voice or text)
        |
        v
Master Agent  — the only user-facing voice
        |
        v
Router Agent  — structured intent and field extraction
        |
        +--> Guardian  --> Health MCP, Security MCP, Inventory MCP
        +--> Companion --> Memory MCP, Communication MCP
        +--> Logistics --> Inventory MCP
        +--> Research  --> Tavily remote MCP
```

Agent definitions, instructions, capabilities, and permitted MCP servers are startup-validated from [`agents.yaml`](backend/src/kindred_ai/config/agents.yaml). The Router never talks to the user or calls tools; it returns a validated structured route. Python remains responsible for execution, confirmations, data access, and safety boundaries.

| Agent | Responsibility | Permitted MCP servers |
| --- | --- | --- |
| Master | Warm conversational voice and final response | None directly |
| Router | Structured classification and delegation | None |
| Guardian | Medicines, stock awareness, stored-message safety | Health, Security, Inventory |
| Companion | Memories, contacts, family messages and call requests | Memory, Communication |
| Logistics | Household stock, requests, reminders | Inventory |
| Research | Read-only current public information | Tavily |

More detail, including tool input schemas, is in [MCP_TOOL_CATALOG.md](MCP_TOOL_CATALOG.md).

## Technology

- **Frontend:** React, TypeScript, Vite
- **Backend:** Python 3.13+, FastAPI, Pydantic
- **Agent intelligence:** OpenAI Responses API; the local configuration currently uses `gpt-5.6-luna` for specialist and routing work
- **Voice:** browser speech recognition plus OpenAI speech generation
- **MCP:** FastMCP, with in-process transport for local development and optional HTTP server URLs
- **Data:** SQLite and versioned SQL migrations; no ORM
- **Observability:** Langfuse
- **Research:** Tavily hosted remote MCP

## Local setup

### Prerequisites

- Python 3.13+
- Node.js 18+
- An OpenAI API key
- Optional: Tavily and Langfuse keys for live research and observability

### 1. Configure local secrets

Copy the safe template, then add your own keys. Never commit `backend/.env`.

```powershell
Copy-Item backend\.env.example backend\.env
```

Required values:

```env
OPENAI_API_KEY=your_key_here
OPENAI_MODEL_MASTER=gpt-realtime-1.5
OPENAI_MODEL_AGENTS=gpt-5.6-luna
KINDRED_ENABLE_LLM=true
```

Optional values include `TAVILY_API_KEY` and the `LANGFUSE_*` settings shown in [`backend/.env.example`](backend/.env.example).

### 2. Install dependencies

```powershell
uv sync
Set-Location frontend
npm install
Set-Location ..
```

### 3. Start the API

From the repository root:

```powershell
$env:PYTHONPATH = "$PWD\backend\src"
.\.venv\Scripts\python.exe -m uvicorn kindred_ai.presentation.api.app:create_app --factory --reload --port 8000
```

The FastAPI documentation and test endpoints are at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

### 4. Start the frontend

In a second terminal:

```powershell
Set-Location frontend
npm run dev
```

Open the Vite URL shown in the terminal, normally [http://localhost:5173](http://localhost:5173).

### Demo login

```text
Username: anita
Password: kindred-demo
```

The login is intentionally local to the browser using `sessionStorage`. It is included only to make the prototype demo feel realistic; it is not authentication.

## Test path

1. Start the backend and frontend using the commands above.
2. Sign in as Anita.
3. Open **Family Admin** to add a medication plan, medicine supply, trusted contact, personal date, or incoming phone message.
4. Return to the Care Hub and try these requests:

   - “What is my next medicine?”
   - “I forgot my 8 AM medicines.”
   - “Is there any spam message today?”
   - “Please ask my son to call me.”
   - “Remind me to call my mechanic at 10 PM.”

For security testing, add a message such as: `URGENT: Your bank account is blocked. Send the verification code from your phone now.` The Security workflow stores and analyses it, then exposes the result through the Care Hub and Swagger endpoints.

## Tests

Backend tests use isolated temporary SQLite databases and do not use the local demo database:

```powershell
$env:PYTHONPATH = "$PWD\backend\src"
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
```

Build the frontend:

```powershell
Set-Location frontend
npm run build
```

## Safety and prototype boundaries

- No real phone call, text message, purchase, medicine order, or emergency escalation is performed.
- The admin page directly populates local prototype data so judges can test workflows quickly.
- Security analysis is for stored simulated phone messages only. General fraud questions receive general advice and do not create inbox records.
- Medication records are a prototype aid, not clinical advice. Missed-dose guidance directs the user to the medicine leaflet, pharmacist, or clinician.
- Data is local SQLite runtime data under `backend/data/`, which is gitignored.
- Secrets are loaded only from ignored environment files and must never be sent to the frontend, logs, or source control.

## How Codex and GPT-5.6 contributed

This project was built through an iterative collaboration with Codex:

- Codex helped establish the clean architecture, package layout, SQLite migration strategy, FastAPI endpoints, FastMCP tool boundaries, React screens, and test suite.
- Codex accelerated debugging from real test feedback: voice input behavior, medication status versus next-dose logic, reminder delivery, structured Router schemas, contact resolution, LLM tool routing, and graceful handling of validation failures.
- Codex helped make the Care Hub more accessible by refining large actions, concise language, voice review, warm responses, and a family-admin testing workflow.
- GPT-5.6 Luna is used for the Router and specialist conversational intelligence. It interprets natural requests, extracts structured route fields, and creates clear English responses while Python enforces tool permissions and explicit-action safeguards.
- Langfuse was added to make the model, routing, agent, and MCP workflow visible during development and evaluation.

The result is not a generic chat interface: it is a deliberately bounded multi-agent care prototype where each agent has a defined responsibility and only the MCP access it needs.

## Repository guide

```text
backend/
  src/kindred_ai/
    agents/          Master, Router, Guardian, Companion, Logistics, Research
    application/     Use cases and ports
    config/          Validated agent catalog and model settings
    infrastructure/  SQLite repositories, OpenAI adapters, MCP clients, tracing
    mcp/             FastMCP server definitions
    presentation/    FastAPI routers and temporary interfaces
  tests/             Unit and integration tests
frontend/
  src/               React Care Hub and Family Admin interface
Requirement/         Product and usability requirements
Tests/               Demo material
```

## Further documentation

- [Architecture](backend/docs/architecture.md)
- [Agent test scenarios](backend/src/kindred_ai/agents/TEST_SCENARIOS.md)
- [MCP tool catalog](MCP_TOOL_CATALOG.md)
- [Project progress](PROJECT_TODO.md)
- [Usability and interaction specification](frontend/Usability%20%26%20Interaction%20Specification.md)

## License

This repository is provided for hackathon evaluation and demonstration. Add a formal license before using or distributing it beyond that scope.
