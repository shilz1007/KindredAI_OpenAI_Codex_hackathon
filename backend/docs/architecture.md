# Kindred AI Architecture

## 1. Vision

Kindred AI is an AI-powered elderly care companion designed to support elderly people living independently.

The system provides:
- Voice-based interaction
- Emotional companionship
- Health assistance
- Safety monitoring
- Family communication support

The system supports bilingual conversations:
- English
- Bengali


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
                  Function Routing
                         |
        -----------------------------------
        |                |                |
        |                |                |
 Companion Agent   Guardian Agent   Logistics Agent
        |                |                |
        |                |                |
 Memory MCP +      Security MCP +      Inventory MCP
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

Before the React Native/WebRTC interface is implemented, agents are tested through a local Gradio interface.

- The interface is a temporary development harness, not a production user interface.
- Each agent is wired into the harness as it is implemented.
- The harness calls the same Python agent orchestration and MCP application services used by the backend.
- Agent-specific manual test scenarios are maintained in `src/kindred_ai/agents/TEST_SCENARIOS.md`.
- The Master test harness routes safety-message analysis, medication-supply checks, and explicitly confirmed medication replenishment requests to Guardian.
- The voice panel is a push-to-talk OpenAI Realtime WebSocket test: it sends a recorded microphone WAV utterance, lets the Master model consult Guardian through an approved tool, and plays the returned PCM audio as WAV.
- This is genuine Realtime API audio input/output, but it is not yet continuous browser WebRTC streaming. Continuous, interruptible voice belongs in the future React Native client.
- The temporary UI must not bypass agent authorization, MCP boundaries, or user-confirmation requirements.
