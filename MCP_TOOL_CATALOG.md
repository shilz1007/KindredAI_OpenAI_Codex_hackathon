# Kindred AI MCP Tool Catalog

This is the current contract inventory for agent access and FastMCP tools. JSON Schema uses the JSON Schema 2020-12 style. Timestamps are ISO 8601 strings with timezone offsets.

## Agent Access

| Agent | Permitted MCP servers | Tools it should use |
| --- | --- | --- |
| Master | None | None. Master routes requests and never calls MCP tools directly. |
| Companion | Memory, Communication | All Memory tools; Communication contact, phone-book, message, and simulated-call tools. |
| Guardian | Security, Health, Inventory | All Health/Security tools; only medication `check_inventory` and `request_purchase` from Inventory. |
| Logistics | Inventory | Only household `check_household_inventory`, `request_household_purchase`, and `create_reminder`. |

## Shared Response Shapes

```json
{
  "$defs": {
    "medicationSchedule": {"type":"object","required":["id","medication_name","dose_instructions","timezone","daily_times","is_active"],"properties":{"id":{"type":"string"},"medication_name":{"type":"string"},"dose_instructions":{"type":"string"},"timezone":{"type":"string"},"daily_times":{"type":"array","items":{"type":"string","pattern":"^\\d{2}:\\d{2}$"}},"is_active":{"type":"boolean"}}},
    "medicationTakenRecord": {"type":"object","required":["id","schedule_id","taken_at","note"],"properties":{"id":{"type":"string"},"schedule_id":{"type":"string"},"taken_at":{"type":"string","format":"date-time"},"note":{"type":["string","null"]}}},
    "healthEvent": {"type":"object","required":["id","event_type","occurred_at","details","severity"],"properties":{"id":{"type":"string"},"event_type":{"type":"string"},"occurred_at":{"type":"string","format":"date-time"},"details":{"type":["string","null"]},"severity":{"type":"string"}}},
    "memoryItem": {"type":"object","required":["id","content","category","source","importance","created_at"],"properties":{"id":{"type":"string"},"content":{"type":"string"},"category":{"type":"string"},"source":{"type":"string"},"importance":{"type":"integer"},"created_at":{"type":"string","format":"date-time"}}},
    "securityEvent": {"type":"object","required":["id","message","risk_level","matched_signals","created_at"],"properties":{"id":{"type":"string"},"message":{"type":"string"},"risk_level":{"type":"string","enum":["low","medium","high","critical"]},"matched_signals":{"type":"array","items":{"type":"string"}},"created_at":{"type":"string","format":"date-time"}}},
    "medicationInventory": {"type":"object","required":["id","medication_name","units_available","last_purchased_at"],"properties":{"id":{"type":"string"},"medication_name":{"type":"string"},"units_available":{"type":"integer","minimum":0},"last_purchased_at":{"type":"string","format":"date-time"}}},
    "householdItem": {"type":"object","required":["id","item_name","quantity_available","reorder_threshold","reorder_needed"],"properties":{"id":{"type":"string"},"item_name":{"type":"string"},"quantity_available":{"type":"integer","minimum":0},"reorder_threshold":{"type":"integer","minimum":0},"reorder_needed":{"type":"boolean"}}}
  }
}
```

## Health MCP — Guardian

### `get_medication_schedule`

Request: `{}`

Response: `{"type":"array","items":{"$ref":"#/$defs/medicationSchedule"}}`

### `record_medication_taken`

Request:

```json
{"type":"object","additionalProperties":false,"required":["schedule_id"],"properties":{"schedule_id":{"type":"string"},"taken_at":{"type":["string","null"],"format":"date-time","default":null},"note":{"type":["string","null"],"default":null}}}
```

Response: `{"$ref":"#/$defs/medicationTakenRecord"}`

### `get_health_events`

Request: `{}`

Response: `{"type":"array","items":{"$ref":"#/$defs/healthEvent"}}`

## Memory MCP — Companion

### `get_user_profile`

Request: `{}`

Response:

```json
{"type":"object","required":["id","preferred_name","preferred_language","timezone","preferences"],"properties":{"id":{"type":"string"},"preferred_name":{"type":"string"},"preferred_language":{"type":"string"},"timezone":{"type":"string"},"preferences":{"type":["string","null"]}}}
```

### `save_memory`

Request:

```json
{"type":"object","additionalProperties":false,"required":["content"],"properties":{"content":{"type":"string","minLength":1},"category":{"type":"string","default":"general"},"source":{"type":"string","default":"conversation"},"importance":{"type":"integer","default":1}}}
```

Response: `{"$ref":"#/$defs/memoryItem"}`

### `retrieve_history`

Request: `{"type":"object","additionalProperties":false,"properties":{"limit":{"type":"integer","minimum":1,"default":10}}}`

Response:

```json
{"type":"array","items":{"type":"object","required":["id","speaker","content","occurred_at"],"properties":{"id":{"type":"string"},"speaker":{"type":"string"},"content":{"type":"string"},"occurred_at":{"type":"string","format":"date-time"}}}}
```

## Security MCP — Guardian

### `analyze_message`

Request: `{"type":"object","additionalProperties":false,"required":["message"],"properties":{"message":{"type":"string","minLength":1}}}`

Response: `{"$ref":"#/$defs/securityEvent"}`

### `create_security_alert`

Request:

```json
{"type":"object","additionalProperties":false,"required":["event_id"],"properties":{"event_id":{"type":"string"},"severity":{"type":"string","enum":["low","medium","high","critical"],"default":"medium"}}}
```

Response:

```json
{"type":"object","required":["id","event_id","severity","status","created_at"],"properties":{"id":{"type":"string"},"event_id":{"type":"string"},"severity":{"type":"string"},"status":{"type":"string"},"created_at":{"type":"string","format":"date-time"}}}
```

### `get_security_events`

Request: `{"type":"object","additionalProperties":false,"properties":{"limit":{"type":"integer","minimum":1,"default":20}}}`

Response: `{"type":"array","items":{"$ref":"#/$defs/securityEvent"}}`

> Note: simulated incoming phone-message ingestion is currently a Security **HTTP API** (`POST /api/v1/security/phone-messages`), not an MCP tool. Consider adding an MCP `receive_phone_message` tool if Guardian or another agent needs to invoke it.

## Inventory MCP — Guardian and Logistics

### Medication tools — Guardian only

| Tool | Request schema | Response schema |
| --- | --- | --- |
| `check_inventory` | `{}` | `{"type":"array","items":{"$ref":"#/$defs/medicationInventory"}}` |
| `request_purchase` | `{"type":"object","additionalProperties":false,"required":["medication_name","quantity","user_confirmed"],"properties":{"medication_name":{"type":"string","minLength":1},"quantity":{"type":"integer","minimum":1},"user_confirmed":{"type":"boolean"}}}` | `{"type":"object","required":["id","medication_name","quantity","status","created_at"],"properties":{"id":{"type":"string"},"medication_name":{"type":"string"},"quantity":{"type":"integer"},"status":{"type":"string"},"created_at":{"type":"string","format":"date-time"}}}` |

### Household tools — Logistics only

| Tool | Request schema | Response schema |
| --- | --- | --- |
| `check_household_inventory` | `{}` | `{"type":"array","items":{"$ref":"#/$defs/householdItem"}}` |
| `request_household_purchase` | `{"type":"object","additionalProperties":false,"required":["item_name","quantity","user_confirmed"],"properties":{"item_name":{"type":"string","minLength":1},"quantity":{"type":"integer","minimum":1},"user_confirmed":{"type":"boolean"}}}` | `{"type":"object","required":["id","item_name","quantity","status","created_at"],"properties":{"id":{"type":"string"},"item_name":{"type":"string"},"quantity":{"type":"integer"},"status":{"type":"string"},"created_at":{"type":"string","format":"date-time"}}}` |
| `create_reminder` | `{"type":"object","additionalProperties":false,"required":["title","remind_at"],"properties":{"title":{"type":"string","minLength":1},"remind_at":{"type":"string","format":"date-time"}}}` | `{"type":"object","required":["id","title","remind_at","status"],"properties":{"id":{"type":"string"},"title":{"type":"string"},"remind_at":{"type":"string","format":"date-time"},"status":{"type":"string","enum":["scheduled"]}}}` |

## Communication MCP — Companion

### `get_family_contacts`

Request: `{}`

Response: `{"type":"array","items":{"type":"object","required":["id","name","relationship"],"properties":{"id":{"type":"string"},"name":{"type":"string"},"relationship":{"type":"string"}}}}`

### `get_phone_book`

Request: `{}`

Response: `{"type":"array","items":{"type":"object","required":["id","display_name","relationship","phone_number","approved_for_calls"],"properties":{"id":{"type":"string"},"display_name":{"type":"string"},"relationship":{"type":"string"},"phone_number":{"type":"string"},"approved_for_calls":{"type":"boolean"}}}}`

### `send_family_message`

Request: `{"type":"object","additionalProperties":false,"required":["contact_id","content","user_approved"],"properties":{"contact_id":{"type":"string"},"content":{"type":"string","minLength":1},"user_approved":{"type":"boolean"}}}`

Response: `{"type":"object","required":["id","contact_id","content","status","created_at"],"properties":{"id":{"type":"string"},"contact_id":{"type":"string"},"content":{"type":"string"},"status":{"type":"string","enum":["queued"]},"created_at":{"type":"string","format":"date-time"}}}`

### `request_family_call`

Request: `{"type":"object","additionalProperties":false,"required":["contact_query"],"properties":{"contact_query":{"type":"string","minLength":1}}}`

Response: `{"type":"object","required":["id","contact_id","display_name","relationship","phone_number","status","created_at"],"properties":{"id":{"type":"string"},"contact_id":{"type":"string"},"display_name":{"type":"string"},"relationship":{"type":"string"},"phone_number":{"type":"string"},"status":{"type":"string","enum":["requested"]},"created_at":{"type":"string","format":"date-time"}}}`

### `create_notification`

Request: `{}`

Response: `null`

Status: **not implemented**. It always raises a tool error. Before enabling it, define recipient, content/template, channel, authorization/consent, delivery status, and retry policy.

## Schema Decisions to Make Next

1. Add an explicit `user_id` at API boundaries before multi-user support, while retaining existing internal ownership.
2. Add `message_type`, `drafted_by`, and an approval/audit record to simulated family messages.
3. Add contact aliases (for example `my son`, `Rahim`) instead of relying only on exact name/relationship matching.
4. Define notification fields before implementing `create_notification`.
5. Decide whether Security phone-message ingestion should become an MCP tool or remain an event/API-only capability.
