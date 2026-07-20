# Kindred AI MCP Tool Catalog

This is the practical reference for the current prototype. Use it to see **which agent may use each MCP**, what each tool does, and the exact JSON expected by the tool.

## Read this first

| Symbol | Meaning |
| --- | --- |
| `Read` | Retrieves prototype data; does not create or change a record. |
| `Write` | Creates or changes a local SQLite record. |
| `Simulated` | A call, message, reminder, or purchase is recorded locally only. Nothing is sent or ordered outside Kindred. |
| `Approval required` | The tool rejects the request until the user has explicitly approved it. |

All timestamps are ISO 8601 date-time strings, for example `2026-07-19T08:00:00+02:00`.

---

## 1. Agent access at a glance

| Agent | Role | Permitted MCPs | Important boundary |
| --- | --- | --- | --- |
| **Master** | Conversational coordinator and router | None directly | Routes to specialists; it must not call MCP tools itself. |
| **Companion** | Personal conversation, memories, family support | Memory, Communication | Family messages require explicit approval and are simulated. |
| **Guardian** | Health, medication supply, incoming-message safety | Health, Security, Inventory | Uses only **medication** inventory tools, never household purchasing. |
| **Logistics** | Household items and reminders | Inventory | Uses only **household** inventory tools and reminders. |

### Permission matrix

| MCP | Master | Companion | Guardian | Logistics |
| --- | :---: | :---: | :---: | :---: |
| Health | — | — | ✅ | — |
| Memory | — | ✅ | — | — |
| Security | — | — | ✅ | — |
| Inventory — medication tools | — | — | ✅ | — |
| Inventory — household tools | — | — | — | ✅ |
| Communication | — | ✅ | — | — |

---

## 2. Tool index

| MCP | Tool | Mode | Called by | Purpose |
| --- | --- | --- | --- | --- |
| Health | `get_medication_schedule` | Read | Guardian | Get active medicine schedules and daily times. |
| Health | `create_medication_schedule` | Write | Guardian | Create an active medicine plan and its daily times. |
| Health | `record_medication_taken` | Write | Guardian | Record one confirmed dose. |
| Health | `get_health_events` | Read | Guardian | Review health events, newest first. |
| Memory | `get_user_profile` | Read | Companion | Get the demo user’s profile. |
| Memory | `save_memory` | Write | Companion | Store an approved fact or preference. |
| Memory | `retrieve_history` | Read | Companion | Get recent conversation history. |
| Security | `analyze_message` | Write | Guardian | Analyse and store a security event. |
| Security | `create_security_alert` | Write | Guardian | Add an alert for an existing security event. |
| Security | `get_security_events` | Read | Guardian | List stored security events. |
| Security | `get_phone_messages` | Read | Guardian | List simulated stored phone messages, newest first. |
| Inventory | `check_inventory` | Read | Guardian | Get medication stock, linked Health schedule ID, and reorder status. |
| Inventory | `upsert_medication_inventory` | Write | Guardian | Create or update medication stock linked to a Health schedule. |
| Inventory | `request_purchase` | Write · approval required | Guardian | Record a confirmed medication replenishment request. |
| Inventory | `check_household_inventory` | Read | Logistics | Get household stock and reorder signals. |
| Inventory | `get_reminders` | Read | Logistics | List scheduled local reminders, next due first. |
| Inventory | `request_household_purchase` | Write · approval required | Logistics | Record a confirmed household purchase request. |
| Inventory | `create_reminder` | Write · simulated | Logistics | Store a local reminder; delivery is not implemented. |
| Communication | `get_family_contacts` | Read | Companion | List family contacts. |
| Communication | `get_phone_book` | Read | Companion | List contacts approved for simulated calls. |
| Communication | `add_phone_book_contact` | Write · simulated | Companion | Store a trusted family contact for simulated communication. |
| Communication | `send_family_message` | Write · approval required · simulated | Companion | Queue an approved family message. |
| Communication | `request_family_call` | Write · simulated | Companion | Record a request to call a family contact. |
| Communication | `create_notification` | Not implemented | Companion | Always returns a tool error. |

---

## 3. Health MCP — Guardian

### `get_medication_schedule`

**Use when:** the user asks what medication is due or what their schedule is.

**Input**

```json
{}
```

