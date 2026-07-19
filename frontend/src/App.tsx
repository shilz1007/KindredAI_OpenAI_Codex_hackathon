import { FormEvent, useEffect, useMemo, useState } from "react";

type ChatMessage = { role: "user" | "assistant"; content: string };
type Medication = { id: string; medication_name: string; dose_instructions: string; daily_times: string[] };
type Alert = { id: string; risk_level: string; details: string | null };

const API = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
const sessionId = crypto.randomUUID();

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) throw new Error((await response.json().catch(() => null))?.detail ?? "Kindred could not complete that request.");
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>;
}

export function App() {
  const [role, setRole] = useState<"elder" | "caregiver">("elder");
  const [messages, setMessages] = useState<ChatMessage[]>([{ role: "assistant", content: "Good morning, Anita. How can I help today?" }]);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [medications, setMedications] = useState<Medication[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);

  const todayLabel = useMemo(() => new Intl.DateTimeFormat("en-GB", { weekday: "long", day: "numeric", month: "long" }).format(new Date()), []);
  const refreshDashboard = async () => {
    try {
      const [schedule, securityAlerts] = await Promise.all([api<Medication[]>("/health/medication-schedule"), api<Alert[]>("/security/events")]);
      setMedications(schedule); setAlerts(securityAlerts);
    } catch { /* The chat remains usable even if a dashboard card cannot refresh. */ }
  };
  useEffect(() => { void refreshDashboard(); }, []);

  const sendMessage = async (event: FormEvent) => {
    event.preventDefault(); const message = draft.trim(); if (!message || loading) return;
    setMessages(current => [...current, { role: "user", content: message }]); setDraft(""); setError(""); setLoading(true);
    try {
      const result = await api<{ reply: string }>(`/master/conversations/${sessionId}/turns`, { method: "POST", body: JSON.stringify({ message }) });
      setMessages(current => [...current, { role: "assistant", content: result.reply }]); await refreshDashboard();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to reach Kindred."); }
    finally { setLoading(false); }
  };
  const clearConversation = async () => { await api<void>(`/master/conversations/${sessionId}`, { method: "DELETE" }); setMessages([{ role: "assistant", content: "Conversation cleared. How can I help?" }]); };

  return <main className="app-shell">
    <header><div><p className="eyebrow">KINDRED CARE COMPANION</p><h1>Good morning, Anita</h1><p>{todayLabel}</p></div><div className="role-switch" aria-label="Demo role"><button className={role === "elder" ? "active" : ""} onClick={() => setRole("elder")}>Elder view</button><button className={role === "caregiver" ? "active" : ""} onClick={() => setRole("caregiver")}>Caregiver view</button></div></header>
    <p className="demo-banner">Demo mode — messages, calls, reminders, and orders are simulated. No real action is taken.</p>
    {role === "elder" ? <section className="elder-layout">
      <section className="conversation card"><div className="card-title"><h2>Talk with Kindred</h2><button className="text-button" onClick={() => void clearConversation()}>Clear</button></div><div className="chat" aria-live="polite">{messages.map((message, index) => <p className={`bubble ${message.role}`} key={index}>{message.content}</p>)}{loading && <p className="bubble assistant">Kindred is thinking…</p>}</div><form onSubmit={sendMessage}><label htmlFor="message">Type your message</label><div className="composer"><input id="message" value={draft} onChange={event => setDraft(event.target.value)} placeholder="For example: Tell my son to call me" /><button type="submit">Send</button></div></form><button className="voice-button" disabled title="WebRTC voice is the next integration step">🎙 Start voice conversation <span>Coming next</span></button>{error && <p className="error">{error}</p>}</section>
      <aside className="status-column"><section className="card"><h2>Today</h2><p>Ask Kindred to add a reminder, check your plans, or contact family.</p><div className="quick-actions"><button onClick={() => setDraft("Show my medication supply")}>My medicines</button><button onClick={() => setDraft("Tell my son to call me")}>Call family</button><button onClick={() => setDraft("Remind me to buy tea leaves")}>Remind me</button><button onClick={() => setDraft("Do I need to buy Jasmine tea?")}>Household supplies</button></div></section><section className="card"><h2>Medication</h2>{medications.map(medication => <p key={medication.id}><strong>{medication.medication_name}</strong><br />{medication.dose_instructions} · {medication.daily_times.join(", ")}</p>)}</section></aside>
    </section> : <Caregiver medications={medications} alerts={alerts} refresh={refreshDashboard} />}
  </main>;
}

function Caregiver({ medications, alerts, refresh }: { medications: Medication[]; alerts: Alert[]; refresh: () => Promise<void> }) {
  return <section className="caregiver"><div className="card-title"><div><h2>Caregiver dashboard</h2><p>Shared demo data only.</p></div><button onClick={() => void refresh()}>Refresh</button></div><div className="dashboard-grid"><section className="card"><h3>Medication schedules</h3>{medications.map(medication => <p key={medication.id}><strong>{medication.medication_name}</strong><br />{medication.daily_times.join(", ")}</p>)}</section><section className="card"><h3>Security events</h3>{alerts.length ? alerts.map(alert => <p key={alert.id}><strong className={`risk ${alert.risk_level}`}>{alert.risk_level}</strong> {alert.details ?? "Security event"}</p>) : <p>No security events.</p>}</section><section className="card"><h3>Management</h3><p>Use the current API-backed panels for phone book, reminders, household inventory, and simulated communications.</p><p className="muted">Detailed management forms are the next UI increment.</p></section></div></section>;
}
