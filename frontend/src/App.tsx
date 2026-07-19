import { FormEvent, useEffect, useMemo, useState } from "react";
import "./voice.css";

type ChatMessage = { role: "user" | "assistant"; content: string };
type Medication = { id: string; medication_name: string; dose_instructions: string; daily_times: string[] };
type Alert = { id: string; risk_level: string; details: string | null };
type SpeechRecognitionResultLike = { isFinal: boolean; 0: { transcript: string } };
type SpeechRecognitionLike = {
  lang: string; interimResults: boolean; maxAlternatives: number;
  start: () => void;
  onstart: (() => void) | null;
  onresult: ((event: { results: ArrayLike<SpeechRecognitionResultLike> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
};
type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

const API = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
const sessionId = crypto.randomUUID();

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail ?? "Kindred could not complete that request.");
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>;
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
  const [signedIn, setSignedIn] = useState(false);
  const [screen, setScreen] = useState<"hub" | "admin">("hub");
  const [role, setRole] = useState<"elder" | "caregiver">("elder");
  const [language, setLanguage] = useState<"en" | "bn">("en");
  const [messages, setMessages] = useState<ChatMessage[]>([{ role: "assistant", content: "Good morning, Anita. I am here whenever you need me." }]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState("");
  const [voiceStatus, setVoiceStatus] = useState<"idle" | "listening" | "sending">("idle");
  const [medications, setMedications] = useState<Medication[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const text = copy[language];
  const date = useMemo(() => new Intl.DateTimeFormat(language === "bn" ? "bn-BD" : "en-GB", { weekday: "long", day: "numeric", month: "long" }).format(new Date()), [language]);

  const refresh = async () => {
    try {
      const [schedule, security] = await Promise.all([api<Medication[]>("/health/medication-schedule"), api<Alert[]>("/security/events")]);
      setMedications(schedule); setAlerts(security);
    } catch { setNotice("The dashboard will refresh when the Kindred backend is running."); }
  };
  useEffect(() => { void refresh(); }, []);

  const sendMessage = async (rawMessage: string, speakReply = false) => {
    const message = rawMessage.trim(); if (!message || loading) return;
    setMessages(items => [...items, { role: "user", content: message }]); setDraft(""); setLoading(true); setNotice("");
    try {
      const result = await api<{ reply: string }>(`/master/conversations/${sessionId}/turns`, { method: "POST", body: JSON.stringify({ message }) });
      setMessages(items => [...items, { role: "assistant", content: result.reply }]); await refresh();
      if (speakReply && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(result.reply);
        utterance.lang = language === "bn" ? "bn-BD" : "en-GB";
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
    recognition.lang = language === "bn" ? "bn-BD" : "en-GB";
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => { setVoiceStatus("listening"); setNotice("Listening… speak naturally, then pause when you are finished."); };
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results).map(result => result[0].transcript).join(" ").trim();
      setDraft(transcript);
      if (event.results[event.results.length - 1]?.isFinal) finalTranscript = transcript;
    };
    recognition.onerror = (event) => {
      setVoiceStatus("idle");
      if (event.error !== "aborted") setNotice(`Voice input could not start: ${event.error}. Check your microphone permission and try again.`);
    };
    recognition.onend = () => {
      if (finalTranscript) { setVoiceStatus("sending"); void sendMessage(finalTranscript, true); }
      else setVoiceStatus("idle");
    };
    recognition.start();
  };

  if (!signedIn) return <Login onLogin={() => setSignedIn(true)} onAdmin={() => { setSignedIn(true); setScreen("admin"); }} />;
  if (screen === "admin") return <Admin onBack={() => setScreen("hub")} />;

  const quickActions = [
    ["💊", "My medicines", "Show my medication supply"], ["🛒", "Groceries", "Do I need to buy Jasmine tea?"],
    ["👪", "Call family", "Tell my son to call me"], ["⏰", "Reminders", "Remind me to buy tea leaves"],
  ];
  return <main className="kindred-shell">
    <header className="kindred-header">
      <div><p className="eyebrow">KINDRED CARE COMPANION</p><h1>{text.greeting("Anita")}</h1><p className="date-label">{date}</p></div>
      <div className="header-actions">
        <div className="language-toggle" aria-label="Language"><button className={language === "en" ? "active" : ""} onClick={() => setLanguage("en")}>EN</button><button className={language === "bn" ? "active" : ""} onClick={() => setLanguage("bn")}>বাংলা</button></div>
        <div className="role-toggle"><button className={role === "elder" ? "active" : ""} onClick={() => setRole("elder")}>Elder</button><button className={role === "caregiver" ? "active" : ""} onClick={() => setRole("caregiver")}>Caregiver</button></div>
        <button className="quiet-button" onClick={() => setScreen("admin")}>Developer view</button>
      </div>
    </header>
    <section className="thought-card"><span>✦</span><p><strong>Thought of the day</strong>{text.thought}</p></section>
    {role === "caregiver" ? <Caregiver medications={medications} alerts={alerts} refresh={refresh} /> : <section className="hub-grid">
      <aside className="quick-panel" aria-label="Quick actions"><h2>{text.quick}</h2>{quickActions.map(([icon, label, prompt]) => <button key={label} onClick={() => setDraft(prompt)}><span aria-hidden>{icon}</span><strong>{label}</strong><small>Tap for help</small></button>)}</aside>
      <section className="voice-canvas">
        <div className="agent-status"><span className={loading || voiceStatus !== "idle" ? "status-dot busy" : "status-dot"} />{voiceStatus === "listening" ? "Listening…" : voiceStatus === "sending" || loading ? text.thinking : "Kindred is ready"}</div>
        <button className={`voice-orb ${voiceStatus === "listening" ? "listening" : ""}`} onClick={startVoiceConversation} aria-label={text.listen} aria-pressed={voiceStatus === "listening"}><span>✦</span><strong>{voiceStatus === "listening" ? "Listening…" : text.listen}</strong><small>{voiceStatus === "listening" ? "Pause when you are finished" : text.chat}</small></button>
        <p className="voice-help">Tap to speak. Kindred turns your words into a message, sends it to the Master Agent, and reads the reply aloud. Calls, messages, and orders remain safely simulated.</p>
      </section>
      <aside className="day-panel"><h2>{text.today}</h2><div className="agenda-item"><span className="agenda-time">09:00</span><p><strong>Morning check-in</strong><br />Kindred is here to help plan your day.</p></div><div className="agenda-item"><span className="agenda-time">16:00</span><p><strong>Family time</strong><br />A gentle reminder to call Sara.</p></div><section className="safety-note"><strong>Safety first</strong><p>Kindred will flag suspicious phone messages quietly for review.</p></section></aside>
    </section>}
    <section className="lower-grid">
      <section className="info-card"><div className="section-title"><h2>Medication today</h2><button onClick={() => setDraft("Show my medication schedule")}>Ask Kindred</button></div>{medications.length ? medications.map(item => <p className="medicine" key={item.id}><span>✓</span><strong>{item.medication_name}</strong><small>{item.dose_instructions} · {item.daily_times.join(", ")}</small></p>) : <p>Medication information appears here when the backend is running.</p>}</section>
      <section className="chat-card"><div className="section-title"><h2>{text.chat}</h2><button onClick={() => setMessages([{ role: "assistant", content: "Conversation cleared. How can I help?" }])}>Clear</button></div><div className="chat" aria-live="polite">{messages.slice(-4).map((message, index) => <p className={`bubble ${message.role}`} key={index}>{message.content}</p>)}{loading && <p className="bubble assistant">{text.thinking}…</p>}</div><form onSubmit={send}><label htmlFor="message">Type your message</label><div className="composer"><input id="message" value={draft} onChange={event => setDraft(event.target.value)} placeholder="For example: Tell my son to call me" /><button>Send</button></div></form></section>
    </section>
    {notice && <p className="notice" role="status">{notice}</p>}
    <p className="prototype-footer">Prototype mode · no real calls, messages, purchases, or health decisions are made.</p>
  </main>;
}

function Login({ onLogin, onAdmin }: { onLogin: () => void; onAdmin: () => void }) {
  const [showPassword, setShowPassword] = useState(false);
  return <main className="login-page"><form className="login-card" onSubmit={event => { event.preventDefault(); onLogin(); }}><p className="login-mark">K</p><p className="eyebrow">KINDRED CARE COMPANION</p><h1>Welcome home</h1><p className="login-subtitle">A calm, caring companion for every day.</p><label htmlFor="login-id">User name or email</label><input id="login-id" autoComplete="username" placeholder="Anita or your email" required /><label htmlFor="login-password">Password</label><div className="password-row"><input id="login-password" type={showPassword ? "text" : "password"} autoComplete="current-password" placeholder="Enter password" required /><button type="button" onClick={() => setShowPassword(value => !value)}>{showPassword ? "Hide" : "Reveal"}</button></div><button className="login-button">Enter Kindred</button><p className="login-help">Demo sign-in: enter any details to continue.</p><button className="admin-login" type="button" onClick={onAdmin}>Open developer sandbox</button></form></main>;
}

function Admin({ onBack }: { onBack: () => void }) {
  const [status, setStatus] = useState("Ready to create simulated test records.");
  const [message, setMessage] = useState("Urgent: your bank account is blocked. Send the verification code now.");
  const [memory, setMemory] = useState("Anita enjoys morning tea in the garden.");
  const [reminder, setReminder] = useState("Buy tea leaves");
  const [contact, setContact] = useState("son");
  const submit = (path: string, body: object, clearInput?: () => void) => async (event: FormEvent) => {
    event.preventDefault();
    try {
      await api(path, { method: "POST", body: JSON.stringify(body) });
      clearInput?.();
      setStatus("✓ Record inserted successfully. You can add another record or return to the Care Hub to test it.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Could not insert the record. Your entered value has been kept so you can try again.");
    }
  };
  return <main className="admin-page"><header className="admin-header"><div><p className="eyebrow">DEVELOPER & JUDGE SANDBOX</p><h1>Live prototype testing</h1><p>Create simulated records through the real FastAPI endpoints. Every action is visible to the running prototype.</p></div><button className="quiet-button" onClick={onBack}>Back to Kindred</button></header><p className="admin-status">{status}</p><section className="admin-grid">
    <form className="admin-card safety" onSubmit={submit("/security/phone-messages", { message }, () => setMessage(""))}><h2>Simulate a phone message</h2><p>Guardian stores and classifies this as a simulated incoming SMS.</p><textarea value={message} onChange={event => setMessage(event.target.value)} required placeholder="Type a simulated phone message" /><button>Insert phone message</button></form>
    <form className="admin-card" onSubmit={submit("/memory/memories", { content: memory, category: "preference", source: "judge-admin", importance: 3 }, () => setMemory(""))}><h2>Save a memory</h2><p>Add an approved personal fact for Companion retrieval.</p><textarea value={memory} onChange={event => setMemory(event.target.value)} required placeholder="Type a personal memory or preference" /><button>Insert personal record</button></form>
    <form className="admin-card" onSubmit={submit("/logistics/reminders", { title: reminder, remind_at: "2026-07-26T09:00:00+02:00" }, () => setReminder(""))}><h2>Add a reminder</h2><p>Creates a simulated household reminder.</p><input value={reminder} onChange={event => setReminder(event.target.value)} required placeholder="Reminder title" /><button>Insert reminder</button></form>
    <form className="admin-card" onSubmit={submit("/health/medication-taken", { schedule_id: "demo-schedule-metformin", note: "Recorded from developer sandbox" })}><h2>Verify medication</h2><p>Records the seeded Metformin dose as taken.</p><button>Insert medication record</button></form>
    <form className="admin-card" onSubmit={submit("/companion/family-messages", { contact_id: contact, content: "Please call me when you can.", user_approved: true }, () => setContact("son"))}><h2>Queue a family message</h2><p>Queues a safe, simulated approved message.</p><select value={contact} onChange={event => setContact(event.target.value)}><option value="son">Rahim (son)</option><option value="daughter">Sara (daughter)</option></select><button>Insert family message</button></form>
    <form className="admin-card" onSubmit={submit("/logistics/purchase-requests", { item_name: "Jasmine tea", quantity: 2, user_confirmed: true })}><h2>Request household item</h2><p>Creates a confirmed simulated purchase request.</p><button>Insert purchase request</button></form>
  </section><section className="admin-boundary"><strong>Planned next:</strong> record update/delete and bulk-upload controls require dedicated, audited backend endpoints. They are intentionally not simulated in the browser.</section></main>;
}

function Caregiver({ medications, alerts, refresh }: { medications: Medication[]; alerts: Alert[]; refresh: () => Promise<void> }) {
  return <section className="caregiver-view"><div className="caregiver-heading"><div><p className="eyebrow">CAREGIVER VIEW</p><h2>Care with context, not alarm</h2><p>Review simulated data shared by Anita's Kindred prototype.</p></div><button className="quiet-button" onClick={() => void refresh()}>Refresh data</button></div><div className="caregiver-grid"><section className="info-card"><h3>Medication schedules</h3>{medications.length ? medications.map(item => <p className="medicine" key={item.id}><span>✓</span><strong>{item.medication_name}</strong><small>{item.daily_times.join(", ")}</small></p>) : <p>No data loaded.</p>}</section><section className="info-card"><h3>Security review</h3>{alerts.length ? alerts.slice(0, 4).map(item => <p key={item.id} className="alert-line"><strong className={`risk ${item.risk_level}`}>{item.risk_level}</strong>{item.details ?? "Security event"}</p>) : <p>No stored security alerts.</p>}</section><section className="info-card"><h3>Caregiver protocol</h3><p>Prototype workflows can queue approved family messages. Real escalation, intervention, and clinical decisions are not enabled.</p></section></div></section>;
}
