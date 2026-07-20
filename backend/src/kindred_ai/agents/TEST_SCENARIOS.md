# Temporary UI Agent Test Scenarios

Use the temporary Gradio interface while building each agent. It is a development harness only and does not replace the future React Native/WebRTC interface.

## Master Agent → Guardian Agent — available now

- Fraud detection: `Urgent: send your gift card details now.`
  - Expected: Master gives a conversational safety reply using a high-risk Guardian result and an open alert.
- Safe message: `My daughter will call this evening.`
  - Expected: Master gives a conversational reply using a low-risk Guardian result and no alert.
- Medication stock: `show medication supply`
  - Expected: Master explains that Metformin has six days remaining and a refill warning.
- Confirmed refill: `confirm order Metformin 60`
  - Expected: Master confirms a persisted `requested` replenishment request.
- Invalid refill command: `confirm order Metformin`
  - Expected: usage guidance; no request created.

## Companion Agent — planned

- Ask for a poem and confirm it uses saved user preferences.
- Ask for a prior conversation detail and confirm Memory MCP context is used.
- Ask to contact a family member and confirm the request is routed through Communication MCP.

## Logistics Agent — available through Swagger

- In Swagger, call `GET /api/v1/logistics/household-inventory`; expect separate household stock, including a low-stock Jasmine tea item.
- Call `POST /api/v1/logistics/purchase-requests` with Jasmine tea, quantity `2`, and `user_confirmed: false`; expect rejection and no request.
- Repeat with `user_confirmed: true`; expect a locally persisted `requested` purchase request. No external order is ever placed by this prototype.
- Call `POST /api/v1/logistics/reminders` with `{"title":"Buy Jasmine tea","remind_at":"2026-07-26T09:00:00+02:00"}`; expect a `scheduled` reminder. Delivery through Communication MCP is deferred.

## Master Agent — next scenarios

- Ask: `I feel lonely today.` Expect Master to delegate to Companion and return a warm, memory-informed answer.
- Ask: `Call my son.` Expect Master to resolve a saved phone-book contact with the relationship `son` and record a local call request. It must say that no real call is placed in this prototype.
- Ask: `Do I need to buy Jasmine tea?` Expect Master to delegate to Logistics and explain the household stock/reorder result.
- Ask a follow-up such as `What did I just ask about?` in the same text-chat session. Expect Master to receive the recent session context.
- Select **Clear** in the temporary UI, then ask the follow-up again. Expect the temporary session context to be gone.
- Submit English and Bengali requests and verify language detection/routing when Bengali is implemented.
# Companion Agent scenarios

- Ask: "What do you remember about me?" Expect a warm response grounded in Anita's Memory MCP profile/history.
- Ask: "I feel lonely today." Expect Companion to respond warmly without accessing Health or Security data.
- In Swagger, call `GET /api/v1/companion/contacts`; expect the fictional approved family contacts.
- In Swagger, call `POST /api/v1/companion/family-messages` with `user_approved: false`; expect rejection.
- Repeat with `user_approved: true`; expect a locally `queued` message only—no real external delivery.
