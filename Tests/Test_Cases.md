# Kindred AI — End-to-End Test Cases

This is the manual end-to-end test plan for judges and developers. It tests the experience from the React UI and Swagger, then verifies the resulting data through the visible dashboards, Swagger responses, and Langfuse traces.

## Test conventions

| Label | Meaning |
| --- | --- |
| **UI** | Run from the React application at `http://localhost:5173`. |
| **API** | Run from Swagger at `http://127.0.0.1:8000/docs`. |
| **Expected** | The result required for the test to pass. |
| **Evidence** | Where to confirm the result. |
| **Simulated** | The application records a local action only. It must not contact real people, pharmacies, or suppliers. |

## Before starting

1. Start the backend:

   ```powershell
   $env:PYTHONPATH = "$PWD\backend\src"
   & .\.venv\Scripts\python.exe -m uvicorn kindred_ai.presentation.api.app:create_app --factory --reload
   ```

2. Start the frontend:

   ```powershell
   cd frontend
   npm.cmd run dev
   ```

3. Open the React UI and Swagger in separate browser tabs.
4. For LLM-backed tests, ensure the OpenAI environment variables are configured. For tracing tests, ensure Langfuse environment variables are configured.
5. Use a fresh browser session or a fresh `session_id` where a test requires isolated conversation state.

---

## A. Startup, configuration, and contracts

| ID | Scenario | Steps | Expected | Evidence |
| --- | --- | --- | --- | --- |
| A-01 | Backend starts successfully | Start Uvicorn. | Startup completes without agent-catalog validation errors. | Terminal log and `GET /docs`. |
| A-02 | Swagger is available | Open `/docs`. | Health, Security, Memory, Companion, Logistics, Guardian, Inventory, and Master sections are visible. | Swagger UI. |
| A-03 | Default agent catalog is valid | Start backend with the default `agents.yaml`. | Master has no direct MCPs; Companion has Memory/Communication; Guardian has Security/Health/Inventory; Logistics has Inventory. | Startup log and `agents.yaml`. |
| A-04 | Invalid catalog fails safely | In a temporary copy, add an unknown MCP or invalid owner, then start backend. Restore the file afterwards. | Startup fails with a clear configuration error. | Terminal error. |
| A-05 | Browser can call backend | Open React UI with backend running. Submit a chat message. | No browser CORS error occurs. | Browser network/console and chat response. |
| A-06 | Public contract is understandable | Review `MCP_TOOL_CATALOG.md` before testing tools. | A reviewer can identify an owner, side effect, input, and response for each MCP tool. | Catalog document. |

---

## B. Login, accessibility, and UI shell

| ID | Scenario | Steps | Expected | Evidence |
| --- | --- | --- | --- | --- |
| B-01 | Login screen | Open React UI. | Country-field background, high-contrast login card, username/password fields, and password reveal control are visible. | React UI. |
| B-02 | Demo sign-in | Enter any non-empty credentials and select **Enter Kindred**. | Care Hub opens; this does not create a real authentication session. | React UI. |
| B-03 | Password visibility | Enter a password, select **Reveal**, then select **Hide**. | Field type changes between masked and visible without clearing the text. | React UI. |
| B-04 | Opaque accessibility shield | Sign in and inspect the Care Hub. | Background imagery is visually softened; cards and text remain high-contrast and legible. | React UI. |
| B-05 | Large quick actions | Inspect the left Quick actions panel on desktop and mobile width. | Medicine, Groceries, Call family, and Reminders are large, clearly labeled touch targets. | React UI. |
| B-06 | Responsive layout | Narrow browser to approximately 390 px wide. | No controls overlap or become unreachable; panels stack vertically. | React UI. |
| B-07 | UI language control | Toggle **EN** and **বাংলা**. | The shell greeting, thought, and main labels change language. Agent replies may remain English in this prototype. | React UI. |
| B-08 | Caregiver mode | Select **Caregiver**. | Medication schedules, security review, and explicit prototype/safety boundaries are visible. | React UI. |
| B-09 | Developer entry point | Select **Developer view** from the Care Hub. | Judge/Developer sandbox opens without requiring a real administrator account. | React UI. |

---

## C. Master Agent — conversation and routing

