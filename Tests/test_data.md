# Kindred AI — Developer-Mode Test Data

## Recommended size: 30 records

Start with **30 records**. This gives the judges meaningful variation across security, memory, reminders, medication adherence, communication, and household logistics, while keeping the manual data-entry session to about 15–20 minutes.

Use 50 records only after the 30-record set is working. A 100-record dataset is unnecessary for this prototype until a dedicated bulk-import API exists.

## Important rules

- Enter records only through **Developer view** in the React UI for this exercise.
- Do **not** enter real personal, medical, financial, or phone data. Everything below is fictional.
- A family message, call, reminder, and purchase request is always **simulated**. Nothing is delivered or ordered externally.
- Security phone-message risk is model-classified. The “expected band” is a review guide, not a hard deterministic assertion.
- The Developer view currently supports inserts. It does not yet support update, delete, or bulk upload.

## How to enter the dataset

1. Run backend and frontend.
2. Sign in using any demo credentials.
3. Open **Developer view**.
4. Enter each record in the order shown below.
5. After each section, verify it through Swagger or Caregiver view before continuing.

---

## Dataset overview

| Area | Records | Developer-view card | Why it matters |
| --- | ---: | --- | --- |
| Simulated phone inbox | 10 | **Simulate a phone message** | Tests low-risk information, suspicious messages, and safety alerts. |
| Personal memory | 7 | **Save a memory** | Gives Companion realistic preferences and relationships to retrieve. |
| Household reminders | 5 | **Add a reminder** | Tests Logistics reminder creation and conversational follow-up. |
| Medication adherence | 3 | **Verify medication** | Tests dose-record persistence and Health event history. |
| Family communication | 3 | **Queue a family message** | Tests both approved seeded contacts. |
| Household purchases | 2 | **Request household item** | Tests explicit simulated Logistics purchase requests. |
| **Total** | **30** |  |  |

---

## 1. Simulated phone inbox — 10 records

For each row, paste the text into **Simulate a phone message**, then select **Save and analyse**.

| ID | Message text | Expected risk band | Expected behaviour |
| --- | --- | --- | --- |
| S-01 | `Hi Anita, this is Sara. I will visit you on Sunday afternoon. Love you!` | Low | Stored; no alert expected. |
| S-02 | `The community library will close at 5 PM today because of staff training.` | Low | Stored; no alert expected. |
| S-03 | `Water maintenance is planned from 2 PM to 3 PM today. Please store water if needed.` | Low | Stored as useful local information; no alert expected. |
| S-04 | `Your clinic appointment is confirmed for Tuesday at 10:30 AM. Reply STOP to opt out.` | Low | Stored; no alert expected. |
| S-05 | `Your parcel is waiting. Track it at https://delivery-example.test/track/123` | Low or Medium | Stored; review the model explanation. An alert is acceptable only if classified medium or higher. |
| S-06 | `URGENT: Your bank account is blocked. Send the verification code from your phone now to avoid suspension.` | High | Stored and alert expected. |
| S-07 | `You have been selected for a tax refund. Pay a small processing fee today to receive the money.` | High | Stored and alert expected. |
| S-08 | `Microsoft security team detected a virus. Install remote support now and give the technician access to your phone.` | High or Critical | Stored and alert expected. |
| S-09 | `Buy three gift cards immediately and send the numbers to resolve your legal case.` | High | Stored and alert expected. |
| S-10 | `Congratulations! You won 100,000 kroner. Click here and enter your card details to claim it today.` | High or Critical | Stored and alert expected. |

### Verify after S-01 to S-10

- Swagger: `GET /api/v1/security/phone-messages` shows all ten, newest first.
- Swagger: `GET /api/v1/security/events` shows events/alerts for non-low classifications.
- Caregiver view shows security-review items after refresh.
- Ask the Master: **“Someone asked for a code sent to my phone. Is it safe?”** Confirm it gives general advice but does **not** add an eleventh phone-message record.

---

## 2. Personal memory — 7 records

Paste each item into **Save a memory**, then select **Save memory**. The current Developer card saves every item as category `preference`; the suggested category below is a future data-model label and is included to make the test intent clear.

| ID | Memory text | Suggested category | Suggested follow-up question |
| --- | --- | --- | --- |
| M-01 | `Anita enjoys cardamom tea in the morning.` | preference | `What tea do I enjoy?` |
| M-02 | `Anita likes to sit in the garden when the weather is sunny.` | preference | `What do I enjoy doing on sunny days?` |
| M-03 | `Rahim is Anita's son and Sara is Anita's daughter.` | relationship | `Who are my children?` |
| M-04 | `Anita prefers gentle reminders rather than loud alarms.` | preference | `How should you remind me?` |
| M-05 | `Anita enjoys listening to old Bengali songs after dinner.` | preference | `What music do I enjoy?` |
| M-06 | `Anita's anniversary is on 18 September.` | important_date | `When is my anniversary?` |
| M-07 | `Anita prefers appointments in the late morning when possible.` | preference | `What appointment time do I prefer?` |

