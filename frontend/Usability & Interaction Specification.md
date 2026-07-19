# Kindred Care Companion — Usability & Interaction Specification

## Purpose

Kindred is an English-first elderly-care companion. It offers calm voice and text interaction, helps the user follow routines, connects them with family through simulated communication, and surfaces safety information without creating unnecessary anxiety.

This is a prototype. Calls, SMS, WhatsApp messages, orders, and notifications are stored as local `queued` or `requested` records only. Nothing is sent to a real person or external service.

## 1. Elder User Experience

### Design principles

- Use a warm neutral background, large text, high contrast, and controls at least 48px tall.
- Keep the primary screen simple: speak, type, or choose a clear quick action.
- Explain actions in plain language and always make pending/simulated status visible.
- Do not use alarming language for a suspected scam or missed routine unless urgency is clinically configured.

### Home screen

The home screen contains:

- A friendly greeting and current date/time in the configured user timezone.
- Equal prominence for a large voice control and a text conversation field.
- A short conversation transcript with a **Clear conversation** action.
- Three status cards: **Today**, **Medication**, and **Family & reminders**.
- Quick actions: **My medicines**, **Call family**, **Remind me**, **Household supplies**, and **Safety help**.

### Morning grounding routine

At the user-configured morning time (9:00 AM in the demo), the interface opens a gentle orientation card and, when voice is connected, reads it aloud:

> Good morning, Anita. Let’s look at your day together.

The card shows only information currently present in Kindred’s databases:

- upcoming reminder(s),
- medication schedule(s),
- known calendar/memory event(s), and
- any household item requiring attention.

It then asks whether the user would like to add a reminder or household request. For example, “Please remind me to buy tea leaves” routes through Master to Logistics, which creates a persisted local reminder or household request.

The demo includes a **Trigger morning routine now** sandbox action. Production scheduling, quiet hours, and notification delivery are separate work.

### Conversation and family requests

The Master Agent is the only conversational voice. It receives the user request, asks the LLM router to select a specialist, and presents the specialist result naturally.

Example: “Tell my son to call me.”

```text
Elder → Master → LLM Router → Companion → Communication MCP
```

The Companion resolves `son` in the phone book and stores a simulated family message:

```text
recipient: Rahim
content: Please call me.
status: queued
```

Kindred replies: “I’ve queued a message to Rahim asking him to call you.” It must not claim that a real message or call was completed.

### Medication and safety cards

- A medication reminder displays the medicine name, stored instructions, and a large **I have taken it** control. This records a medication-taken event through Guardian and Health MCP.
- Low supply uses the existing inventory calculation and states the known quantity/days remaining. A refill request requires explicit confirmation.
- A suspicious simulated phone message is flagged by Guardian in Security MCP. The user sees a calm feed item such as: “I flagged a suspicious simulated message so you do not need to act on it.”
- A safe simulated family message may be read aloud and offers a draft reply. Sending the reply creates a `queued` Communication MCP message only after user confirmation.

## 2. Caregiver Experience

The caregiver view is a shared-demo management portal, not an authenticated production system. It must display a persistent **Demo mode — no real messages, calls, or orders** banner.

### Dashboard

Show:

- medication supply and refill warnings,
- recent health events and due medicines,
- open security alerts and flagged phone messages,
- scheduled reminders,
- household stock and pending purchase requests, and
- queued family messages/call requests.

### Management screens

The caregiver can manage the prototype’s persisted records:

- medication schedules and inventory quantities,
- household items, thresholds, requests, and reminders,
- phone-book contacts and family message drafts,
- simulated inbox messages and security-alert review, and
- demo memory/profile data.

Every write action uses an explicit review/confirmation dialog. Outbound communication and ordering actions must retain `queued` or `requested` status.

## 3. Developer / Judge Sandbox

The sandbox is a separate advanced panel, not part of the Elder home screen. It exists so a judge can demonstrate the full workflow without waiting for real time or external events.

Controls:

- **Trigger morning routine now** — renders the morning orientation from persisted demo data.
- **Inject phishing message** — writes a simulated phone message to Security MCP, invokes classification, and displays the resulting alert state.
- **Inject safe family message** — stores a simulated family message for read-out/reply testing.
- **Set medication stock low** — changes only demo inventory and exposes the Guardian refill-warning flow.
- **Set household stock low** — changes only demo household inventory and exposes Logistics reorder guidance.
- **Reset demo scenario** — restores idempotent fictitious seed data after a visible confirmation.

The sandbox must invoke backend application/API workflows. It must not write directly to SQLite files from React.

## 4. Agent and MCP Responsibilities

| User need | Master route | Specialist | MCP/data owner | Prototype result |
| --- | --- | --- | --- | --- |
| Friendly conversation or remembered preference | `general_companionship` | Companion | Memory MCP | Conversational response grounded in saved context |
| Tell son/daughter something | `family_message` | Companion | Communication MCP + phone book | Queued simulated message |
| Medication schedule, taken dose, low supply | medication route | Guardian | Health MCP + medication Inventory MCP | Recorded event, warning, or confirmed request |
| Suspicious stored phone message | stored-message review | Guardian | Security MCP | Flagged message and alert if appropriate |
| Household tea/milk/reminder request | household route | Logistics | household Inventory MCP | Stored reminder or confirmed purchase request |

The Master does not access databases or MCPs directly. The browser does not access MCP tools or SQLite databases directly.

## 5. Incoming Phone Message Event Flow

Incoming phone messages are event-driven. The Master Agent does not poll a phone inbox and is not invoked merely because a message arrived.

```text
Phone / sandbox simulator
        ↓
Authenticated backend message-ingestion endpoint
        ↓
Security MCP stores the simulated message as pending
        ↓
Guardian invokes the Security classifier
        ↓
Message is marked low / medium / high / critical
        ↓
Medium+ creates a Security event and open alert
        ↓
Frontend receives refreshed feed state or a later notification
        ↓
Master explains the result only when speaking with the Elder user
```

For the prototype, the Developer Sandbox and React UI simulate a phone delivery by posting a message to the backend. A later mobile client can call the same endpoint after it receives an SMS/device event. React must never classify messages itself or write directly to the Security database.

Behaviour:

- Low-risk messages are saved and may appear in a normal inbox/feed.
- Medium, high, and critical messages create an alert and appear in the caregiver dashboard.
- The Elder feed uses calm language such as “I flagged a suspicious message so you do not need to act on it.”
- The Master reads or explains the result during a user interaction; Guardian remains responsible for automatic analysis.
- Failed model analysis leaves the message in a failed state, creates no alert, and is visible to the caregiver/demo dashboard for review.

## 6. Backend and Frontend Contract Requirements

- React uses stable FastAPI endpoints, never Python in-process calls used by Gradio.
- Text conversation requires a Master API with a browser session identifier, send-turn, and clear-session operations.
- Browser voice uses WebRTC with a short-lived backend-issued Realtime credential. The long-lived OpenAI API key remains server-side.
- Realtime tool requests are allow-listed and sent to a backend Master delegation endpoint; the browser cannot invoke arbitrary agent/MCP tools.
- Use the single fictional family consistently: Anita, Rahim (son), and Sara (daughter). Add other fictional contacts only through the phone book.
- English is the only supported language in this release. Bengali support is deferred.

## 7. Acceptance Scenarios

1. A user can speak or type a request, see the transcript, and continue a multi-turn conversation in one browser session.
2. A user can say “Tell my son to call me”; a queued simulated message to Rahim is visible in the caregiver dashboard.
3. A user can mark a scheduled dose as taken; the event persists and the medication card updates.
4. A judge can inject a phishing message; Guardian flags it and the Elder feed shows calm, non-alarming guidance.
5. A user can request tea leaves or a reminder; Logistics persists the relevant household record.
6. No UI action sends a real communication, places a real order, or exposes the OpenAI API key.
