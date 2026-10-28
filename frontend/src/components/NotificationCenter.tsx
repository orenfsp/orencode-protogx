"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import Link from "next/link";

type Notice = { id: number; kind: string; title: string; body: string; created_at: string; read_at: string | null; status: "pending" | "sent" | "failed" | "cancelled"; attempts: number; error_code: string };
const delivery = { pending: "Email в очереди", sent: "Email отправлен", failed: "Ошибка доставки email", cancelled: "Email отменён" };

// Parent keys by identity AND role: role switches remove stale data and abort requests.
export function NotificationCenter() {
  const [items, setItems] = useState<Notice[] | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<number | null>(null);
  const [expanded, setExpanded] = useState(false);
  const controller = useRef<AbortController | null>(null);
  async function load(signal: AbortSignal) {
    try { const result = await api<Notice[]>("notifications/", { signal }); if (!signal.aborted) { setItems(result); setError(""); } }
    catch { if (!signal.aborted) setError("Не удалось загрузить уведомления. Попробуйте ещё раз."); }
  }
  useEffect(() => {
    const abort = new AbortController(); controller.current = abort;
    void api<Notice[]>("notifications/", { signal: abort.signal }).then((result) => {
      if (!abort.signal.aborted) setItems(result);
    }).catch(() => { if (!abort.signal.aborted) setError("Не удалось загрузить уведомления. Попробуйте ещё раз."); });
    return () => abort.abort();
  }, []);
  async function markRead(id: number) {
    const signal = controller.current?.signal;
    if (!signal || signal.aborted) return;
    setBusy(id);
    try {
      const result = await api<Notice>(`notifications/${id}/read/`, { method: "POST", signal });
      if (!signal.aborted) setItems((old) => old?.map((item) => item.id === id ? result : item) ?? null);
    } catch { if (!signal.aborted) setError("Не удалось отметить уведомление прочитанным."); }
    finally { if (!signal.aborted) setBusy(null); }
  }
  return <section className="blk" aria-labelledby="notifications-heading"><h2 id="notifications-heading"><b>04</b><span>Уведомления</span></h2><div>
    <p>События текущей роли · последние 100 уведомлений.</p>
    <button className="btn" onClick={() => { if (controller.current) void load(controller.current.signal); }}>Обновить уведомления</button>
    {error && <p role="alert">{error}</p>}
    {!items ? <p role="status">Загрузка уведомлений…</p> : items.length === 0 ? <p className="note">Уведомлений пока нет.</p> : <ul className="workflow-stack notifications-list">{(expanded ? items : items.slice(0, 5)).map((item) => <li className="workflow-record notification-item" key={item.id}>
      <p><strong>{item.title}</strong> · <time dateTime={item.created_at}>{new Date(item.created_at).toLocaleString("ru-RU")}</time></p>
      <p>{item.body}</p><p><span className={`bd ${item.status === "failed" ? "er" : ""}`}>{delivery[item.status]}</span></p>
      <p><Link className="workflow-link" href={item.kind.includes("rank") || item.kind.includes("category") ? "/qualifications" : item.kind.includes("report") || item.kind.includes("premium") ? "/dashboard" : "/competitions"}>Открыть раздел события</Link></p>
      {item.read_at ? <span>Прочитано</span> : <button className="btn" disabled={busy !== null} onClick={() => void markRead(item.id)} aria-label={`Отметить прочитанным: ${item.title}`}>Отметить прочитанным</button>}
    </li>)}</ul>}
    {items && items.length > 5 && <button className="btn" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>{expanded ? "Свернуть список" : `Показать все уведомления (${items.length})`}</button>}
  </div></section>;
}
