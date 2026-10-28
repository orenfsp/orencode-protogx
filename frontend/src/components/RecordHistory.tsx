"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Revision = { id: number; created_at: string; reason?: string; action?: string; active_role?: string; before: Record<string, unknown>; after: Record<string, unknown> };
const labels: Record<string, string> = { pending: "Ожидает подтверждения", confirmed: "Активна", rejected: "Отклонена", suspended: "Приостановлена", ended: "Завершена", status: "Статус", order_number: "Приказ", assigned_on: "Дата присвоения", valid_until: "Срок действия", reason: "Причина", discipline_id: "Дисциплина", revision: "Версия", athlete: "Спортсмен", coach: "Тренер" };
const display = (value: unknown) => typeof value === "string" ? labels[value] ?? value : String(value ?? "—");

function HistoryEntries({ path, version }: { path: string; version: string }) {
  const [rows, setRows] = useState<Revision[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const abort = new AbortController();
    void api<Revision[]>(path, { signal: abort.signal }).then((value) => { if (!abort.signal.aborted) setRows(value); }).catch(() => { if (!abort.signal.aborted) setError("Не удалось загрузить историю"); });
    return () => abort.abort();
  }, [path, version]);
  return error ? <p role="alert">{error}</p> : !rows ? <p role="status">Загрузка истории…</p> : rows.length === 0 ? <p>Изменений пока нет.</p> : <ol>{rows.map((row) => <li key={row.id}><p><time dateTime={row.created_at}>{new Date(row.created_at).toLocaleString("ru-RU")}</time>{row.active_role ? ` · ${labels[row.active_role] ?? (row.active_role === "federation" ? "Федерация" : row.active_role)}` : ""}</p>{row.action === "coach_link.requested" && <p>Запрошена связь</p>}{row.action === "coach_link.decided" && <p>Решение спортсмена</p>}{Object.keys(row.after).filter((key) => key !== "reason" && key !== "revision").map((key) => <p key={key}>{labels[key] ?? key}: {key in row.before ? `${display(row.before[key])} → ` : ""}{display(row.after[key])}</p>)}{Boolean(row.reason || row.after.reason) && <p>Причина: {String(row.reason || row.after.reason)}</p>}</li>)}</ol>;
}

export function RecordHistory({ path, version = "" }: { path: string; version?: string }) {
  const [opened, setOpened] = useState(false);
  return <details onToggle={(event) => setOpened(event.currentTarget.open)}><summary>История изменений</summary>{opened && <HistoryEntries key={`${path}:${version}`} path={path} version={version} />}</details>;
}
