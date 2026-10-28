"use client";

import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";

type Kind = { id: number; name: string; is_active: boolean };
type Deadline = { id: number; title: string; due_on: string };

export function FederationOperations() {
  const [types, setTypes] = useState<Kind[]>([]);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [name, setName] = useState("");
  const [title, setTitle] = useState("");
  const [due, setDue] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const abort = new AbortController();
    void Promise.all([api<Kind[]>("competition-types/", { signal: abort.signal }), api<Deadline[]>("report-deadlines/", { signal: abort.signal })]).then(([kinds, dates]) => { if (!abort.signal.aborted) { setTypes(kinds); setDeadlines(dates); } }).catch(() => { if (!abort.signal.aborted) setMessage("Не удалось загрузить справочники и сроки"); });
    return () => abort.abort();
  }, []);
  async function add(event: FormEvent, kind: "type" | "deadline") {
    event.preventDefault(); setBusy(true); setMessage("");
    try {
      if (kind === "type") { const item = await api<Kind>("competition-types/", { method: "POST", body: JSON.stringify({ name }) }); setTypes((old) => [...old, item]); setName(""); }
      else { const item = await api<Deadline>("report-deadlines/", { method: "POST", body: JSON.stringify({ title, due_on: due }) }); setDeadlines((old) => [...old, item]); setTitle(""); setDue(""); }
    } catch (cause) { setMessage(cause instanceof Error ? cause.message : "Не удалось сохранить"); }
    finally { setBusy(false); }
  }
  async function toggle(item: Kind) {
    setBusy(true);
    try { const updated = await api<Kind>(`competition-types/${item.id}/`, { method: "PATCH", body: JSON.stringify({ is_active: !item.is_active }) }); setTypes((old) => old.map((value) => value.id === item.id ? updated : value)); }
    catch { setMessage("Не удалось изменить тип"); }
    finally { setBusy(false); }
  }
  return <section className="blk"><h2><b>06</b><span>Сроки и справочники</span></h2><div className="workflow-stack">
    {message && <p role="alert">{message}</p>}
    <h3>Сроки отчётов</h3><ul>{deadlines.map((item) => <li key={item.id}>{item.title} · {item.due_on}</li>)}</ul>
    <p>Ходатайства на премии Губернатора: до 1 февраля. Напоминания появляются за 60 дней; сроки отчётов — за 30 дней.</p>
    <form className="workflow-form" onSubmit={(event) => void add(event, "deadline")}><label className="lb">Название отчёта<input className="inp" required value={title} onChange={(event) => setTitle(event.target.value)} /></label><label className="lb">Срок отчёта<input className="inp" type="date" required value={due} onChange={(event) => setDue(event.target.value)} /></label><button className="btn" disabled={busy}>Добавить срок отчёта</button></form>
    <h3>Типы соревнований</h3><ul>{types.map((item) => <li key={item.id}>{item.name} · {item.is_active ? "Активен" : "Архив"} <button className="btn" disabled={busy} onClick={() => void toggle(item)}>{item.is_active ? "В архив" : "Восстановить"}</button></li>)}</ul>
    <form className="workflow-form" onSubmit={(event) => void add(event, "type")}><label className="lb">Новый тип соревнования<input className="inp" maxLength={100} required value={name} onChange={(event) => setName(event.target.value)} /></label><button className="btn" disabled={busy}>Добавить тип</button></form>
  </div></section>;
}