| ID | Scenario | Steps | Expected | Evidence |
| --- | --- | --- | --- | --- |
| C-01 | General conversation | Ask: “What is a rainbow?” | Master gives a warm, concise answer. No MCP record should be created solely for this question. | Chat response; Security/Health lists unchanged. |
| C-02 | Melancholy support | Ask: “I feel a little lonely today.” | Master responds empathetically and offers gentle, non-clinical support. | Chat response. |
| C-03 | Happy conversation | Ask: “My daughter is visiting today and I am so happy.” | Master acknowledges the positive event warmly. | Chat response. |
| C-04 | Empty message guard | In Swagger, post an empty Master conversation message. | Request is rejected with a clear validation/error response; no turn is stored. | Swagger response. |
| C-05 | Multi-turn context | In one session, say “My son is Rahim,” then ask “Who did I mention?” | Follow-up is informed by recent in-memory conversation context where model behaviour permits. | Chat response. |
| C-06 | Clear conversation | Select **Clear**, then ask a follow-up that depended on the previous turn. | UI transcript resets and Master’s temporary session context is cleared. | React UI and `DELETE /master/conversations/{session_id}`. |
| C-07 | Call-family routing | Ask: “Call my son.” | Master delegates to Companion; a **simulated call request** for Rahim is recorded, not a real call. | Chat response; `POST /companion/call-requests` / logs. |
| C-08 | Household reminder routing | Ask: “Remind me to buy tea leaves tomorrow at 9 AM Oslo time.” | Master delegates to Logistics and returns a scheduled reminder when the date/time is parseable. | Chat response; Logistics reminder result. |
| C-09 | Unknown specialist intent | Ask a general question unrelated to an agent workflow. | Master stays conversational and does not pretend a specialist action occurred. | Chat response and unchanged records. |

---

## D. Companion, Memory, and family communication

| ID | Scenario | Steps | Expected | Evidence |
| --- | --- | --- | --- | --- |
| D-01 | Retrieve profile | Swagger: `GET /memory/profile`. | Demo user profile is returned. | Swagger response. |
| D-02 | Store approved memory | Swagger: `POST /memory/memories` with a preference such as “Anita enjoys cardamom tea.” | A memory ID and timestamp are returned. | Swagger response. |
| D-03 | Memory-informed conversation | After D-02, ask: “What tea do I enjoy?” | Companion response uses stored memory where retrieval/model behaviour permits; it must not invent unrelated facts. | Chat and `GET /memory/history`. |
| D-04 | Reject blank memory | Swagger: save memory with blank content. | Validation error; no memory is stored. | Swagger and history unchanged. |
| D-05 | Family contacts | Swagger: `GET /companion/contacts`. | Seeded family contacts include son Rahim and daughter Sara. | Swagger response. |
| D-06 | Phone book | Swagger: `GET /companion/phone-book`. | Approved call contacts are listed with prototype phone numbers. | Swagger response. |
| D-07 | Simulated call by relationship | Swagger: `POST /companion/call-requests` with `{"contact_query":"son"}`. | A local `requested` call record for Rahim is returned. No call is placed. | Swagger response. |
| D-08 | Unknown call contact | Submit `{"contact_query":"neighbour"}`. | Clear 422 error; no call request record is created. | Swagger response. |
| D-09 | Approved family message | Submit `POST /companion/family-messages` with `contact_id: "daughter"`, non-empty content, and `user_approved: true`. | A `queued` simulated message is returned. | Swagger response. |
| D-10 | Approval is enforced | Repeat D-09 with `user_approved: false`. | Clear error; no message is queued. | Swagger response. |
| D-11 | Missing message content | Submit an empty family-message body. | Clear error; no message is queued. | Swagger response. |

---

## E. Health, medication adherence, and medication inventory

