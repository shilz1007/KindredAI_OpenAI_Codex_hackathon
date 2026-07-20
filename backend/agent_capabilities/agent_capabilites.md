# Kindred Agent Capabilities and MCP Access

## Purpose of this document

This document is the working capability inventory for Kindred. It records what each agent is expected to do, the MCP servers it is permitted to use, and the tools currently available through those servers.

It is **not** a system-prompt document. It is the source used to decide what each future system prompt should permit, prohibit, and explain to the user.

## Shared rules

- The **Master Agent** is the only user-facing conversational entry point.
- Specialist agents are reached through Master routing; users do not directly choose an MCP tool.
- Every MCP has an ownership boundary. Agents must not read or write data from MCPs they are not permitted to use.
- Calls, messages, purchases, orders, and notifications are recorded locally in this prototype. They never contact a real person or external provider.
- Actions that change data must be confirmed by the user when confirmation is required by the workflow.
- The router uses an LLM to decide the appropriate agent and intent. Application code still validates data, enforces permission boundaries, and protects write operations.

---

## 1. Master Agent

### Role

Master is Kindred's English-speaking coordinator. It understands the user's request, maintains short-lived conversation state, delegates to a specialist, and gives the final clear response.

### Expected responsibilities

- Welcome user and provide a short, personalized daily briefing.
- Hold the main voice and text conversation in warm, concise English.
- Interpret a user's request and route it to Guardian, Companion, Logistics, or general Master guidance.
- Keep temporary turn context for multi-turn tasks such as collecting and confirming a phone-book contact.
- Ask for missing details and present a clear confirmation before a supported write action.
- Convert specialist facts into short, elderly-friendly language.
- Keep general safety advice conversational without creating Security database events from a spoken question alone.

### Not responsible for

- Direct database access.
- Direct MCP calls.
- Diagnosing medical conditions, making clinical decisions, or placing real orders/calls/messages.
- Bypassing a specialist agent's data and action boundary.

### MCP access

**Permitted MCP servers:** None directly.

Master delegates to specialist agents only:

| Specialist | Delegated domains |
| --- | --- |
| Companion | Memory and Communication |
| Guardian | Security, Health, and medication Inventory |
| Logistics | Household Inventory and Reminders |

---

## 2. Router Agent (internal)

### Role

Router is an internal, model-led decision agent. Master sends it the user request, limited conversation context, and the current Europe/Oslo time. Router returns a schema-validated decision identifying the next agent and any safe, structured details that agent needs.

### Expected responsibilities

- Classify a request as Master, Companion, Guardian, or Logistics work.
- Select one approved intent, such as medication supply, family call, phone-book contact, or household reminder.
- Extract only clearly stated details, such as a medicine name, relationship, quantity, or reminder date/time.
- Resolve relative reminder language such as “today” against the supplied local-time context.
- Return `null` for missing or uncertain structured values rather than inventing them.

### Not responsible for

- Speaking to Anita, making a promise, or writing a final conversational response.
- Calling an MCP tool, accessing a database, or performing an action.
- Overriding Master confirmation rules or specialist permissions.

### MCP access

**Permitted MCP servers:** None.

Router has an executable Python `RouterAgent` boundary and an OpenAI structured-output model adapter. It returns a validated `AgentRoute` only; Master executes the selected specialist workflow.

---

## 3. Companion Agent

### Role

Companion provides personalized social support and manages approved family-communication and phone-book workflows.

### Expected responsibilities

- Have warm, respectful, English-only social conversations.
- Use approved memories, profile information, and recent history to personalize conversation.
- Recognize important personal dates held in Memory MCP for the daily briefing.
- Resolve family members by name or relationship from the phone book, for example `son` or `daughter`.
- Collect a new trusted contact's name, relationship, and phone number through the Master-led conversation flow.
- Save a phone-book contact only after the user confirms the repeated details.
- Record a simulated request asking a trusted person to call Anita.
- Queue an approved simulated family message, including a birthday message, to the correct saved contact.

### Not responsible for

- Reading Health, Security, or Inventory data.
- Placing a real telephone call or sending a real SMS.
- Inventing a contact, a phone number, contact notes, or contact-editing features that have not been built.
- Creating a family message without explicit user approval.

### Permitted MCP servers

