"use client";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";

type Record = { id: number; order_number: string; assigned_on: string; valid_until: string };
export function QualificationCorrectionPanel({ ranks, categories, onSaved }: { ranks: Record[]; categories: Record[]; onSaved: () => Promise<void> }) {
  const [selection, setSelection] = useState("");
  const [order, setOrder] = useState("");
  const [assigned, setAssigned] = useState("");
  const [until, setUntil] = useState("");
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  function choose(value: string) {
    setSelection(value);
    const [kind, id] = value.split(":");
    const item = (kind === "rank" ? ranks : categories).find((record) => record.id === Number(id));
    setOrder(item?.order_number ?? ""); setAssigned(item?.assigned_on ?? ""); setUntil(item?.valid_until ?? "");
  }
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage("");
    const [kind, id] = selection.split(":");
    try { await api(`qualification-history/${kind}/${id}/corrections/`, { method: "POST", body: JSON.stringify({ order_number: order, assigned_on: assigned, valid_until: until, reason }) }); setMessage("Исправление сохранено; предыдущие реквизиты остаются в журнале версий."); await onSaved(); }
    catch (cause) { setMessage(cause instanceof Error ? cause.message : "Исправление не сохранено"); }
    finally { setBusy(false); }
  }
  return <section className="blk"><h2><b>08</b><span>Исправление реквизитов</span></h2><div><p>Изменение разряда или категории оформляется отдельным решением. Здесь исправляются номер приказа и даты с сохранением предыдущей версии.</p><form className="workflow-form" onSubmit={save}>
    <label className="lb">Запись истории<select className="inp" required value={selection} onChange={(event) => choose(event.target.value)}><option value="">Выберите</option>{ranks.map((item) => <option key={`r${item.id}`} value={`rank:${item.id}`}>Разряд #{item.id} · {item.order_number}</option>)}{categories.map((item) => <option key={`c${item.id}`} value={`category:${item.id}`}>Категория #{item.id} · {item.order_number}</option>)}</select></label>
    <label className="lb">Исправленный номер приказа<input className="inp" required value={order} onChange={(event) => setOrder(event.target.value)} /></label><label className="lb">Исправленная дата присвоения<input className="inp" required type="date" value={assigned} onChange={(event) => setAssigned(event.target.value)} /></label><label className="lb">Исправленный срок действия<input className="inp" required type="date" value={until} onChange={(event) => setUntil(event.target.value)} /></label><label className="lb">Причина исправления<input className="inp" required value={reason} onChange={(event) => setReason(event.target.value)} /></label><button className="btn" disabled={busy}>Сохранить исправление</button>
  </form>{message && <p role="status">{message}</p>}</div></section>;
}