| ID | Scenario | Steps | Expected | Evidence |
| --- | --- | --- | --- | --- |
| E-01 | Medication schedule | Swagger: `GET /health/medication-schedule`. | Active seeded schedules include daily local times and `Europe/Oslo` timezone. | Swagger response. |
| E-02 | Record a dose through Swagger | `POST /health/medication-taken` using `demo-schedule-metformin`. | New taken record with ID and timestamp is returned. | Swagger response and health events. |
| E-03 | Record a dose from Admin | Developer view → **Record dose taken**. | Same real API call succeeds and a positive status message appears. | UI, Swagger events. |
| E-04 | Unknown/inactive schedule protection | Post a made-up or inactive `schedule_id`. | Clear 422 error and no taken record is created. | Swagger response and health events unchanged. |
| E-05 | Medication supply question | Ask: “How many days of Metformin do I have left?” | Master delegates to Guardian and reports days based on stored schedule/inventory data. | Chat response; Guardian supply endpoint. |
| E-06 | Refill warning | Review `GET /guardian/medication-supply` for seeded low-stock medication. | A warning is returned at seven days or fewer. | Swagger response. |
| E-07 | Refill confirmation required | Ask to order a medicine without saying “confirm”. | Master explains that explicit confirmation is required; no request is inserted. | Chat and Inventory requests unchanged. |
| E-08 | Confirmed refill | Ask with specific medicine/quantity and explicit “confirm”. | Guardian records one simulated replenishment request. No pharmacy order is placed. | Chat and `POST /guardian/replenishment-requests`. |
| E-09 | Health event order | `GET /health/events`. | Events are returned newest first. | Swagger response. |

---

## F. Security inbox and safety routing

| ID | Scenario | Steps | Expected | Evidence |
| --- | --- | --- | --- | --- |
| F-01 | General safety advice does not create records | Note count of Security events/alerts. Ask: “Someone called asking for the code sent to my phone. Is it safe?” | Master gives cautious general advice. Security event/alert counts do not change. | Chat plus `GET /security/events`. |
| F-02 | High-risk simulated SMS | Developer view → submit the default verification-code scam message. | Message is stored, classified by the Security workflow, and creates an alert for medium/high/critical risk. | Developer status; `GET /security/phone-messages`; `GET /security/events`. |
| F-03 | Low-risk simulated SMS | Swagger: submit “The library closes at 5 PM today.” | Message is stored with low-risk result and no new alert. | Phone-message list and alert/event counts. |
| F-04 | Inbox list order | Submit two different messages, then list phone messages. | Newest message appears first with analysis state/result. | `GET /security/phone-messages`. |
| F-05 | Empty message rejection | Post `{"message":""}` to `/security/phone-messages`. | 422 error; no record or alert is created. | Swagger response. |
| F-06 | Model-analysis failure safety | With a temporary invalid/unavailable LLM configuration, submit a phone message. Restore configuration afterwards. | Message remains stored with failed analysis state; API returns clear error; no unknown-risk alert is created. | API response and phone-message list. |
| F-07 | Deterministic legacy endpoint | Swagger: `POST /security/analyze-message` with a scam message. | Security event is created through the legacy deterministic prototype endpoint. | Swagger event list. |
| F-08 | Alert severity validation | Create an alert with an invalid severity. | Validation error; no alert created. | Swagger response. |
| F-09 | Guardian security guidance | Use `POST /guardian/analyze` with a suspicious message. | Guardian returns event/alert context and cautious guidance where the LLM is configured. | Swagger response. |

---

## G. Logistics and household inventory

| ID | Scenario | Steps | Expected | Evidence |
| --- | --- | --- | --- | --- |
| G-01 | Household stock view | `GET /logistics/household-inventory`. | Seeded household items show quantity, threshold, and reorder state. | Swagger response. |
| G-02 | Household question routing | Ask: “Do I need to buy Jasmine tea?” | Master delegates to Logistics and uses household inventory context. | Chat response. |
| G-03 | Reminder creation | Developer view → create a reminder; or call `POST /logistics/reminders`. | Local `scheduled` reminder is returned. No external notification is sent. | UI status / Swagger response. |
| G-04 | Reminder validation | Submit blank title or invalid timestamp. | Validation error; no reminder created. | Swagger response. |
| G-05 | Household purchase confirmation required | Ask for an item but do not explicitly confirm. | Master explains confirmation is required; no request is recorded. | Chat and purchase list unchanged. |
| G-06 | Confirmed household purchase | Ask with item/quantity and explicit “confirm”; or use Developer view. | Local confirmed simulated request is created. | Chat / Swagger response. |
| G-07 | Invalid quantity | Submit quantity `0` or negative. | Validation error; no purchase request is recorded. | Swagger response. |