**Output** — an array of schedules.

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "required": ["id", "medication_name", "dose_instructions", "timezone", "daily_times", "is_active"],
    "properties": {
      "id": {"type": "string"},
      "medication_name": {"type": "string"},
      "dose_instructions": {"type": "string"},
      "timezone": {"type": "string"},
      "daily_times": {"type": "array", "items": {"type": "string", "pattern": "^\\d{2}:\\d{2}$"}},
      "is_active": {"type": "boolean"}
    }
  }
}
```

### `create_medication_schedule`

**Use when:** a medication plan is being set up for the prototype user.

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["medication_name", "dose_instructions", "daily_times"],
  "properties": {
    "medication_name": {"type": "string", "minLength": 1},
    "dose_instructions": {"type": "string", "minLength": 1},
    "daily_times": {"type": "array", "minItems": 1, "items": {"type": "string", "pattern": "^\\d{2}:\\d{2}$"}},
    "timezone": {"type": "string", "default": "Europe/Oslo"}
  }
}
```

Returns the created schedule, including its generated `id`. Use that ID when adding or linking medication stock in Inventory MCP.

### `record_medication_taken`

**Use when:** the user confirms they have taken an active scheduled dose.

**Input**

```json
{
  "type": "object",
  "additionalProperties": false,
  "required": ["schedule_id"],
  "properties": {
    "schedule_id": {"type": "string", "example": "demo-schedule-metformin"},
    "taken_at": {"type": ["string", "null"], "format": "date-time", "default": null},
    "note": {"type": ["string", "null"], "default": null}
  }
}
```

**Output**

```json
{"type":"object","required":["id","schedule_id","taken_at","note"],"properties":{"id":{"type":"string"},"schedule_id":{"type":"string"},"taken_at":{"type":"string","format":"date-time"},"note":{"type":["string","null"]}}}
```

**Failure:** an unknown or inactive schedule ID returns a clear error and writes nothing.

### `get_health_events`

**Input:** `{}`

**Output**

```json
{"type":"array","items":{"type":"object","required":["id","event_type","occurred_at","details","severity"],"properties":{"id":{"type":"string"},"event_type":{"type":"string"},"occurred_at":{"type":"string","format":"date-time"},"details":{"type":["string","null"]},"severity":{"type":"string"}}}}
```

---

## 4. Memory MCP — Companion

### `get_user_profile`

**Input:** `{}`

**Output**

```json
{"type":"object","required":["id","preferred_name","preferred_language","timezone","preferences"],"properties":{"id":{"type":"string"},"preferred_name":{"type":"string"},"preferred_language":{"type":"string"},"timezone":{"type":"string"},"preferences":{"type":["string","null"]}}}
```

### `save_memory`

**Use when:** the user explicitly asks Kindred to remember something, or a memory has been approved.

```json
{"type":"object","additionalProperties":false,"required":["content"],"properties":{"content":{"type":"string","minLength":1},"category":{"type":"string","default":"general"},"source":{"type":"string","default":"conversation"},"importance":{"type":"integer","minimum":1,"maximum":5,"default":1}}}
```

**Output**

```json
{"type":"object","required":["id","content","category","source","importance","created_at"],"properties":{"id":{"type":"string"},"content":{"type":"string"},"category":{"type":"string"},"source":{"type":"string"},"importance":{"type":"integer"},"created_at":{"type":"string","format":"date-time"}}}
```

### `retrieve_history`

```json
{"type":"object","additionalProperties":false,"properties":{"limit":{"type":"integer","minimum":1,"default":10}}}
```

Returns recent entries, newest first: `id`, `speaker`, `content`, and `occurred_at`.

---

## 5. Security MCP — Guardian

### Important routing rule

General questions such as *“Is it safe to share a code?”* stay with the **Master Agent’s general intelligence**. They must not create a security event or alert.

Only an incoming simulated phone message is stored and classified. The judge/Admin interface submits these through the HTTP endpoint below; it is intentionally **not** an MCP tool.

| HTTP API | Purpose |
| --- | --- |
| `POST /api/v1/security/phone-messages` | Store and immediately classify a simulated phone message. |
| `GET /api/v1/security/phone-messages` | Review submitted messages and their classification state. |

### `analyze_message`

```json
{"type":"object","additionalProperties":false,"required":["message"],"properties":{"message":{"type":"string","minLength":1}}}
```

Returns a stored security event with `id`, `message`, `risk_level` (`low`, `medium`, `high`, or `critical`), `matched_signals`, and `created_at`.

### `create_security_alert`

```json
{"type":"object","additionalProperties":false,"required":["event_id"],"properties":{"event_id":{"type":"string"},"severity":{"type":"string","enum":["low","medium","high","critical"],"default":"medium"}}}
```

Returns `id`, `event_id`, `severity`, `status`, and `created_at`.

### `get_security_events`

