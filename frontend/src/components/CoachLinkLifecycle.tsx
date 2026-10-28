"use client";
import { useState } from "react";
import { api, CoachLink } from "@/lib/api";

export function CoachLinkLifecycle({ links, athlete, onSaved }: { links: CoachLink[]; athlete: boolean; onSaved: () => Promise<void> }) {
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  async function transition(id: number, status: string) {
    setBusy(true); setMessage("");
    try { await api(`coach-links/${id}/status/`, { method: "POST", body: JSON.stringify({ status, reason }) }); await onSaved(); setMessage("Статус связи обновлён"); }
    catch (cause) { setMessage(cause instanceof Error ? cause.message : "Не удалось изменить связь"); }
    finally { setBusy(false); }
  }
  return <section className="blk"><h2><b>03</b><span>Управление связями</span></h2><div className="workflow-stack"><label className="lb">Причина изменения статуса<input className="inp" maxLength={500} value={reason} onChange={(event) => setReason(event.target.value)} /></label>{message && <p role="status">{message}</p>}{links.filter((item) => ["confirmed", "suspended"].includes(item.status)).map((item) => <div key={item.id} className="workflow-record"><p>{athlete ? item.coach_name : item.athlete_name} · Связь #{item.id} · {item.status === "suspended" ? "Приостановлена" : "Активна"}</p><div className="cta">{item.status === "confirmed" && <button className="btn" disabled={busy || !reason.trim()} onClick={() => void transition(item.id, "suspended")}>Приостановить</button>}{item.status === "suspended" && athlete && <button className="btn" disabled={busy || !reason.trim()} onClick={() => void transition(item.id, "confirmed")}>Возобновить</button>}<button className="btn" disabled={busy || !reason.trim()} onClick={() => void transition(item.id, "ended")}>Завершить</button>{!athlete && item.status === "confirmed" && <a className="btn" href={`/api/v1/reports/athlete-participation/?athlete=${item.athlete}`}>Отчёт выступлений · XLSX</a>}</div></div>)}</div></section>;
}