---

## H. Developer/Judge sandbox end-to-end

| ID | Scenario | Steps | Expected | Evidence |
| --- | --- | --- | --- | --- |
| H-01 | Enter sandbox | From login or Care Hub, open Developer view. | Sandbox clearly says it writes through real backend APIs. | React UI. |
| H-02 | Security data injection | Save a custom simulated SMS, then return to Caregiver view. | Security result/alert is visible after refresh when risk warrants it. | UI and Swagger. |
| H-03 | Memory data injection | Save a custom memory, then ask the related Companion question. | Memory is stored; Companion can use it as context. | UI and Swagger. |
| H-04 | Reminder data injection | Create a reminder with custom title. | Success status identifies the API path; reminder exists in backend response. | UI and Swagger. |
| H-05 | Family-message data injection | Queue a message to son and daughter. | Both are local `queued` records only; no real delivery occurs. | UI status and Communication DB/API response. |
| H-06 | Purchase data injection | Request Jasmine tea. | Local confirmed simulated request only. | UI status and Swagger. |
| H-07 | Backend unavailable | Stop backend, reload UI, then submit a sandbox form. | UI shows a useful failure message; browser does not crash. | React UI and browser console. |
| H-08 | Scope boundary | Review the sandbox footer. | It does not claim update/delete/bulk operations that are not implemented by audited backend APIs. | React UI. |

---

## I. Voice, observability, and regression checks

| ID | Scenario | Steps | Expected | Evidence |
| --- | --- | --- | --- | --- |
| I-01 | Voice canvas affordance | Select **Tap to talk** in React UI. | UI guides the user to the text conversation and accurately explains that React WebRTC streaming is not yet live. | React UI. |
| I-02 | Realtime voice test | Run the React Care Hub with a valid Realtime model configuration. | Push-to-talk test connects and responds; it can consult Master specialist context. | React Care Hub and terminal. |
| I-03 | Agent trace | Make a medication-supply query with Langfuse configured. | A trace shows Master conversation, router generation, Guardian delegation, and MCP tool calls. | Langfuse dashboard. |
| I-04 | No secret leakage | Inspect UI errors, terminal logs, Langfuse input/output, and repository status after a test. | API keys, passwords, and raw sensitive tokens are not exposed. | Browser/terminal/Langfuse/Git diff. |
| I-05 | Automated regression suite | Run backend tests. | All current automated tests pass. | `python -m unittest discover -s backend/tests -v`. |
| I-06 | Frontend build | Run `npm.cmd run build` from `frontend`. | TypeScript/Vite build completes successfully. | Terminal output. |

---

## J. Explicitly deferred tests — do not mark as passing today

These scenarios are product goals, not current prototype capabilities. Keeping them visible prevents judges from mistaking a simulated action for a live one.

| ID | Deferred capability | Current expected result |
| --- | --- | --- |
| J-01 | Real SMS, phone, pharmacy, or supplier delivery | No real delivery must occur. |
| J-02 | Continuous browser microphone/WebRTC session | React UI must state it is not yet live. |
| J-03 | Scheduled 09:00 proactive wake-up | No automatic background wake-up is implemented. |
| J-04 | Automatic medication reminder 15 minutes before a dose | No live scheduler/notification delivery is implemented. |
| J-05 | 48-hour inactivity caregiver emergency alert | No live telemetry or emergency escalation is implemented. |
| J-06 | Full Bengali agent responses | UI shell can switch labels; agent-language routing remains future work. |
| J-07 | Admin update/delete/bulk data operations | Current sandbox supports approved inserts only; dedicated audited endpoints are required first. |
| J-08 | Authentication and production authorization | Demo sign-in is not real authentication. |

---

## Completion checklist for a judge demonstration

- [ ] A-01 through A-05 pass.
- [ ] One general conversation, one Companion flow, one Guardian medication flow, and one Logistics flow pass.
- [ ] F-01 and F-02 both pass, proving general safety advice is separate from stored-message scanning.
- [ ] At least one Developer sandbox action is reflected in Swagger or Caregiver view.
- [ ] I-03 is visible in Langfuse when tracing is configured.
- [ ] J-section items are described honestly as deferred rather than demonstrated as live functionality.
