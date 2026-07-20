# Kindred Demo Video Script

**Target duration:** 2 minutes 35 seconds to 2 minutes 50 seconds.  
**Goal:** Show a clear elderly-care use case, the safe simulated actions, the agent/MCP architecture, and how Codex accelerated development.  
**Recording rule:** Keep real API keys, phone numbers, and private data off screen. All calls, messages, purchases, and medicine actions shown are prototype simulations.

## Before recording

- Start the backend and frontend.
- Sign in once, then log out, so the demo starts at the login page.
- In Family Admin, ensure there is a trusted contact with relationship **son** and a medicine plan with low supply.
- Add one suspicious phone message, such as a verification-code scam, so it appears in Caregiver View.
- Close unrelated browser tabs, terminals, notifications, and any screen that could show secrets.
- Speak slowly. Do not read the on-screen text word for word.

## 0:00–0:15 — Problem and introduction

**Show:** Login page, then sign in as Anita.

**Say:**

> Kindred is a voice-first care companion for older adults. It makes everyday support easier: medication awareness, scam protection, household help, and staying connected to family.

## 0:15–0:35 — Personal daily greeting

**Show:** Care Hub loads. Let the greeting appear and play.

**Say:**

> When Anita signs in, Kindred starts with a short English greeting. It uses approved personal information, such as an important family birthday, without overwhelming her with a long dashboard.

**Point out:** The birthday uses the actual son contact saved in the phone book.

## 0:35–0:55 — Medication support

**Show:** Ask in chat or voice: “How many days of Metformin do I have left?”

**Say:**

> Guardian checks medication supply through the Health MCP. The answer is deliberately short and elderly-friendly: it only highlights medicine that is running low and offers refill help.

## 0:55–1:20 — Family connection and confirmation

**Show:** Enter these messages in the chat:

1. `Can you save a contact in the phone book for me?`
2. `John Baker, my son, +47 900 11 222.`
3. `Yes, save it.`
4. `Please send birthday wishes to my son.`

**Say:**

> Kindred collects a name, relationship, and phone number, then repeats the details for confirmation. Only after Anita says yes does Companion save it through Communication MCP. It can then resolve “my son” from the phone book and queue a simulated birthday message.

**Point out:** The result says the message was successfully sent, but the prototype records it locally and never contacts a real person.

## 1:20–1:40 — Scam protection

**Show:** Switch to Caregiver View. Show the flagged suspicious phone message.

**Say:**

> Incoming simulated phone messages are stored separately and classified by Guardian through Security MCP. Suspicious messages are flagged for a caregiver, while ordinary personal messages remain available without creating unnecessary alarms.

## 1:40–1:55 — Everyday support

**Show:** Open one Quick Action, such as Reminders or Groceries. Add a local reminder or show an upcoming one.

**Say:**

> The same Care Hub also supports simple everyday tasks, such as reminders and household supplies. Every action is explicit, reviewable, and safely simulated for this prototype.

## 1:55–2:20 — Architecture

**Show:** `architecture.md`, `agents.yaml`, or the MCP tool catalog. Keep this visual brief.

**Say:**

> The Master Agent is the only conversational entry point. It routes requests to Companion, Guardian, or Logistics. Each specialist has only the MCP servers it is permitted to use, keeping health, security, memory, communication, and inventory boundaries separate.

## 2:20–2:40 — Codex and GPT-5.6 contribution

**Show:** Repository structure, a focused test run, and optionally Langfuse traces.

**Say:**

> I collaborated with Codex throughout the project. Codex, using GPT-5.6, accelerated the clean architecture, FastMCP boundaries, database migrations, tests, React interface, and iterative improvements from real user testing. The running specialist agents use GPT-5.1, while the application keeps orchestration, permissions, and MCP access in explicit Python code.

## 2:40–2:50 — Close

**Show:** Return to Care Hub.

**Say:**

> Kindred turns simple conversation into practical, personal support while keeping sensitive actions transparent and safely simulated.

## Optional cuts if the video runs long

- Remove the Everyday support section first.
- Keep the exact contact-confirmation flow; it is the clearest proof of safe agent orchestration.
- Keep total runtime below 2 minutes 55 seconds to leave margin for pauses and transitions.