```json
{"type":"object","additionalProperties":false,"properties":{"limit":{"type":"integer","minimum":1,"default":20}}}
```

### `get_phone_messages`

```json
{"type":"object","additionalProperties":false,"properties":{"limit":{"type":"integer","minimum":1,"default":20}}}
```

Returns simulated phone-message records with the message text, received timestamp, analysis status, risk level, explanation, detected signals, and linked security event ID when one exists.

---

## 6. Inventory MCP

### Medication inventory — Guardian only

| Tool | Input | Result |
| --- | --- | --- |
| `check_inventory` | `{}` | Health `schedule_id`, medication name, units available, last purchase date, and reorder status. |
| `upsert_medication_inventory` | `{"schedule_id":"string","medication_name":"string","units_available":30,"last_purchased_on":"YYYY-MM-DD"}` | Create or update local medicine stock for a Health schedule. |
| `request_purchase` | `{"medication_name":"string","quantity":1,"user_confirmed":true}` | A locally recorded request with ID, status, and timestamp. |

`request_purchase` schema:

```json
{"type":"object","additionalProperties":false,"required":["medication_name","quantity","user_confirmed"],"properties":{"medication_name":{"type":"string","minLength":1},"quantity":{"type":"integer","minimum":1},"user_confirmed":{"type":"boolean"}}}
```

**Safety rule:** `user_confirmed` must be `true`; this only records a simulated request and never contacts a pharmacy.

### Household inventory — Logistics only

| Tool | Input | Result |
| --- | --- | --- |
| `check_household_inventory` | `{}` | Item, available quantity, reorder threshold, and `reorder_needed`. |
| `get_reminders` | `{}` | Scheduled local reminders, ordered by next due time. |
| `request_household_purchase` | `{"item_name":"string","quantity":1,"user_confirmed":true}` | A locally recorded simulated purchase request. |
| `create_reminder` | `{"title":"string","remind_at":"date-time"}` | A locally scheduled reminder. |

`request_household_purchase` schema:

```json
{"type":"object","additionalProperties":false,"required":["item_name","quantity","user_confirmed"],"properties":{"item_name":{"type":"string","minLength":1},"quantity":{"type":"integer","minimum":1},"user_confirmed":{"type":"boolean"}}}
```

`create_reminder` schema:

```json
{"type":"object","additionalProperties":false,"required":["title","remind_at"],"properties":{"title":{"type":"string","minLength":1},"remind_at":{"type":"string","format":"date-time"}}}
```

---

## 7. Communication MCP — Companion

| Tool | Input | What happens |
| --- | --- | --- |
| `get_family_contacts` | `{}` | Returns family contact IDs, names, and relationships. |
| `get_phone_book` | `{}` | Returns approved phone-book contacts, including a prototype phone number. |
| `send_family_message` | `{"contact_id":"son","content":"Please call me.","user_approved":true}` | Queues a local simulated message. |
| `request_family_call` | `{"contact_query":"son"}` | Records a simulated call request. |
| `create_notification` | `{}` | **Not implemented**; always raises a tool error. |

`send_family_message` schema:

```json
{"type":"object","additionalProperties":false,"required":["contact_id","content","user_approved"],"properties":{"contact_id":{"type":"string"},"content":{"type":"string","minLength":1},"user_approved":{"type":"boolean"}}}
```

`request_family_call` schema:

```json
{"type":"object","additionalProperties":false,"required":["contact_query"],"properties":{"contact_query":{"type":"string","minLength":1}}}
```

**Safety rule:** no real message or call is ever sent. A family message also requires `user_approved: true`.

---

## 8. Related HTTP APIs (useful for judges)

MCP tools are agent-facing. Swagger exposes HTTP adapters for manual testing:

| Area | Examples |
| --- | --- |
| Master | Create or clear a conversation turn. |
| Health | View schedule, record dose, list events. |
| Security | Submit/list simulated phone messages and review events. |
| Companion | View phone book, queue a family message, request a call. |
| Logistics | Review household stock, create reminder, submit purchase request. |
| Memory | View profile/history and save an approved memory. |

Open Swagger at `http://127.0.0.1:8000/docs` while the backend is running.

---

## 9. Decisions still open

1. Introduce authenticated `user_id` at public API boundaries before multi-user support.
2. Add aliases such as “my son” and “Rahim” to the phone-book model.
3. Define notification recipient, consent, channel, delivery status, and retry policy before implementing `create_notification`.
4. Decide whether phone-message ingestion remains HTTP/event-only or becomes an explicit Security MCP tool.
