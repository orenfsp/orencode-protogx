"use client";

import { Toast } from "@/components/Toast";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useCurrentUser } from "@/components/AppShell";
import { api } from "@/lib/api";

type HistoryRow = { competition_id: number; competition_title: string; version: number; published_at: string; row: { status: string; place: number | null; score: string | null } };
const statusName: Record<string, string> = { classified: "Классифицирован", no_show: "Не явился", unclassified: "Без результата", disqualified: "Дисквалифицирован", pending_result: "Результат не внесён" };

function HistoryResults() {
  const [rows, setRows] = useState<HistoryRow[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let current = true;
    api<HistoryRow[]>("history/").then((result) => { if (current) setRows(result); }).catch((cause) => { if (current) setError(cause instanceof Error ? cause.message : "История недоступна"); });
    return () => { current = false; };
  }, []);
  return error ? <Toast>{error}</Toast> : !rows ? <div className="note" role="status">Загрузка истории…</div> : rows.length ? <div className="tw"><table><thead><tr><th>№</th><th>Соревнование</th><th>Статус</th><th>Место</th><th>Баллы</th><th>Протокол</th></tr></thead><tbody>{rows.map((entry, index) => <tr key={entry.competition_id}><td>{index + 1}</td><td><Link className="workflow-link" href={`/competitions/${entry.competition_id}`}>{entry.competition_title}</Link></td><td>{statusName[entry.row.status] ?? entry.row.status}</td><td>{entry.row.place ?? "—"}</td><td>{entry.row.score ?? "—"}</td><td className="m">v{entry.version}<p><a className="workflow-link" href={`/api/v1/history/${entry.competition_id}/protocols/${entry.version}/?file_format=pdf`}>Моя выписка · PDF</a></p></td></tr>)}</tbody></table></div> : <div className="note">Опубликованных результатов пока нет.</div>;
}

export default function History() {
  const me = useCurrentUser();
  return <><header className="dashboard-head"><span className="kick"><Link className="workflow-link" href="/dashboard">← Кабинет</Link></span><h1>История результатов</h1><p className="lead">Последние опубликованные версии протоколов, в которых вы участвовали.</p>{me?.active_role === "athlete" && <a className="btn" href="/api/v1/reports/athlete-participation/">Скачать отчёт выступлений · XLSX</a>}</header><section className="blk"><h2><b>01</b><span>Выступления</span></h2><div>{me?.active_role === "athlete" ? <HistoryResults key={me.id} /> : <div className="note">Откройте роль спортсмена.</div>}</div></section></>;
}
