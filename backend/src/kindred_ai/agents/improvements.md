# Kindred AI - Architecture Improvements

## Purpose

This document describes improvements to move Kindred AI from a deterministic workflow system into a true multi-agent AI architecture.

The React Care Hub is the current prototype voice interface. A production deployment may later use a dedicated WebRTC voice interface.

---

# 1. Current Architecture Problems

## Deterministic Pattern Matching

Current flow:

User Voice
→ React Care Hub
→ Realtime API Adapter
→ Master Agent
→ Pattern Matching Rules
→ Guardian Workflow


Problem:

The system currently depends on hardcoded rules such as:

- If message contains "Metformin"
    → Medication workflow

- If message contains "order" and "tablets"
    → Purchase workflow

- Otherwise
    → Security workflow


Limitations:

- Cannot handle new conversation types easily.
- Logic becomes difficult to maintain.
- Not a true agentic architecture.
- LLM intelligence is limited to conversation generation only.


---

# 2. Target Agentic Architecture


User

↓

Voice Interface

(Current: React Care Hub)
(Future: React Native + WebRTC)

↓

Master Agent

↓

Agent Router

↓

--------------------------------

|              |               |

Companion   Guardian       Logistics

Agent        Agent           Agent


↓

MCP Servers

↓

Domain Databases


---

# 3. Master Agent Improvements


## Current Responsibility

The Master Agent currently:
- Receives user request.
- Calls Guardian workflow.
- Depends on deterministic routing.


## New Responsibility

The Master Agent should:

- Maintain the conversation.
- Understand user intent.
- Detect user language.
- Decide if specialist help is required.
- Route requests to the correct agent.


The Master Agent should NOT:

- Access databases.
- Execute business logic.
- Know health rules.
- Know security rules.


---

# 4. Replace Pattern Matching with Agent Routing


## Current

Example:

"If message contains Metformin"

↓

Medication workflow


## Improved

Use LLM-based intent routing.


Example:

User:

"How many Metformin tablets do I have left?"


Master Agent determines:

```json
{
  "intent": "medication_supply",
  "agent": "guardian",
  "required_capabilities": [
      "health",
      "inventory"
  ]
}
