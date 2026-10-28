"use client";

import { Toast } from "@/components/Toast";
import { QualificationCorrectionPanel } from "@/components/QualificationCorrectionPanel";
import { RecordHistory } from "@/components/RecordHistory";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useCurrentUser } from "@/components/AppShell";
import { api } from "@/lib/api";

// DTO модуля AC-09 описаны локально: общий src/lib/api.ts принадлежит руководителю.
type Option = { value: string; label: string };
type Options = { ranks: Option[]; categories: Option[]; request_types: Option[]; hint_disclaimer: string };
type Hint = { rank: string; rank_label: string; rule_version: string; source_verified: boolean; disclaimer: string };
type ResultRow = { result: number; athlete: number; athlete_name: string; competition: number; competition_title: string; competition_level: string; discipline_name: string; place: number | null; score: string | null; current_rank: string | null; current_rank_label: string | null; pending_ranks: string[]; hint: Hint | null };
type Review = "pending" | "approved" | "rejected";
type RecordInfo = { id: number; order_number: string; assigned_on: string; valid_until: string } | null;
type RankApp = { id: number; athlete: number; athlete_name: string; submitted_by_name: string; request_type: string; requested_rank_label: string; discipline_name: string; competition: number; competition_title: string; place: number | null; comment: string; status: Review; decision_reason: string; submitted_at: string; record: RecordInfo };
type CatApp = { id: number; judge: number; judge_name: string; request_type: string; requested_category_label: string; comment: string; status: Review; decision_reason: string; submitted_at: string; record: RecordInfo };
type Validity = "active" | "expiring" | "expired";
type RankRecord = { id: number; athlete: number; athlete_name: string; discipline_name: string; rank_label: string; order_number: string; assigned_on: string; valid_until: string; validity: Validity; days_left: number; competition_id: number; competition_title: string; place: number | null };
type CatRecord = { id: number; judge: number; judge_name: string; category_label: string; order_number: string; assigned_on: string; valid_until: string; validity: Validity; days_left: number };
type Deadline = { kind: "rank" | "judge_category"; person: number; person_name: string; label: string; valid_until: string; days_left: number; validity: Validity };
type DecisionBody = { status: "approved" | "rejected"; reason?: string; order_number?: string; assigned_on?: string; valid_until?: string };

const fmt = (iso: string) => iso.split("T")[0].split("-").reverse().join(".");
const statusName: Record<Review, string> = { pending: "На рассмотрении", approved: "Присвоено", rejected: "Отклонено" };
const typeName: Record<string, string> = { assign: "Присвоение", confirm: "Подтверждение" };
const validityName: Record<Validity, string> = { active: "Действует", expiring: "Скоро истекает", expired: "Истёк" };
const validityClass: Record<Validity, string> = { active: "bd", expiring: "bd wn", expired: "bd er" };
const today = () => new Date().toISOString().slice(0, 10);

function Status({ status }: { status: Review }) { return <span className={`bd ${status === "pending" ? "wn" : status === "rejected" ? "er" : ""}`}>{statusName[status]}</span>; }
function Validity_({ value, left }: { value: Validity; left: number }) { return <span className={validityClass[value]}>{validityName[value]}{value !== "expired" ? ` · ${left} дн.` : ""}</span>; }

function DecisionForm({ approveLabel, onDecide }: { approveLabel: string; onDecide: (body: DecisionBody) => Promise<void> }) {
  const [order, setOrder] = useState("");
  const [assignedOn, setAssignedOn] = useState(today);
  const [validUntil, setValidUntil] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  async function run(body: DecisionBody) { setBusy(true); try { await onDecide(body); } finally { setBusy(false); } }
  return <div className="workflow-form">
    <label className="lb">Номер приказа<input className="inp" value={order} onChange={(event) => setOrder(event.target.value)} /></label>
    <label className="lb">Дата присвоения<input className="inp" type="date" max={today()} value={assignedOn} onChange={(event) => setAssignedOn(event.target.value)} /></label>
    <label className="lb">Действует до<input className="inp" type="date" min={assignedOn} value={validUntil} onChange={(event) => setValidUntil(event.target.value)} /></label>
    <label className="lb">Причина отказа<input className="inp" value={reason} onChange={(event) => setReason(event.target.value)} /></label>
    <div className="workflow-actions">
      <button className="btn p" type="button" disabled={busy} onClick={() => void run({ status: "approved", order_number: order, assigned_on: assignedOn, valid_until: validUntil })}>{approveLabel}</button>
      <button className="btn" type="button" disabled={busy} onClick={() => void run({ status: "rejected", reason })}>Отклонить</button>
    </div>
  </div>;
}