### Verify after M-01 to M-07

- Swagger: `GET /api/v1/memory/history` shows stored records where applicable.
- Ask each suggested follow-up in the Care Hub. The answer should use stored information when Companion retrieval/model behaviour permits.
- The agent must not invent a fact that was not supplied.

---

## 3. Household reminders — 5 records

Enter each title in **Add a reminder**, then select **Create reminder**. The current Developer view uses a fixed prototype time of `2026-07-26T09:00:00+02:00`; title variation is the purpose of this dataset.

| ID | Reminder title | Conversational test after insert |
| --- | --- | --- |
| R-01 | `Buy cardamom tea` | `Remind me to buy cardamom tea tomorrow at 9 AM Oslo time.` |
| R-02 | `Water the balcony plants` | `Remind me to water the balcony plants tomorrow at 9 AM Oslo time.` |
| R-03 | `Call Sara after lunch` | `Remind me to call Sara tomorrow at 9 AM Oslo time.` |
| R-04 | `Prepare documents for clinic visit` | `Remind me to prepare clinic documents tomorrow at 9 AM Oslo time.` |
| R-05 | `Buy milk and bread` | `Remind me to buy milk and bread tomorrow at 9 AM Oslo time.` |

### Verify after R-01 to R-05

- Each submission returns a `scheduled` local reminder.
- No SMS, push notification, or real alarm is sent.
- A Master reminder request with a parseable Oslo timestamp delegates to Logistics.

---

## 4. Medication adherence — 3 records

The Developer card is intentionally fixed to the seeded active schedule `demo-schedule-metformin` and adds the note `Recorded from developer sandbox`.

| ID | Action | Expected behaviour |
| --- | --- | --- |
| H-01 | Select **Record dose taken** once. | A Metformin taken record is stored. |
| H-02 | Select **Record dose taken** a second time. | A second independent record is stored. |
| H-03 | Select **Record dose taken** a third time. | A third independent record is stored. |

### Verify after H-01 to H-03

- Swagger: `GET /api/v1/health/events` shows newly created events newest first.
- Caregiver and Elder medication cards still show active schedules.
- Ask: **“How many days of Metformin do I have left?”** The answer must be based on the seeded schedule and inventory, not invented.

---

## 5. Family communication — 3 records

Use **Queue a family message**. The current card uses the approved text `Please call me when you can.` and exposes the seeded contact selector.

| ID | Select contact | Expected behaviour |
| --- | --- | --- |
| C-01 | `Rahim (son)` | A local simulated message is returned with status `queued`. |
| C-02 | `Sara (daughter)` | A local simulated message is returned with status `queued`. |
| C-03 | `Rahim (son)` | Another independent local simulated message is returned. |

### Verify after C-01 to C-03

- No real message is sent.
- Swagger: `GET /api/v1/companion/phone-book` shows both approved contacts.
- In Care Hub, ask **“Call my son.”** Confirm the Master records a simulated call request and explains it does not place a real call.

---

## 6. Household purchases — 2 records

Use **Request household item** twice. It submits the seeded item `Jasmine tea`, quantity `2`, with explicit user confirmation.

| ID | Action | Expected behaviour |
| --- | --- | --- |
| L-01 | Select **Request Jasmine tea**. | A confirmed simulated household purchase request is stored. |
| L-02 | Select **Request Jasmine tea** again. | A second independent request is stored. |

### Verify after L-01 to L-02

- No external supplier is contacted.
- Swagger: `GET /api/v1/logistics/household-inventory` still shows stock/reorder information.
- Ask **“Do I need to buy Jasmine tea?”** and confirm Logistics context is used.
- Ask for a household purchase without saying **confirm**; confirm no request is created.

---

## Post-population acceptance checks

After all 30 records are entered, run these checks before the full end-to-end test plan:

- [ ] 10 phone messages are visible; benign and suspicious examples are both present.
- [ ] At least 7 memories are present and can support Companion questions.
- [ ] 5 reminders have been created.
- [ ] 3 medication-taken records exist for the active Metformin schedule.
- [ ] 3 family messages are queued locally only.
- [ ] 2 household purchase requests are recorded locally only.
- [ ] General fraud advice does not create a security inbox record.
- [ ] Caregiver view can display medication and security information after refresh.
- [ ] Langfuse shows Master/agent/MCP activity if Langfuse is configured.

## What not to enter through Developer mode

- Real bank account numbers, verification codes, passwords, addresses, or real phone numbers.
- Any genuine prescription, medical diagnosis, emergency report, or personally identifying information.
- Data intended to test real delivery, calling, or ordering. Those functions are not connected in this prototype.
