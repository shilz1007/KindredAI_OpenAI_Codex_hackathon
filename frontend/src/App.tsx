import { FormEvent, useEffect, useMemo, useState } from "react";
import "./voice.css";

type ChatMessage = { role: "user" | "assistant"; content: string };
type Medication = { id: string; medication_name: string; dose_instructions: string; daily_times: string[] };
type MedicationStock = { id: string; schedule_id: string; medication_name: string; units_available: number };
type PhoneBookContact = { id: string; display_name: string; relationship: string; phone_number: string; approved_for_calls: boolean };
type PhoneMessage = { id: string; message: string; received_at: string; analysis_status: string; risk_level: "low" | "medium" | "high" | "critical" | null; explanation: string | null; signals: string[] };
type MedicationSupply = { medication_name: string; units_available: number; daily_units: number; days_remaining: number; refill_needed: boolean };
type HouseholdItem = { id: string; item_name: string; quantity_available: number; reorder_threshold: number; reorder_needed: boolean };
type Reminder = { id: string; title: string; remind_at: string; status: string };
type QuickAction = "medicines" | "groceries" | "family" | "reminders";
type SpeechRecognitionResultLike = { isFinal: boolean; 0: { transcript: string } };
type SpeechRecognitionLike = {
  lang: string; interimResults: boolean; continuous: boolean; maxAlternatives: number;
  start: () => void;
  stop: () => void;
  onstart: (() => void) | null;
  onresult: ((event: { results: ArrayLike<SpeechRecognitionResultLike> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
};
type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

function readableChatText(content: string): string {
  // Keep older model responses readable even if they contain Markdown.
  return content
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/(?:^|\s)-\s+(?=[A-Z])/g, "\n• ")
    .replace(/^#{1,6}\s*/gm, "");
}

const API = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
const sessionId = crypto.randomUUID();
const DEMO_USERNAME = "anita";
const DEMO_PASSWORD = "kindred-demo";
const DEMO_SESSION_KEY = "kindred_demo_signed_in";
const WELCOME_MESSAGE: ChatMessage = { role: "assistant", content: "Good morning, Anita. I am here whenever you need me." };
const VOICE_PAUSE_MS = 2500;
const DEFAULT_THOUGHT = "Every new day brings a small reason to smile.";

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail ?? "Kindred could not complete that request.");
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>;
}

function comfortingEnglishVoice(): SpeechSynthesisVoice | undefined {
  const voices = window.speechSynthesis.getVoices();
  const englishVoices = voices.filter(voice => /^en-(GB|US|AU|CA|NZ|IN)/i.test(voice.lang));
  const femaleVoiceName = /sonia|libby|jenny|zira|hazel|samantha|serena|ava|aria|emma|olivia|female/i;
  return englishVoices.find(voice => femaleVoiceName.test(voice.name))
    ?? englishVoices.find(voice => /^en-GB/i.test(voice.lang))
    ?? englishVoices.find(voice => /^en-US/i.test(voice.lang))
    ?? englishVoices[0];
}

const copy = {
  en: {
    greeting: (name: string) => `Good ${new Date().getHours() < 12 ? "morning" : new Date().getHours() < 18 ? "afternoon" : "evening"}, ${name}`,
    thought: "A gentle step today is still a beautiful journey forward.",
    listen: "Tap to talk", thinking: "Kindred is thinking", chat: "Chat with Kindred", quick: "Quick actions", today: "Today at a glance",
  },
  bn: {
    greeting: (name: string) => `শুভেচ্ছা, ${name}`,
    thought: "আজকের ছোট একটি পদক্ষেপও সুন্দর অগ্রগতি।", listen: "কথা বলতে ট্যাপ করুন", thinking: "Kindred ভাবছে", chat: "Kindred-এর সাথে কথা বলুন", quick: "দ্রুত কাজ", today: "আজকের সারাংশ",
  },
};

export function App() {
  const [signedIn, setSignedIn] = useState(() => sessionStorage.getItem(DEMO_SESSION_KEY) === "true");
  const [screen, setScreen] = useState<"hub" | "admin">("hub");
  const [role, setRole] = useState<"elder" | "caregiver">("elder");
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [voiceStatus, setVoiceStatus] = useState<"idle" | "listening" | "sending">("idle");
  const [voiceReview, setVoiceReview] = useState("");
  const [medications, setMedications] = useState<Medication[]>([]);
  const [medicationSupply, setMedicationSupply] = useState<MedicationSupply[]>([]);
  const [phoneMessages, setPhoneMessages] = useState<PhoneMessage[]>([]);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [activeQuickAction, setActiveQuickAction] = useState<QuickAction | null>(null);
  const [dailyThought, setDailyThought] = useState(DEFAULT_THOUGHT);
  const text = copy.en;
  const date = useMemo(() => new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long" }).format(new Date()), []);

  const refresh = async () => {
    try {
      const [schedule, supply, inbox, scheduledReminders] = await Promise.all([
        api<Medication[]>("/health/medication-schedule"),
        api<MedicationSupply[]>("/guardian/medication-supply"),
        api<PhoneMessage[]>("/security/phone-messages?limit=20"),
        api<Reminder[]>("/logistics/reminders"),
      ]);
      setMedications(schedule); setMedicationSupply(supply); setPhoneMessages(inbox); setReminders(scheduledReminders);
    } catch { setNotice("The dashboard will refresh when the Kindred backend is running."); }
  };
  useEffect(() => { void refresh(); }, []);
  useEffect(() => {
    if (!signedIn) return;
    void api<{ thought: string }>("/master/welcome-thought", { method: "POST" })
      .then(result => setDailyThought(result.thought))
      .catch(() => setDailyThought(DEFAULT_THOUGHT));
  }, [signedIn]);

  const sendMessage = async (rawMessage: string, speakReply = false) => {
    const message = rawMessage.trim(); if (!message || loading) return;
    setMessages(items => [...items, { role: "user", content: message }]); setDraft(""); setLoading(true); setNotice("");
    try {
      const result = await api<{ reply: string }>(`/master/conversations/${sessionId}/turns`, { method: "POST", body: JSON.stringify({ message }) });
      setMessages(items => [...items, { role: "assistant", content: result.reply }]); await refresh();
      if (speakReply && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(result.reply);
        const voice = comfortingEnglishVoice();
        utterance.voice = voice ?? null;
        utterance.lang = voice?.lang || "en-GB";
        utterance.rate = 0.92;
        utterance.pitch = 1.05;
        window.speechSynthesis.speak(utterance);
      }
    } catch (reason) { setNotice(reason instanceof Error ? reason.message : "Unable to reach Kindred."); }
    finally { setLoading(false); setVoiceStatus("idle"); }
  };

  const send = async (event: FormEvent) => {
    event.preventDefault();
    await sendMessage(draft);
  };

  const startVoiceConversation = () => {
    if (loading || voiceStatus === "listening") return;
    const speechWindow = window as Window & { SpeechRecognition?: SpeechRecognitionConstructor; webkitSpeechRecognition?: SpeechRecognitionConstructor };
    const Recognition = speechWindow.SpeechRecognition ?? speechWindow.webkitSpeechRecognition;
    if (!Recognition) {
      setNotice("Voice input is not available in this browser. Please use Microsoft Edge or Google Chrome, or type your message below.");
      return;
    }
    const recognition = new Recognition();
    let finalTranscript = "";
    let pauseTimer: number | undefined;
    const reviewVoiceTranscript = () => {
      if (!finalTranscript) { setVoiceStatus("idle"); return; }
      recognition.stop();
      setDraft(finalTranscript);
      setVoiceReview(finalTranscript);
      setVoiceStatus("idle");
      setNotice("Please check what I heard, then send it or try speaking again.");
    };
    const waitForPossibleContinuation = () => {
      if (pauseTimer) window.clearTimeout(pauseTimer);
      pauseTimer = window.setTimeout(reviewVoiceTranscript, VOICE_PAUSE_MS);
    };
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.continuous = true;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => { setVoiceStatus("listening"); setNotice("Listening… take your time. Kindred will wait briefly after you pause."); };
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results).map(result => result[0].transcript).join(" ").trim();
      setDraft(transcript);
      if (event.results[event.results.length - 1]?.isFinal) {
        finalTranscript = transcript;
        waitForPossibleContinuation();
      }
    };
    recognition.onerror = (event) => {
      if (pauseTimer) window.clearTimeout(pauseTimer);
      setVoiceStatus("idle");
      if (event.error !== "aborted") setNotice(`Voice input could not start: ${event.error}. Check your microphone permission and try again.`);
    };
    recognition.onend = () => {
      if (finalTranscript && !pauseTimer) waitForPossibleContinuation();
      if (!finalTranscript) setVoiceStatus("idle");
    };
    recognition.start();
  };

  const signIn = (destination: "hub" | "admin" = "hub") => {
    sessionStorage.setItem(DEMO_SESSION_KEY, "true");
    setScreen(destination);
    setSignedIn(true);
  };

  const logout = () => {
    sessionStorage.removeItem(DEMO_SESSION_KEY);
    window.speechSynthesis?.cancel();
    setMessages([WELCOME_MESSAGE]);
    setDraft("");
    setNotice("");
    setVoiceStatus("idle");
    setScreen("hub");
    setRole("elder");
    setSignedIn(false);
  };

  if (!signedIn) return <Login onLogin={() => signIn()} onAdmin={() => signIn("admin")} />;
  if (screen === "admin") return <Admin onBack={() => setScreen("hub")} onLogout={logout} />;

  const quickActionHelp: Record<string, { action: QuickAction; help: string }> = {
    "My medicines": { action: "medicines", help: "See supplies or record a dose" },
    Groceries: { action: "groceries", help: "Check household supplies" },
    "Call family": { action: "family", help: "Ask a trusted person to call" },
    Reminders: { action: "reminders", help: "View or add a reminder" },
  };
  const quickActions = [
    ["💊", "My medicines", "Show my medication supply"], ["🛒", "Groceries", "Do I need to buy Jasmine tea?"],
    ["👪", "Call family", "Tell my son to call me"], ["⏰", "Reminders", "Remind me to buy tea leaves"],
  ];
  return <main className="kindred-shell">
    <header className="kindred-header">
      <div><p className="eyebrow">KINDRED CARE COMPANION</p><h1>{text.greeting("Anita")}</h1><p className="date-label">{date}</p></div>
      <div className="header-actions">
        <div className="role-toggle"><button className={role === "elder" ? "active" : ""} onClick={() => setRole("elder")}>Elder</button><button className={role === "caregiver" ? "active" : ""} onClick={() => setRole("caregiver")}>Caregiver</button></div>
        <span className="signed-in-label">Signed in as Anita</span>
        <button className="quiet-button" onClick={() => setScreen("admin")}>Family Admin</button>
        <button className="quiet-button" onClick={logout}>Log out</button>
      </div>
    </header>
    <section className="thought-card"><span>✦</span><p><strong>Thought of the day</strong>{dailyThought}</p></section>
    {role === "caregiver" ? <Caregiver medicationSupply={medicationSupply} phoneMessages={phoneMessages} refresh={refresh} /> : <section className="hub-grid">
      <aside className="quick-panel" aria-label="Quick actions"><h2>{text.quick}</h2>{quickActions.map(([icon, label]) => <button key={label} onClick={() => setActiveQuickAction(quickActionHelp[label].action)}><span aria-hidden>{icon}</span><strong>{label}</strong><small>{quickActionHelp[label].help}</small></button>)}</aside>
      <section className="voice-canvas">
        <div className="agent-status"><span className={loading || voiceStatus !== "idle" ? "status-dot busy" : "status-dot"} />{voiceStatus === "listening" ? "Listening…" : voiceStatus === "sending" || loading ? text.thinking : "Kindred is ready"}</div>
        <button className={`voice-orb ${voiceStatus === "listening" ? "listening" : ""}`} onClick={startVoiceConversation} aria-label={text.listen} aria-pressed={voiceStatus === "listening"}><span>✦</span><strong>{voiceStatus === "listening" ? "Listening…" : text.listen}</strong><small>{voiceStatus === "listening" ? "Pause when you are finished" : text.chat}</small></button>
        <p className="voice-help">Talk with me about anything you would like. I am here to listen and help.</p>
        {voiceReview && <div className="voice-review" role="status"><p><strong>I heard:</strong> “{voiceReview}”</p><div><button onClick={() => { const transcript = voiceReview; setVoiceReview(""); void sendMessage(transcript, true); }}>Send this</button><button className="quiet-button" onClick={() => { setVoiceReview(""); setDraft(""); setNotice(""); }}>Try again</button></div></div>}
      </section>
      <TodayCare medications={medications} reminders={reminders} phoneMessages={phoneMessages} />
    </section>}
    <section className="lower-grid">
      <section className="info-card"><div className="section-title"><h2>Medication today</h2><button onClick={() => setDraft("Show my medication schedule")}>Ask Kindred</button></div>{medications.length ? medications.map(item => <p className="medicine" key={item.id}><span>✓</span><strong>{item.medication_name}</strong><small>{item.dose_instructions} · {item.daily_times.join(", ")}</small></p>) : <p>Medication information appears here when the backend is running.</p>}</section>
      <section className="chat-card"><div className="section-title"><h2>{text.chat}</h2><button onClick={() => setMessages([{ role: "assistant", content: "Conversation cleared. How can I help?" }])}>Clear</button></div><div className="chat" aria-live="polite">{messages.slice(-4).map((message, index) => <p className={`bubble ${message.role}`} key={index}>{readableChatText(message.content)}</p>)}{loading && <p className="bubble assistant">{text.thinking}…</p>}</div><form onSubmit={send}><label htmlFor="message">Type your message</label><div className="composer"><input id="message" value={draft} onChange={event => setDraft(event.target.value)} placeholder="For example: Tell my son to call me" /><button>Send</button></div></form></section>
    </section>
    {notice && <p className="notice" role="status">{notice}</p>}
    <p className="prototype-footer">Prototype mode · no real calls, messages, purchases, or health decisions are made.</p>
    {activeQuickAction && <QuickActionPanel action={activeQuickAction} onClose={() => setActiveQuickAction(null)} onChanged={refresh} />}
  </main>;
}

