# Kindred AI Project Progress

Use `✅` for completed tasks and `⬜` for planned work. Update this file whenever a task is finished.

## Foundation

- ✅ Define the clean backend package structure.
- ✅ Document the high-level architecture and MCP ownership.
- ✅ Create the startup-validated YAML agent catalog.
- ✅ Add Swagger UI for development testing.
- ✅ Add automated backend tests.

## Agent Catalog

- ✅ Define Master, Companion, Guardian, and Logistics agents in `agents.yaml`.
- ✅ Validate permitted MCP access at startup.
- ✅ Allow Guardian access to Security, Health, and confirmed medication-replenishment Inventory workflows.
- ⬜ Add Bengali agent instructions when language routing is implemented.

## Temporary Agent Test UI

- ✅ Create a local Gradio development harness for Guardian Agent.
- ✅ Document manual agent scenarios in `agents/TEST_SCENARIOS.md`.
- ✅ Document the temporary-UI testing plan in the architecture.
- ⬜ Add Companion, Logistics, and Master Agent views as those agents are implemented.

## Memory MCP

- ✅ Create isolated SQLite database, migrations, and demo seed data.
- ✅ Implement user profile retrieval.
- ✅ Implement memory storage.
- ✅ Implement conversation-history retrieval.
- ✅ Add Swagger testing endpoints and automated tests.
- ✅ Add separate non-medication household inventory records and reorder signals for Logistics.
- ⬜ Add semantic/relevance-based memory retrieval for Companion Agent.

## Health MCP

- ✅ Create isolated SQLite database, migrations, and demo seed data.
- ✅ Store medication schedules and daily dose times.
- ✅ Record medication-taken events.
- ✅ Retrieve health events.
- ✅ Add Swagger testing endpoints and automated tests.
- ⬜ Add medication stock/dose-quantity data needed for inventory forecasting.

## Security MCP

- ✅ Create isolated SQLite database, migrations, and demo seed data.
- ✅ Analyze messages with deterministic prototype safety signals.
- ✅ Create and retrieve security alerts/events.
- ✅ Add Swagger testing endpoints and automated tests.
- ⬜ Replace the prototype keyword rules with an approved safety policy/model integration.

## Inventory MCP

- ✅ Create isolated SQLite database, migrations, and demo medication inventory.
- ✅ Track medicine quantities, purchase dates, and reorder status.
- ✅ Implement `check_inventory()`.
- ✅ Implement confirmed `request_purchase()`.
- ✅ Add Swagger testing endpoints and automated tests.

## Guardian Agent

- ✅ Implement Guardian Agent orchestration over Security, Health, and Inventory MCPs.
- ✅ Analyze incoming messages and create alerts for medium/high-risk results.
- ✅ Calculate medication days remaining from schedule and inventory data.
- ✅ Return a refill warning when seven or fewer days remain.
- ✅ Create a medication replenishment request only after explicit user confirmation.
- ✅ Add Guardian Swagger endpoints and end-to-end tests.

## Companion Agent

- ⬜ Implement personalized companionship responses using Memory MCP.
- ⬜ Add language-aware English/Bengali response handling.
- ⬜ Integrate approved family communication through Communication MCP.
- ⬜ Add Companion Swagger endpoints and tests.

## Communication MCP

- ⬜ Create isolated SQLite database and migrations.
- ⬜ Implement family-message delivery workflow.
- ⬜ Implement notification workflow.
- ⬜ Add Swagger testing endpoints and automated tests.

## Logistics Agent

- ✅ Implement authorized household inventory workflows with explicit purchase confirmation.
- ✅ Implement persisted local reminder orchestration.
- ✅ Add Logistics Swagger endpoints and tests.
- ⬜ Deliver due reminders through Communication MCP after a notification policy is defined.

## Master Agent and Realtime Experience

- ✅ Implement a model-backed Master Agent that routes Guardian workflows in the temporary Gradio UI.
- ✅ Build FastMCP client adapters for Guardian's Security, Health, and Inventory access.
- ✅ Extend English intent routing and delegation to Companion and Logistics Agents.
- ✅ Add bounded, in-memory multi-turn context to the temporary Master text UI.
- ⬜ Implement English/Bengali language routing.
- ⬜ Integrate the OpenAI Agents SDK.
- ✅ Integrate a push-to-talk OpenAI Realtime WebSocket voice session in the temporary Gradio UI.
- ⬜ Add continuous WebRTC microphone streaming for the React Native production UI.
- ⬜ Add authentication, authorization, audit logging, and production safety controls.