| MCP server | Tools exposed | Intended use |
| --- | --- | --- |
| Memory MCP | `get_user_profile` | Load approved demo profile context. |
| Memory MCP | `retrieve_history` | Read bounded recent history. |
| Memory MCP | `retrieve_memories` | Retrieve preferences, dates, and other saved memories. |
| Memory MCP | `save_memory` | Available on the MCP; currently used through admin/API workflows rather than Companion chat. |
| Communication MCP | `get_family_contacts` | Read the legacy approved family-contact list. |
| Communication MCP | `get_phone_book` | Read trusted contacts, names, relationships, and prototype phone numbers. |
| Communication MCP | `add_phone_book_contact` | Add a confirmed trusted contact. |
| Communication MCP | `request_family_call` | Record a simulated request for a trusted person to call Anita. |
| Communication MCP | `send_family_message` | Queue a simulated, explicitly approved family message. |
| Communication MCP | `create_notification` | Declared but not implemented; must not be offered to users. |

---

## 4. Guardian Agent

### Role

Guardian is the safety and medication-support specialist. It handles stored phone-message risk review and practical medication workflows.

### Expected responsibilities

- Read and explain already stored simulated phone messages when Anita asks to check messages.
- Analyze safety-relevant content and identify potential scam or fraud signals.
- Create security alerts for elevated-risk security events.
- Read active medication schedules.
- Record a named medicine dose after Anita reports taking it.
- Calculate medicine days remaining from the active schedule and inventory stock.
- Highlight medicine supplies with seven days or fewer remaining.
- Create a simulated medication replenishment request only after Anita explicitly confirms quantity and request.
- Give short, cautious safety guidance based only on available facts.

### Not responsible for

- Treating general spoken safety questions as stored phone messages.
- Creating Security records merely because Anita asks for general fraud advice.
- Clinical diagnosis, emergency response, changing a prescription, or deciding what dosage is safe.
- Placing a real medicine order.
- Reading Memory or Communication data.

### Permitted MCP servers

| MCP server | Tools exposed | Intended use |
| --- | --- | --- |
| Security MCP | `analyze_message` | Analyze a simulated stored phone message or security-relevant content. |
| Security MCP | `create_security_alert` | Create an alert from a known security event. |
| Security MCP | `get_security_events` | Available for review/API workflows; not currently a primary chat path. |
| Security MCP | `get_phone_messages` | List stored incoming simulated phone messages. |
| Health MCP | `get_medication_schedule` | Read active medication plans and daily times. |
| Health MCP | `record_medication_taken` | Persist a taken-dose record for a known active schedule. |
| Health MCP | `create_medication_schedule` | Available for admin/API setup; not a normal Guardian chat action. |
| Health MCP | `get_health_events` | Available for review/API workflows; no clinical interpretation is implied. |
| Inventory MCP | `check_inventory` | Read medication stock linked to a medication schedule. |
| Inventory MCP | `request_purchase` | Create a confirmed simulated medication replenishment request. |
| Inventory MCP | `upsert_medication_inventory` | Available for admin/API supply setup; not a normal chat action. |

---

## 5. Logistics Agent

### Role

Logistics manages non-medication household items and local reminders.

### Expected responsibilities

- Read household inventory and identify low-stock items.
- Create a simulated household purchase request after explicit confirmation.
- Read upcoming local reminders.
- Create a local reminder with a title and full date/time.
- Interpret relative reminder dates such as “today” using the current Europe/Oslo date supplied to the router.
- Keep household actions clearly separate from medicine replenishment, which belongs to Guardian.

### Not responsible for

- Medical stock, medication dose records, prescriptions, or medicine ordering.
- Sending reminder notifications externally; reminder delivery is deferred in this prototype.
- Placing real grocery orders or purchases.
- Reading Security, Health, Memory, or Communication data.

### Permitted MCP server

| MCP server | Tools exposed | Intended use |
| --- | --- | --- |
| Inventory MCP | `check_household_inventory` | Read non-medication household stock. |
| Inventory MCP | `request_household_purchase` | Record an explicitly confirmed simulated household purchase request. |
| Inventory MCP | `create_reminder` | Store a local reminder. |
| Inventory MCP | `get_reminders` | List local reminders in due order. |

---

## MCP ownership summary

| MCP server | Owning agent | Data and actions |
| --- | --- | --- |
| Memory MCP | Companion | Profile, personal memories, preferences, important dates, conversation history. |
| Communication MCP | Companion | Phone book, simulated family calls, and simulated family messages. |
| Security MCP | Guardian | Stored simulated phone messages, security events, and alerts. |
| Health MCP | Guardian | Medication schedules, taken-dose records, and health events. |
| Inventory MCP — medication subset | Guardian | Medication stock and simulated medicine replenishment requests. |
| Inventory MCP — household subset | Logistics | Household stock, simulated household purchases, and local reminders. |

## Deferred capabilities

- Real SMS, phone calls, pharmacy orders, grocery orders, or notifications.
- Contact notes, contact editing, and contact deletion.
- Authenticated multi-user data isolation and encrypted persistent conversation state.
- Bengali-language conversation.
- Clinical diagnosis, medication dose changes, and emergency-service integration.