function TodayCare({ medications, reminders, phoneMessages }: { medications: Medication[]; reminders: Reminder[]; phoneMessages: PhoneMessage[] }) {
  const now = new Date();
  const todayKey = now.toDateString();
  const currentMinutes = now.getHours() * 60 + now.getMinutes();
  const nextMedicine = medications.flatMap(medicine => medicine.daily_times.map(time => {
    const [hours, minutes] = time.split(":").map(Number);
    return { medication_name: medicine.medication_name, time, minutes: hours * 60 + minutes };
  })).sort((left, right) => (left.minutes > currentMinutes ? left.minutes : left.minutes + 1440) - (right.minutes > currentMinutes ? right.minutes : right.minutes + 1440))[0];
  const todayReminders = reminders.filter(reminder => new Date(reminder.remind_at).toDateString() === todayKey);
  const safeMessages = phoneMessages.filter(message => message.analysis_status === "completed" && message.risk_level === "low");
  return <aside className="day-panel live-care-panel"><h2>Today’s care</h2>{nextMedicine ? <div className="agenda-item"><span className="agenda-time">{nextMedicine.time}</span><p><strong>Next medicine</strong><br />{nextMedicine.medication_name}</p></div> : <div className="agenda-item"><p><strong>No medicine scheduled</strong><br />No medicine plans are available yet.</p></div>}{todayReminders.length ? todayReminders.slice(0, 2).map(reminder => <div className="agenda-item" key={reminder.id}><span className="agenda-time">{new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit" }).format(new Date(reminder.remind_at))}</span><p><strong>Reminder</strong><br />{reminder.title}</p></div>) : <div className="agenda-item care-empty"><p><strong>No reminders due today.</strong> Enjoy a calm day at your own pace.</p></div>}<section className="safety-note"><strong>Messages checked</strong><p>{safeMessages.length ? `${safeMessages.length} recent message${safeMessages.length === 1 ? " has" : "s have"} been checked and look safe.` : "New phone messages will be checked quietly for you."}</p></section></aside>;
}

function QuickActionPanel({ action, onClose, onChanged }: { action: QuickAction; onClose: () => void; onChanged: () => Promise<void> }) {
  const [medicines, setMedicines] = useState<Medication[]>([]);
  const [supply, setSupply] = useState<MedicationSupply[]>([]);
  const [household, setHousehold] = useState<HouseholdItem[]>([]);
  const [contacts, setContacts] = useState<PhoneBookContact[]>([]);
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [status, setStatus] = useState("");
  const [selectedSchedule, setSelectedSchedule] = useState("");
  const [doseNote, setDoseNote] = useState("");
  const [refillMedicine, setRefillMedicine] = useState("");
  const [refillQuantity, setRefillQuantity] = useState("");
  const [refillConfirmed, setRefillConfirmed] = useState(false);
  const [grocery, setGrocery] = useState("");
  const [groceryQuantity, setGroceryQuantity] = useState("");
  const [groceryConfirmed, setGroceryConfirmed] = useState(false);
  const [contact, setContact] = useState("");
  const [callConfirmed, setCallConfirmed] = useState(false);
  const [reminderTitle, setReminderTitle] = useState("");
  const [reminderAt, setReminderAt] = useState("");

  const load = async () => {
    try {
      if (action === "medicines") {
        const [plans, stock] = await Promise.all([api<Medication[]>("/health/medication-schedule"), api<MedicationSupply[]>("/guardian/medication-supply")]);
        setMedicines(plans); setSupply(stock);
      } else if (action === "groceries") setHousehold(await api<HouseholdItem[]>("/logistics/household-inventory"));
      else if (action === "family") setContacts((await api<PhoneBookContact[]>("/companion/phone-book")).filter(person => person.approved_for_calls));
      else setReminders(await api<Reminder[]>("/logistics/reminders"));
    } catch (error) { setStatus(error instanceof Error ? error.message : "Could not load this information."); }
  };
  useEffect(() => { void load(); }, [action]);
  const succeed = async (message: string) => { setStatus(message); await load(); await onChanged(); };
  const lowSupply = supply.filter(item => item.days_remaining <= 7);
  const title = { medicines: "My medicines", groceries: "Groceries", family: "Call family", reminders: "Reminders" }[action];
  const recordDose = async (event: FormEvent) => { event.preventDefault(); try { await api("/health/medication-taken", { method: "POST", body: JSON.stringify({ schedule_id: selectedSchedule, note: doseNote || null }) }); setSelectedSchedule(""); setDoseNote(""); await succeed("Your dose has been recorded. Thank you."); } catch (error) { setStatus(error instanceof Error ? error.message : "Could not record the dose."); } };
  const requestRefill = async (event: FormEvent) => { event.preventDefault(); try { await api("/guardian/replenishment-requests", { method: "POST", body: JSON.stringify({ medication_name: refillMedicine, quantity: Number(refillQuantity), user_confirmed: refillConfirmed }) }); setRefillMedicine(""); setRefillQuantity(""); setRefillConfirmed(false); await succeed("Your refill request has been recorded. No real order has been placed."); } catch (error) { setStatus(error instanceof Error ? error.message : "Could not record the refill request."); } };
  const requestGrocery = async (event: FormEvent) => { event.preventDefault(); try { await api("/logistics/purchase-requests", { method: "POST", body: JSON.stringify({ item_name: grocery, quantity: Number(groceryQuantity), user_confirmed: groceryConfirmed }) }); setGrocery(""); setGroceryQuantity(""); setGroceryConfirmed(false); await succeed("Your purchase request has been recorded. No real purchase has been made."); } catch (error) { setStatus(error instanceof Error ? error.message : "Could not record the purchase request."); } };
  const requestCall = async (event: FormEvent) => { event.preventDefault(); const person = contacts.find(item => item.id === contact); if (!person || !callConfirmed) { setStatus("Please choose a trusted contact and confirm first."); return; } try { const result = await api<{ display_name: string; relationship: string }>("/companion/call-requests", { method: "POST", body: JSON.stringify({ contact_query: person.display_name }) }); setContact(""); setCallConfirmed(false); await succeed(`Your message for ${result.display_name} has been recorded. I have asked your ${result.relationship} to call you.`); } catch (error) { setStatus(error instanceof Error ? error.message : "Could not record the call request."); } };
  const saveReminder = async (event: FormEvent) => { event.preventDefault(); try { await api("/logistics/reminders", { method: "POST", body: JSON.stringify({ title: reminderTitle, remind_at: new Date(reminderAt).toISOString() }) }); setReminderTitle(""); setReminderAt(""); await succeed("Your reminder has been saved."); } catch (error) { setStatus(error instanceof Error ? error.message : "Could not save the reminder."); } };

  return <div className="quick-action-backdrop" role="presentation"><section className="quick-action-dialog" role="dialog" aria-modal="true" aria-labelledby="quick-action-title"><header><div><p className="eyebrow">GUIDED ACTION</p><h2 id="quick-action-title">{title}</h2></div><button className="quick-close" onClick={onClose} aria-label="Close">×</button></header><p className="quick-intro">Review the details, then confirm before Kindred records anything.</p>
    {action === "medicines" && <><section className="quick-list"><h3>Your medicine supply</h3>{supply.length ? supply.map(item => <p key={item.medication_name} className={item.days_remaining <= 7 ? "quick-row urgent" : "quick-row"}><strong>{item.medication_name}</strong><span>{item.days_remaining} day{item.days_remaining === 1 ? "" : "s"} left{item.days_remaining <= 7 ? " · refill soon" : ""}</span></p>) : <p>No medicine supply has been recorded yet.</p>}</section><form className="quick-form" onSubmit={recordDose}><h3>Record a taken dose</h3><select value={selectedSchedule} onChange={event => setSelectedSchedule(event.target.value)} required><option value="">Choose a medicine</option>{medicines.map(item => <option key={item.id} value={item.id}>{item.medication_name} · {item.daily_times.join(", ")}</option>)}</select><input value={doseNote} onChange={event => setDoseNote(event.target.value)} placeholder="Optional note" /><button>Record dose</button></form><form className="quick-form" onSubmit={requestRefill}><h3>Request a refill</h3>{lowSupply.length ? <><select value={refillMedicine} onChange={event => setRefillMedicine(event.target.value)} required><option value="">Choose a medicine running low</option>{lowSupply.map(item => <option key={item.medication_name} value={item.medication_name}>{item.medication_name} · {item.days_remaining} days left</option>)}</select><input type="number" min="1" value={refillQuantity} onChange={event => setRefillQuantity(event.target.value)} placeholder="Quantity to request" required /><label><input type="checkbox" checked={refillConfirmed} onChange={event => setRefillConfirmed(event.target.checked)} /> I confirm this simulated refill request</label><button>Confirm refill request</button></> : <p>You have no medicines with seven days or fewer remaining.</p>}</form></>}
    {action === "groceries" && <><section className="quick-list"><h3>Household supplies</h3>{household.length ? household.map(item => <p key={item.id} className={item.reorder_needed ? "quick-row urgent" : "quick-row"}><strong>{item.item_name}</strong><span>{item.quantity_available} available{item.reorder_needed ? " · running low" : ""}</span></p>) : <p>No household supplies have been recorded yet.</p>}</section><form className="quick-form" onSubmit={requestGrocery}><h3>Request a purchase</h3><select value={grocery} onChange={event => setGrocery(event.target.value)} required><option value="">Choose an item</option>{household.map(item => <option key={item.id} value={item.item_name}>{item.item_name}{item.reorder_needed ? " · running low" : ""}</option>)}</select><input type="number" min="1" value={groceryQuantity} onChange={event => setGroceryQuantity(event.target.value)} placeholder="Quantity to request" required /><label><input type="checkbox" checked={groceryConfirmed} onChange={event => setGroceryConfirmed(event.target.checked)} /> I confirm this simulated purchase request</label><button>Confirm purchase request</button></form></>}
    {action === "family" && <><section className="quick-list"><h3>Trusted contacts</h3>{contacts.length ? contacts.map(item => <p key={item.id} className="quick-row"><strong>{item.display_name}</strong><span>{item.relationship}</span></p>) : <p>No trusted contacts are available yet.</p>}</section><form className="quick-form" onSubmit={requestCall}><h3>Ask someone to call</h3><select value={contact} onChange={event => setContact(event.target.value)} required><option value="">Choose a trusted contact</option>{contacts.map(item => <option key={item.id} value={item.id}>{item.display_name} · {item.relationship}</option>)}</select><label><input type="checkbox" checked={callConfirmed} onChange={event => setCallConfirmed(event.target.checked)} /> I confirm this simulated call request</label><button>Confirm call request</button></form></>}
    {action === "reminders" && <><section className="quick-list"><h3>Upcoming reminders</h3>{reminders.length ? reminders.map(item => <p key={item.id} className="quick-row"><strong>{item.title}</strong><span>{new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.remind_at))}</span></p>) : <p>You have no scheduled reminders.</p>}</section><form className="quick-form" onSubmit={saveReminder}><h3>Add a reminder</h3><input value={reminderTitle} onChange={event => setReminderTitle(event.target.value)} placeholder="What should I remind you about?" required /><input type="datetime-local" value={reminderAt} onChange={event => setReminderAt(event.target.value)} required /><button>Save reminder</button></form></>}
    {status && <p className="quick-status" role="status">{status}</p>}<footer><button className="quiet-button" onClick={onClose}>Back to Care Hub</button></footer></section></div>;
}

function Login({ onLogin, onAdmin }: { onLogin: () => void; onAdmin: () => void }) {
  const [showPassword, setShowPassword] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const attemptLogin = (complete: () => void) => {
    if (username.trim().toLowerCase() !== DEMO_USERNAME || password !== DEMO_PASSWORD) {
      setError("Please use the demo credentials shown below.");
      return;
    }
    complete();
  };
  return <main className="login-page"><form className="login-card" onSubmit={event => { event.preventDefault(); attemptLogin(onLogin); }}><p className="login-mark">K</p><p className="eyebrow">KINDRED CARE COMPANION</p><h1>Welcome home</h1><p className="login-subtitle">A calm, caring companion for every day.</p><label htmlFor="login-id">User name</label><input id="login-id" value={username} onChange={event => setUsername(event.target.value)} autoComplete="username" placeholder="anita" required /><label htmlFor="login-password">Password</label><div className="password-row"><input id="login-password" value={password} onChange={event => setPassword(event.target.value)} type={showPassword ? "text" : "password"} autoComplete="current-password" placeholder="Enter password" required /><button type="button" onClick={() => setShowPassword(value => !value)}>{showPassword ? "Hide" : "Reveal"}</button></div><button className="login-button">Enter Kindred</button>{error && <p className="login-error" role="alert">{error}</p>}<p className="login-help">Demo login: <strong>anita</strong> / <strong>kindred-demo</strong></p><button className="admin-login" type="button" onClick={() => attemptLogin(onAdmin)}>Open Family Admin</button></form></main>;
}

function Admin({ onBack, onLogout }: { onBack: () => void; onLogout: () => void }) {
  const [status, setStatus] = useState("Ready to update Anita's care records.");
  const [message, setMessage] = useState("Urgent: your bank account is blocked. Send the verification code now.");
  const [memory, setMemory] = useState("Anita enjoys morning tea in the garden.");
  const [reminder, setReminder] = useState("Buy tea leaves");
  const [availableSchedules, setAvailableSchedules] = useState<Medication[]>([]);
  const [familyContacts, setFamilyContacts] = useState<PhoneBookContact[]>([]);
  const [doseScheduleId, setDoseScheduleId] = useState("");
  const [doseNote, setDoseNote] = useState("");
  const [messageContactId, setMessageContactId] = useState("");
  const [familyMessage, setFamilyMessage] = useState("");
  const [messageApproved, setMessageApproved] = useState(false);
  const [householdItem, setHouseholdItem] = useState("");
  const [householdQuantity, setHouseholdQuantity] = useState("1");
  const [purchaseApproved, setPurchaseApproved] = useState(false);
  const [medicationName, setMedicationName] = useState("");
  const [doseInstructions, setDoseInstructions] = useState("");
  const [dailyTimes, setDailyTimes] = useState("08:00");
  const [stockScheduleId, setStockScheduleId] = useState("");
  const [stockMedicationName, setStockMedicationName] = useState("");
  const [stockUnits, setStockUnits] = useState("30");
  const [stockPurchaseDate, setStockPurchaseDate] = useState("2026-07-20");
  const [contactName, setContactName] = useState("");
  const [contactRelationship, setContactRelationship] = useState("");
  const [contactPhoneNumber, setContactPhoneNumber] = useState("");
  const [contactApproved, setContactApproved] = useState(true);
  useEffect(() => {
    void Promise.all([
      api<Medication[]>("/health/medication-schedule"),
      api<PhoneBookContact[]>("/companion/phone-book"),
    ]).then(([schedules, contacts]) => {
      setAvailableSchedules(schedules);
      setFamilyContacts(contacts);
    }).catch(() => undefined);
  }, []);
  const submit = (path: string, body: object, clearInput?: () => void) => async (event: FormEvent) => {
    event.preventDefault();
    try {
      await api(path, { method: "POST", body: JSON.stringify(body) });
      clearInput?.();
      setStatus("✓ Record saved successfully. You can add another record or return to Anita's Care Hub.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not insert the record. Your entered value has been kept so you can try again.");
    }
  };
  const createMedicationPlan = async (event: FormEvent) => {
    event.preventDefault();
    const times = dailyTimes.split(",").map(value => value.trim()).filter(Boolean);
    try {
      const schedule = await api<Medication>("/health/medication-schedule", {
        method: "POST",
        body: JSON.stringify({ medication_name: medicationName, dose_instructions: doseInstructions, daily_times: times, timezone: "Europe/Oslo" }),
      });
      setMedicationName(""); setDoseInstructions(""); setDailyTimes("08:00");
      setAvailableSchedules(items => [...items, schedule]);
      setStatus(`✓ Medication plan inserted successfully. Schedule ID: ${schedule.id}. Add stock through Inventory setup next.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not insert the medication plan. Your entered values have been kept so you can try again.");
    }
  };
  const saveMedicationStock = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const stock = await api<MedicationStock>("/inventory/medication-stock", {
        method: "POST",
        body: JSON.stringify({ schedule_id: stockScheduleId, medication_name: stockMedicationName, units_available: Number(stockUnits), last_purchased_on: stockPurchaseDate }),
      });
      setStockScheduleId(""); setStockMedicationName(""); setStockUnits("30");
      setStatus(`✓ Medication stock inserted successfully. ${stock.medication_name}: ${stock.units_available} units linked to its plan.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not insert medication stock. Your entered values have been kept so you can try again.");
    }
  };
  const addPhoneBookContact = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const saved = await api<PhoneBookContact>("/companion/phone-book", {
        method: "POST",
        body: JSON.stringify({ display_name: contactName, relationship: contactRelationship, phone_number: contactPhoneNumber, approved_for_calls: contactApproved }),
      });
      setContactName(""); setContactRelationship(""); setContactPhoneNumber(""); setContactApproved(true);
      setFamilyContacts(items => [...items, saved]);
      setStatus(`✓ Family contact inserted successfully. ${saved.display_name} is available for simulated communication.`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not insert the family contact. Your entered values have been kept so you can try again.");
    }
  };
  const saveTakenDose = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await api("/health/medication-taken", { method: "POST", body: JSON.stringify({ schedule_id: doseScheduleId, note: doseNote || null }) });
      setDoseScheduleId(""); setDoseNote("");
      setStatus("✓ Taken dose recorded successfully.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Could not record the taken dose."); }
  };
  const saveFamilyMessage = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await api("/companion/family-messages", { method: "POST", body: JSON.stringify({ contact_id: messageContactId, content: familyMessage, user_approved: messageApproved }) });
      setMessageContactId(""); setFamilyMessage(""); setMessageApproved(false);
      setStatus("✓ Family message recorded successfully.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Could not record the family message."); }
  };
  const saveHouseholdPurchase = async (event: FormEvent) => {
    event.preventDefault();
    try {
      await api("/logistics/purchase-requests", { method: "POST", body: JSON.stringify({ item_name: householdItem, quantity: Number(householdQuantity), user_confirmed: purchaseApproved }) });
      setHouseholdItem(""); setHouseholdQuantity("1"); setPurchaseApproved(false);
      setStatus("✓ Household purchase request recorded successfully.");
    } catch (error) { setStatus(error instanceof Error ? error.message : "Could not record the household purchase request."); }
  };
  return <main className="admin-page"><header className="admin-header"><div><p className="eyebrow">FAMILY ADMIN</p><h1>Anita's care records</h1><p>Manage trusted contacts, medicine plans, supplies, reminders, and other local care records for Anita.</p></div><div className="header-actions"><button className="quiet-button" onClick={onBack}>Back to Anita's Care Hub</button><button className="quiet-button" onClick={onLogout}>Log out</button></div></header><p className="admin-status">{status}</p><section className="admin-grid">
    <form className="admin-card medication-setup" onSubmit={createMedicationPlan}><h2>Prescription details</h2><p>Record medicine details provided by Anita's doctor or pharmacist. Add one or more daily times, separated by commas.</p><input value={medicationName} onChange={event => setMedicationName(event.target.value)} required placeholder="Medicine name, e.g. Metformin" /><input value={doseInstructions} onChange={event => setDoseInstructions(event.target.value)} required placeholder="Dose/instructions, e.g. 500 mg with food" /><input value={dailyTimes} onChange={event => setDailyTimes(event.target.value)} required placeholder="Daily times, e.g. 08:00, 20:00" /><button>Save medicine plan</button></form>
    <form className="admin-card medication-setup" onSubmit={saveMedicationStock}><h2>Medicine supply</h2><p>Use the medicine plan ID returned above, then add the tablets or capsules currently available.</p><input value={stockScheduleId} onChange={event => setStockScheduleId(event.target.value)} required placeholder="Medicine plan ID" /><input value={stockMedicationName} onChange={event => setStockMedicationName(event.target.value)} required placeholder="Medicine name, e.g. Metformin" /><input type="number" min="0" value={stockUnits} onChange={event => setStockUnits(event.target.value)} required placeholder="Tablets or capsules available" /><input type="date" value={stockPurchaseDate} onChange={event => setStockPurchaseDate(event.target.value)} required /><button>Save medicine supply</button></form>
    <form className="admin-card" onSubmit={addPhoneBookContact}><h2>Trusted contacts</h2><p>Add a family member or trusted person for simulated calls and approved family messages.</p><input value={contactName} onChange={event => setContactName(event.target.value)} required placeholder="Name of the person" /><input value={contactRelationship} onChange={event => setContactRelationship(event.target.value)} required placeholder="Relationship, e.g. son" /><input type="tel" value={contactPhoneNumber} onChange={event => setContactPhoneNumber(event.target.value)} required placeholder="Phone number, e.g. +4790000000" /><label><input type="checkbox" checked={contactApproved} onChange={event => setContactApproved(event.target.checked)} /> Approved for simulated calls</label><button>Save trusted contact</button></form>
    <form className="admin-card safety" onSubmit={submit("/security/phone-messages", { message }, () => setMessage(""))}><h2>Review a phone message</h2><p>Add a simulated incoming SMS for Guardian to review and classify.</p><textarea value={message} onChange={event => setMessage(event.target.value)} required placeholder="Type an incoming phone message" /><button>Save phone message</button></form>
    <form className="admin-card" onSubmit={submit("/memory/memories", { content: memory, category: "preference", source: "family-admin", importance: 3 }, () => setMemory(""))}><h2>Personal details</h2><p>Add an approved personal preference or fact for Companion to remember.</p><textarea value={memory} onChange={event => setMemory(event.target.value)} required placeholder="Type a personal detail or preference" /><button>Save personal detail</button></form>
    <form className="admin-card" onSubmit={submit("/logistics/reminders", { title: reminder, remind_at: "2026-07-26T09:00:00+02:00" }, () => setReminder(""))}><h2>Household reminder</h2><p>Create a local reminder for a household task.</p><input value={reminder} onChange={event => setReminder(event.target.value)} required placeholder="Reminder title" /><button>Save reminder</button></form>
    <form className="admin-card" onSubmit={saveTakenDose}><h2>Record a taken dose</h2><p>Select the medicine plan and optionally add a note. The current time is recorded automatically.</p><select value={doseScheduleId} onChange={event => setDoseScheduleId(event.target.value)} required><option value="">Choose a medicine plan</option>{availableSchedules.map(schedule => <option key={schedule.id} value={schedule.id}>{schedule.medication_name} · {schedule.daily_times.join(", ")}</option>)}</select><input value={doseNote} onChange={event => setDoseNote(event.target.value)} placeholder="Optional note, e.g. taken after breakfast" /><button>Save taken dose</button></form>
    <form className="admin-card" onSubmit={saveFamilyMessage}><h2>Family message</h2><p>Choose a trusted contact, write the message, and explicitly approve it before recording.</p><select value={messageContactId} onChange={event => setMessageContactId(event.target.value)} required><option value="">Choose a trusted contact</option>{familyContacts.map(person => <option key={person.id} value={person.id}>{person.display_name} ({person.relationship})</option>)}</select><textarea value={familyMessage} onChange={event => setFamilyMessage(event.target.value)} required placeholder="Write the message for the family member" /><label><input type="checkbox" checked={messageApproved} onChange={event => setMessageApproved(event.target.checked)} /> I approve this simulated message</label><button>Record family message</button></form>
    <form className="admin-card" onSubmit={saveHouseholdPurchase}><h2>Household purchase</h2><p>Enter the item and quantity, then explicitly confirm the local purchase request.</p><input value={householdItem} onChange={event => setHouseholdItem(event.target.value)} required placeholder="Item name, e.g. Jasmine tea" /><input type="number" min="1" value={householdQuantity} onChange={event => setHouseholdQuantity(event.target.value)} required placeholder="Quantity" /><label><input type="checkbox" checked={purchaseApproved} onChange={event => setPurchaseApproved(event.target.checked)} /> I confirm this simulated purchase request</label><button>Record purchase request</button></form>
  </section><section className="admin-boundary"><strong>Family Admin note:</strong> all calls, messages, purchases, and reminders are recorded locally for this prototype. No external action is taken.</section></main>;
}