function DeadlineTable({ items }: { items: Deadline[] }) {
  if (!items.length) return <div className="note">Истекающих и просроченных сроков нет.</div>;
  return <div className="tw"><table><thead><tr><th>№</th><th>Кто</th><th>Что</th><th>Действует до</th><th>Статус</th></tr></thead><tbody>{items.map((item, index) => <tr key={`${item.kind}-${item.person}`}><td>{index + 1}</td><td>{item.person_name}</td><td>{item.kind === "rank" ? "Разряд" : "Категория"}: {item.label}</td><td className="m">{fmt(item.valid_until)}</td><td><Validity_ value={item.validity} left={item.days_left} /></td></tr>)}</tbody></table></div>;
}

function RankHistoryTable({ rows, showAthlete }: { rows: RankRecord[]; showAthlete: boolean }) {
  if (!rows.length) return <div className="note">Присвоенных разрядов пока нет.</div>;
  return <div className="tw"><table><thead><tr><th>№</th>{showAthlete && <th>Спортсмен</th>}<th>Разряд</th><th>Основание</th><th>Приказ</th><th>Присвоен</th><th>Срок</th></tr></thead><tbody>{rows.map((row, index) => <tr key={row.id}><td>{index + 1}</td>{showAthlete && <td>{row.athlete_name}</td>}<td>{row.rank_label}</td><td><Link className="workflow-link" href={`/competitions/${row.competition_id}`}>{row.competition_title}</Link>{row.place ? `, ${row.place} место` : ""}</td><td>{row.order_number}<RecordHistory path={`qualification-history/rank/${row.id}/corrections/`} version={`${row.order_number}:${row.assigned_on}:${row.valid_until}`} /></td><td className="m">{fmt(row.assigned_on)}</td><td><Validity_ value={row.validity} left={row.days_left} /> <span className="m">до {fmt(row.valid_until)}</span></td></tr>)}</tbody></table></div>;
}

function CatHistoryTable({ rows, showJudge }: { rows: CatRecord[]; showJudge: boolean }) {
  if (!rows.length) return <div className="note">Присвоенных категорий пока нет.</div>;
  return <div className="tw"><table><thead><tr><th>№</th>{showJudge && <th>Судья</th>}<th>Категория</th><th>Приказ</th><th>Присвоена</th><th>Срок</th></tr></thead><tbody>{rows.map((row, index) => <tr key={row.id}><td>{index + 1}</td>{showJudge && <td>{row.judge_name}</td>}<td>{row.category_label}</td><td>{row.order_number}<RecordHistory path={`qualification-history/category/${row.id}/corrections/`} version={`${row.order_number}:${row.assigned_on}:${row.valid_until}`} /></td><td className="m">{fmt(row.assigned_on)}</td><td><Validity_ value={row.validity} left={row.days_left} /> <span className="m">до {fmt(row.valid_until)}</span></td></tr>)}</tbody></table></div>;
}

function RankAppTable({ rows, showAthlete }: { rows: RankApp[]; showAthlete: boolean }) {
  if (!rows.length) return <div className="note">Заявок на разряд пока нет.</div>;
  return <div className="tw"><table><thead><tr><th>№</th>{showAthlete && <th>Спортсмен</th>}<th>Запрос</th><th>Результат</th><th>Статус</th><th>Решение</th></tr></thead><tbody>{rows.map((row, index) => <tr key={row.id}><td>{index + 1}</td>{showAthlete && <td>{row.athlete_name}</td>}<td>{typeName[row.request_type]}: {row.requested_rank_label}</td><td><Link className="workflow-link" href={`/competitions/${row.competition}`}>{row.competition_title}</Link>{row.place ? `, ${row.place} место` : ""}</td><td><Status status={row.status} /></td><td>{row.status === "approved" && row.record ? `Приказ ${row.record.order_number}, до ${fmt(row.record.valid_until)}` : row.decision_reason || "—"}</td></tr>)}</tbody></table></div>;
}

