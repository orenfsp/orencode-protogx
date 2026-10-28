"use client";

import { Toast } from "@/components/Toast";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useCurrentUser } from "@/components/AppShell";
import { api, CoachLink, Discipline } from "@/lib/api";

export default function CoachLinks() {
  const me = useCurrentUser();
  const role = me?.active_role;
  const [links, setLinks] = useState<CoachLink[]>([]);
  const [disciplines, setDisciplines] = useState<Discipline[]>([]);
  const [email, setEmail] = useState("");
  const [discipline, setDiscipline] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const reload = useCallback(async () => {
    if (role !== "coach" && role !== "athlete") return;
    try { const [nextLinks, nextDisciplines] = await Promise.all([api<CoachLink[]>("coach-links/"), api<Discipline[]>("disciplines/")]); setLinks(nextLinks); setDisciplines(nextDisciplines); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось загрузить связи"); }
  }, [role]);
  useEffect(() => { const frame = requestAnimationFrame(() => { void reload(); }); return () => cancelAnimationFrame(frame); }, [reload]);
  async function request(event: FormEvent) {
    event.preventDefault(); setError("");
    try { await api("coach-links/", { method: "POST", body: JSON.stringify({ athlete_email: email, discipline: Number(discipline) }) }); setNotice("Если аккаунт найден, запрос появится у спортсмена"); await reload(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Запрос не отправлен"); }
  }
  async function decide(id: number, status: "confirmed" | "rejected") {
    setError("");
    try { await api(`coach-links/${id}/decision/`, { method: "POST", body: JSON.stringify({ status }) }); setNotice(status === "confirmed" ? "Связь подтверждена" : "Запрос отклонён"); await reload(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Решение не сохранено"); }
  }
  return <><header className="dashboard-head"><span className="kick"><Link className="workflow-link" href="/dashboard">← Кабинет</Link></span><h1>Связи тренера</h1><p className="lead">Тренер может подавать заявки только после подтверждения спортсменом связи по дисциплине.</p></header>
    {error && <Toast>{error}</Toast>}{notice && <Toast tone="success">{notice}</Toast>}
    {role === "coach" && <section className="blk"><h2><b>01</b><span>Запросить связь</span></h2><div className="workflow-stack"><form className="workflow-form" onSubmit={request}><label className="lb">Email спортсмена<input className="inp" type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label><label className="lb">Дисциплина<select className="inp" required value={discipline} onChange={(event) => setDiscipline(event.target.value)}><option value="">Выберите</option>{disciplines.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><button className="btn p" type="submit">Отправить запрос</button></form></div></section>}
    {(role === "coach" || role === "athlete") && <section className="blk"><h2><b>02</b><span>Связи</span></h2><div className="workflow-stack">{links.length ? links.map((link) => <div className="workflow-record" key={link.id}><strong>{role === "coach" ? link.athlete_name : link.coach_name}</strong><span>{disciplines.find((item) => item.id === link.discipline)?.name}</span><span className={`bd ${link.status === "pending" ? "wn" : ""}`}>{link.status === "pending" ? "Ожидает" : link.status === "confirmed" ? "Подтверждена" : "Отклонена"}</span>{role === "athlete" && link.status === "pending" && <div className="workflow-actions"><button className="btn p" type="button" onClick={() => void decide(link.id, "confirmed")}>Подтвердить</button><button className="btn" type="button" onClick={() => void decide(link.id, "rejected")}>Отклонить</button></div>}</div>) : <div className="note">Связей пока нет.</div>}</div></section>}
  </>;
}
