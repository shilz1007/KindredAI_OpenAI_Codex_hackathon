# Kindred AI Project Progress

Use `✅` for completed work and `⬜` for planned work. The prototype deliberately simulates calls, messages, orders, and notifications; it does not contact real people or services.

## Foundation

- ✅ Define the clean backend package structure and high-level architecture.
- ✅ Define and startup-validate the YAML agent catalog and MCP ownership mapping.
- ✅ Add FastAPI/Swagger endpoints for development and judge testing.
- ✅ Add automated backend tests for the implemented MCPs and agent workflows.
- ✅ Add a React prototype UI with a demo login, Elder/Caregiver views, and a temporary chat experience.
- ✅ Add a Judge/Admin sandbox for inserting simulated data through the real backend APIs.

## Agents

- ✅ Master Agent: English LLM-backed routing, delegation, and bounded in-memory conversation context.
- ✅ Guardian Agent: Security, Health, and medication-inventory workflows.
- ✅ Companion Agent: Memory-backed personalised responses and approved simulated family communication.
- ✅ Logistics Agent: Household-inventory workflows and persisted reminder orchestration.
- ⬜ Add Bengali instructions and language routing.
- ⬜ Persist multi-turn conversation state beyond the current in-memory prototype.
- ⬜ Introduce production-grade agent authorization and policy enforcement.

## MCPs and Persistence

### Memory MCP

- ✅ Isolated SQLite persistence, migrations, idempotent demo seed data, Swagger endpoints, and tests.
- ✅ Profile retrieval, approved memory storage, and conversation-history retrieval.
- ⬜ Add semantic/relevance-based retrieval.

### Health MCP

- ✅ Isolated SQLite persistence, migrations, idempotent demo seed data, Swagger endpoints, and tests.
- ✅ Medication schedules, daily dose times, taken-dose records, and health-event retrieval.
- ✅ Medication stock and seven-day replenishment-warning workflow through Guardian/Inventory.
- ⬜ Add clinical validation, patient onboarding, and per-user timezone support.

### Security MCP

- ✅ Simulated phone-message inbox stored separately from security events and alerts.
- ✅ GPT-5.1 structured classification of stored phone messages; medium, high, and critical results create alerts.
- ✅ Keep general fraud/cyber-safety questions with Master general intelligence rather than storing them as phone messages.
- ✅ Swagger endpoints and automated tests for the inbox and alerts.
- ⬜ Add a reviewed production safety policy, model evaluation set, and human escalation workflow.

### Inventory MCP

- ✅ Medication inventory: quantities, purchase dates, reorder status, confirmed replenishment requests, tests, and Swagger endpoints.
- ✅ Separate household inventory and confirmed household purchase requests for Logistics.
- ⬜ Add supplier/pharmacy integrations only after explicit authorization and safety controls are designed.

### Communication MCP

- ✅ Local SQLite phone book with seeded son/daughter contacts.
- ✅ Simulated approved family-message queue and call-request records.
- ✅ Companion Swagger endpoints for contacts, phone book, messages, and call requests.
- ⬜ Add real message/call delivery only with consent, authentication, and an approved provider.

## Experience, Testing, and Observability

- ✅ Temporary Gradio harnesses for early Master/Guardian testing.
- ✅ React UI for ongoing prototype testing, including a judge-facing Admin data-entry page.
- ✅ OpenAI Responses integration for text conversation and a temporary Realtime WebSocket voice test.
- ✅ Langfuse tracing for agent delegation, LLM generations, and MCP tool calls.
- ✅ Document MCP tool ownership and JSON schemas in `MCP_TOOL_CATALOG.md`.
- ⬜ Add continuous browser/WebRTC voice streaming to the production React UI.
- ⬜ Add a polished frontend test dashboard to inspect inserted records, alerts, and queued actions.
- ⬜ Add accessibility testing with target older users and caregivers.

## Production Readiness

- ⬜ Implement authentication, authorization, audit logs, and encrypted production data storage.
- ⬜ Add rate limiting, input validation review, secret management, backups, and monitoring alerts.
- ⬜ Add CI checks, deployment configuration, and a production database migration process.
- ⬜ Complete end-to-end acceptance tests for all judge scenarios.
