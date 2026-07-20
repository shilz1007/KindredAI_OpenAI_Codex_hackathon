# Kindred AI Architecture

## 1. Vision

Kindred AI is an AI-powered elderly care companion designed to support elderly people living independently.

The system provides:
- Voice-based interaction
- Emotional companionship
- Health assistance
- Safety monitoring
- Family communication support

The current prototype supports English conversations. Bengali voice interaction is deferred.


---

# 2. High Level Architecture


                    Elderly User
                         |
                         |
                 WebRTC Voice Interface
                         |
                         |
                  Master Agent
                 (Voice Face)
                         |
                    Router Agent
             (internal route selection)
                         |
        ------------------------------------------------
        |                |                |             |
        |                |                |             |
 Companion Agent   Guardian Agent   Logistics Agent  Research Agent
        |                |                |             |
        |                |                |             |
 Memory MCP +      Security MCP +      Inventory MCP Tavily remote MCP
 Communication MCP Health MCP +
                   Inventory MCP


                         |
                  Memory Service
                         |
                  User Profile DB



---

# 3. Master Agent

## Responsibility

The Master Agent is the only agent that directly communicates with the elderly user.

Responsibilities:

- Maintain realtime voice session
- Understand user intent
- Detect language
- Maintain conversation flow
- Delegate tasks to specialist agents


## Does NOT:

- Access databases directly
- Execute business logic
- Perform specialist tasks

## Internal Router Agent

Router Agent is a separate internal agent. Master sends it the user request, short-lived session context, and current Europe/Oslo time. Router returns a structured, validated decision identifying the correct next agent and any clearly stated details needed by that workflow.

Router Agent:

- Has no MCP, database, or user-facing conversation access.
- Cannot perform an action or bypass confirmation requirements.
- Selects Master, Companion, Guardian, Logistics, or Research as the next handler.
- Uses the validated Router instruction from `agents.yaml`.


---

# 4. Companion Agent

## Purpose

Provides emotional and social companionship.

Capabilities:

- General conversation
- Story telling
- Poetry
- Cultural conversations
- Remember user preferences


Uses:

- Memory MCP Server
- Communication MCP Server

---

# Research Agent

## Purpose

Retrieves current public information for Master without accessing Anita's personal data.

Uses:

- Tavily hosted remote MCP, read-only
- An isolated local SQLite history containing only the latest 20 public research answers

The Research Agent never speaks directly to the user. Master reads its concise English result without exposing search URLs, source details, or credentials.


---

# 5. Guardian Agent

## Purpose

Background safety monitoring agent.

Runs independently from voice conversation.


Capabilities:

- Analyze incoming messages
- Detect possible fraud
- Monitor safety events
- Create alerts
- Notify family if required


Uses:

- Security MCP Server
- Health MCP Server
- Inventory MCP Server (medication replenishment only; requires user confirmation)


---

# 6. Logistics Agent

## Purpose

Handles external actions.

Capabilities:

- Send messages to family
- Create reminders
- Order items
- Manage simple requests


Uses:

- Inventory MCP Server


---

# 7. MCP Server Architecture


Each MCP server is isolated.

Each server:

- Owns its business logic
- Owns its database
- Exposes tools through MCP
- Cannot directly access other MCP databases


## MCP Servers


### Memory MCP

Purpose:
Store and retrieve user context.


Tools:

- get_user_profile()
- save_memory()
- retrieve_history()



### Health MCP

Purpose:
Manage health-related information.


Tools:

- get_medication_schedule()
- record_medication_taken()
- get_health_events()



### Security MCP

Purpose:
Safety monitoring.


Tools:

- analyze_message()
- create_security_alert()
- get_security_events()



### Communication MCP

Purpose:
External communication.


Tools:

- send_family_message()
- create_notification()



### Inventory MCP

Purpose:
Manage household items.


Tools:

- check_inventory()
- request_purchase()



---

# 8. Technology Stack


Backend:

- Python
- FastMCP
- OpenAI Agents SDK
- SQLite
- FastAPI


Frontend:

- React Native
- Expo
- TypeScript
- WebRTC


AI:

- GPT Realtime API
- OpenAI Agents


---

# 9. Development Principles


1. Agents should have clear responsibilities.

2. MCP servers expose capabilities, not intelligence.

3. Master Agent coordinates but does not execute specialist tasks.

4. Databases are isolated by domain.

5. Build incrementally with working demos.

---

# 10. Temporary Agent Testing Plan

Agents are tested through the React Care Hub and FastAPI/Swagger endpoints.

- The interface is a temporary development harness, not a production user interface.
- Each agent is wired into the harness as it is implemented.
- The harness calls the same Python agent orchestration and MCP application services used by the backend.
- Agent-specific manual test scenarios are maintained in `src/kindred_ai/agents/TEST_SCENARIOS.md`.
- The Master test harness routes safety-message analysis, medication-supply checks, and explicitly confirmed medication replenishment requests to Guardian.
- The voice panel is a push-to-talk OpenAI Realtime WebSocket test: it sends a recorded microphone WAV utterance, lets the Master model consult Guardian through an approved tool, and plays the returned PCM audio as WAV.
- This is genuine Realtime API audio input/output, but it is not yet continuous browser WebRTC streaming. Continuous, interruptible voice belongs in the future React Native client.
- The temporary UI must not bypass agent authorization, MCP boundaries, or user-confirmation requirements.