function Caregiver({ medicationSupply, phoneMessages, refresh }: { medicationSupply: MedicationSupply[]; phoneMessages: PhoneMessage[]; refresh: () => Promise<void> }) {
  // A previous prototype failure can leave a pending copy beside a completed copy.
  // For the caregiver, show the completed analysis for identical SMS text.
  const displayedMessages = Array.from(phoneMessages.reduce((unique, message) => {
    const key = message.message.trim().toLocaleLowerCase();
    const existing = unique.get(key);
    if (!existing || (existing.analysis_status !== "completed" && message.analysis_status === "completed")) unique.set(key, message);
    return unique;
  }, new Map<string, PhoneMessage>()).values());
  const suspiciousMessages = displayedMessages.filter(item => item.risk_level && item.risk_level !== "low");
  const messageLabel = (message: PhoneMessage) => message.analysis_status === "failed" ? "Needs review" : message.analysis_status !== "completed" ? "Still being reviewed" : message.risk_level === "low" ? "Looks safe" : `${message.risk_level} risk`;
  const lowSupply = medicationSupply.filter(item => item.days_remaining <= 7).sort((left, right) => left.days_remaining - right.days_remaining);
  return <section className="caregiver-view"><div className="caregiver-heading"><div><p className="eyebrow">CAREGIVER VIEW</p><h2>Care with context, not alarm</h2><p>Review only the items that need attention.</p></div><button className="quiet-button" onClick={() => void refresh()}>Refresh data</button></div><div className="caregiver-grid"><section className="info-card caregiver-medicines"><h3>Medicines needing attention</h3>{lowSupply.length ? lowSupply.map(item => <p className="quick-row urgent" key={item.medication_name}><strong>{item.medication_name}</strong><span>{item.days_remaining} day{item.days_remaining === 1 ? "" : "s"} left · refill soon</span></p>) : <p>All recorded medicine supplies are above seven days.</p>}</section><section className="info-card caregiver-inbox"><h3>Phone message review</h3><p className="inbox-summary">{displayedMessages.length} unique messages reviewed · {suspiciousMessages.length} need attention</p>{displayedMessages.length ? displayedMessages.slice(0, 8).map(item => <article className={`caregiver-message ${item.risk_level && item.risk_level !== "low" ? "suspicious" : ""}`} key={item.id}><div><strong className={`risk ${item.risk_level ?? "pending"}`}>{messageLabel(item)}</strong><time>{new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.received_at))}</time></div><p>{item.message}</p>{item.explanation && <small>{item.explanation}</small>}</article>) : <p>No incoming messages have been reviewed yet.</p>}</section></div></section>;
}