function CatAppTable({ rows, showJudge }: { rows: CatApp[]; showJudge: boolean }) {
  if (!rows.length) return <div className="note">Заявок на категорию пока нет.</div>;
  return <div className="tw"><table><thead><tr><th>№</th>{showJudge && <th>Судья</th>}<th>Запрос</th><th>Статус</th><th>Решение</th></tr></thead><tbody>{rows.map((row, index) => <tr key={row.id}><td>{index + 1}</td>{showJudge && <td>{row.judge_name}</td>}<td>{typeName[row.request_type]}: {row.requested_category_label}</td><td><Status status={row.status} /></td><td>{row.status === "approved" && row.record ? `Приказ ${row.record.order_number}, до ${fmt(row.record.valid_until)}` : row.decision_reason || "—"}</td></tr>)}</tbody></table></div>;
}

export default function Qualifications() {
  const me = useCurrentUser();
  return <QualificationsContent key={`${me?.id ?? "guest"}:${me?.active_role ?? "none"}`} me={me} />;
}

function QualificationsContent({ me }: { me: ReturnType<typeof useCurrentUser> }) {
  const role = me?.active_role;
  const [options, setOptions] = useState<Options | null>(null);
  const [deadlines, setDeadlines] = useState<Deadline[]>([]);
  const [results, setResults] = useState<ResultRow[]>([]);
  const [resultPage, setResultPage] = useState(1);
  const [resultPages, setResultPages] = useState(1);
  const [rankApps, setRankApps] = useState<RankApp[]>([]);
  const [rankHistory, setRankHistory] = useState<RankRecord[]>([]);
  const [catApps, setCatApps] = useState<CatApp[]>([]);
  const [catHistory, setCatHistory] = useState<CatRecord[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [resultId, setResultId] = useState("");
  const [rank, setRank] = useState("");
  const [requestType, setRequestType] = useState("assign");
  const [category, setCategory] = useState("");
  const [comment, setComment] = useState("");
  const requestId = useRef(0);

  const reload = useCallback(async () => {
    if (!role) return;
    const request = ++requestId.current;
    try {
      const [nextOptions, nextDeadlines] = await Promise.all([api<Options>("qualification-options/"), api<{ items: Deadline[] }>("qualification-deadlines/")]);
      if (request !== requestId.current) return;
      setOptions(nextOptions); setDeadlines(nextDeadlines.items);
      if (role !== "judge") {
        const [nextResults, nextApps, nextHistory] = await Promise.all([api<{ items: ResultRow[]; pages: number }>(`rank-results/?page=${resultPage}`), api<RankApp[]>("rank-applications/"), api<RankRecord[]>("rank-history/")]);
        if (request !== requestId.current) return;
        setResults(nextResults.items); setResultPages(nextResults.pages); setRankApps(nextApps); setRankHistory(nextHistory);
      }
      if (role === "judge" || role === "federation") {
        const [nextApps, nextHistory] = await Promise.all([api<CatApp[]>("judge-category-applications/"), api<CatRecord[]>("judge-category-history/")]);
        if (request !== requestId.current) return;
        setCatApps(nextApps); setCatHistory(nextHistory);
      }
    } catch (cause) { if (request === requestId.current) setError(cause instanceof Error ? cause.message : "Не удалось загрузить данные"); }
  }, [role, resultPage]);
  useEffect(() => { const counter = requestId; const frame = requestAnimationFrame(() => { void reload(); }); return () => { cancelAnimationFrame(frame); counter.current++; }; }, [reload]);

  const selected = results.find((row) => String(row.result) === resultId);
  function pickResult(value: string) { setResultId(value); const row = results.find((item) => String(item.result) === value); setRank(row?.hint?.rank ?? ""); }

  async function submitRank(event: FormEvent) {
    event.preventDefault(); setError(""); setNotice("");
    try { await api("rank-applications/", { method: "POST", body: JSON.stringify({ result: Number(resultId), requested_rank: rank, request_type: requestType, comment }) }); setNotice("Заявка отправлена в федерацию"); setComment(""); await reload(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Заявка не отправлена"); }
  }
  async function submitCategory(event: FormEvent) {
    event.preventDefault(); setError(""); setNotice("");
    try { await api("judge-category-applications/", { method: "POST", body: JSON.stringify({ requested_category: category, request_type: requestType, comment }) }); setNotice("Заявка отправлена в федерацию"); setComment(""); await reload(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Заявка не отправлена"); }
  }
  async function decide(path: string, id: number, body: DecisionBody) {
    setError(""); setNotice("");
    try { await api(`${path}/${id}/decision/`, { method: "POST", body: JSON.stringify(body) }); setNotice(body.status === "approved" ? "Решение сохранено, запись добавлена в историю" : "Заявка отклонена"); await reload(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Решение не сохранено"); }
  }

  const typeSelect = <label className="lb">Тип заявки<select className="inp" value={requestType} onChange={(event) => setRequestType(event.target.value)}>{options?.request_types.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>;
  const commentField = <label className="lb">Комментарий<textarea className="inp" maxLength={1000} value={comment} onChange={(event) => setComment(event.target.value)} /></label>;
  const pendingRank = rankApps.filter((item) => item.status === "pending");
  const pendingCat = catApps.filter((item) => item.status === "pending");
  const hinted = results.filter((row) => row.hint);

  return <><header className="dashboard-head"><span className="kick"><Link className="workflow-link" href="/dashboard">← Кабинет</Link></span><h1>Разряды и судейские категории</h1><p className="lead">Заявка, решение федерации, приказ и срок действия. Подача в Госуслугах выполняется вне платформы.</p></header>
    {error && <Toast>{error}</Toast>}{notice && <Toast tone="success">{notice}</Toast>}
    {role !== "judge" && role && resultPages > 1 && <div className="workflow-actions"><button type="button" className="btn" disabled={resultPage <= 1} onClick={() => { setResultId(""); setResultPage((page) => page - 1); }}>Предыдущие результаты</button><span>Страница {resultPage} из {resultPages}</span><button type="button" className="btn" disabled={resultPage >= resultPages} onClick={() => { setResultId(""); setResultPage((page) => page + 1); }}>Следующие результаты</button></div>}
    {!me ? <section className="blk"><h2><b>01</b><span>Вход</span></h2><Toast>Для доступа <Link href="/login">войдите</Link>.</Toast></section> : <>
      {role === "federation" && <>
        <section className="blk"><h2><b>01</b><span>Заявки на разряд</span></h2><div className="workflow-stack">{pendingRank.length ? pendingRank.map((app) => <div className="workflow-record" key={app.id}><strong>{app.athlete_name}</strong><span>{typeName[app.request_type]}: {app.requested_rank_label} · {app.discipline_name}</span><span>Основание: <Link className="workflow-link" href={`/competitions/${app.competition}`}>{app.competition_title}</Link>{app.place ? `, ${app.place} место` : ""}. Подал: {app.submitted_by_name}</span>{app.comment && <span>{app.comment}</span>}<DecisionForm approveLabel="Присвоить" onDecide={(body) => decide("rank-applications", app.id, body)} /></div>) : <div className="note">Заявок на рассмотрении нет.</div>}</div></section>
        <section className="blk"><h2><b>02</b><span>Заявки на категорию судьи</span></h2><div className="workflow-stack">{pendingCat.length ? pendingCat.map((app) => <div className="workflow-record" key={app.id}><strong>{app.judge_name}</strong><span>{typeName[app.request_type]}: {app.requested_category_label}</span>{app.comment && <span>{app.comment}</span>}<DecisionForm approveLabel="Присвоить" onDecide={(body) => decide("judge-category-applications", app.id, body)} /></div>) : <div className="note">Заявок на рассмотрении нет.</div>}</div></section>
        <section className="blk"><h2><b>03</b><span>Результаты, возможно подходящие под разряд</span></h2><div><Toast>{options?.hint_disclaimer} Правила и источник проверяет федерация.</Toast>{hinted.length ? <div className="tw"><table><thead><tr><th>№</th><th>Спортсмен</th><th>Результат</th><th>Подсказка</th><th>Правило</th></tr></thead><tbody>{hinted.map((row, index) => <tr key={row.result}><td>{index + 1}</td><td>{row.athlete_name}</td><td><Link className="workflow-link" href={`/competitions/${row.competition}`}>{row.competition_title}</Link>, {row.place} место</td><td>{row.hint?.rank_label}{row.current_rank_label ? ` (сейчас: ${row.current_rank_label})` : ""}</td><td className="m">{row.hint?.rule_version}{row.hint?.source_verified ? "" : " · не сверено"}</td></tr>)}</tbody></table></div> : <div className="note">Подходящих результатов нет.</div>}</div></section>
        <section className="blk"><h2><b>04</b><span>Контроль сроков</span></h2><DeadlineTable items={deadlines} /></section>
        <section className="blk"><h2><b>05</b><span>Реестр разрядов</span></h2><RankHistoryTable rows={rankHistory} showAthlete /></section>
        <section className="blk"><h2><b>06</b><span>Реестр категорий судей</span></h2><CatHistoryTable rows={catHistory} showJudge /></section>
        <QualificationCorrectionPanel ranks={rankHistory} categories={catHistory} onSaved={reload} />
        <section className="blk"><h2><b>07</b><span>Все заявки</span></h2><div className="workflow-stack"><RankAppTable rows={rankApps} showAthlete /><CatAppTable rows={catApps} showJudge /></div></section>
      </>}
      {(role === "athlete" || role === "coach") && <>
        <section className="blk"><h2><b>01</b><span>Подать заявку на разряд</span></h2><div className="workflow-stack">
          {role === "athlete" && <div className="note">Если у вас есть подтверждённый тренер по дисциплине, заявку подаёт он.</div>}
          {results.length ? <form className="workflow-form" onSubmit={submitRank}>
            <label className="lb">Результат-основание<select className="inp" required value={resultId} onChange={(event) => pickResult(event.target.value)}><option value="">Выберите</option>{results.map((row) => <option key={row.result} value={row.result}>{role === "coach" ? `${row.athlete_name} · ` : ""}{row.competition_title} · {row.place} место</option>)}</select></label>
            {selected?.hint && <Toast>Подсказка: {selected.hint.rank_label} (правило {selected.hint.rule_version}{selected.hint.source_verified ? "" : ", не сверено с источником"}). {selected.hint.disclaimer}</Toast>}
            <label className="lb">Разряд<select className="inp" required value={rank} onChange={(event) => setRank(event.target.value)}><option value="">Выберите</option>{options?.ranks.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
            {typeSelect}{commentField}
            <div className="workflow-actions"><button className="btn p" type="submit">Отправить в федерацию</button></div>
          </form> : <div className="note">Нет проверенных результатов опубликованных протоколов, на которые можно сослаться.</div>}
        </div></section>
        <section className="blk"><h2><b>02</b><span>Заявки</span></h2><RankAppTable rows={rankApps} showAthlete={role === "coach"} /></section>
        <section className="blk"><h2><b>03</b><span>Разряды</span></h2><RankHistoryTable rows={rankHistory} showAthlete={role === "coach"} /></section>
        <section className="blk"><h2><b>04</b><span>Сроки действия</span></h2><DeadlineTable items={deadlines} /></section>
      </>}
      {role === "judge" && <>
        <section className="blk"><h2><b>01</b><span>Подать заявку на категорию</span></h2><form className="workflow-form" onSubmit={submitCategory}>
          <label className="lb">Категория<select className="inp" required value={category} onChange={(event) => setCategory(event.target.value)}><option value="">Выберите</option>{options?.categories.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          {typeSelect}{commentField}
          <div className="workflow-actions"><button className="btn p" type="submit">Отправить в федерацию</button></div>
        </form></section>
        <section className="blk"><h2><b>02</b><span>Заявки</span></h2><CatAppTable rows={catApps} showJudge={false} /></section>
        <section className="blk"><h2><b>03</b><span>Моя категория</span></h2><CatHistoryTable rows={catHistory} showJudge={false} /></section>
        <section className="blk"><h2><b>04</b><span>Сроки действия</span></h2><DeadlineTable items={deadlines} /></section>
      </>}
    </>}
  </>;
}
