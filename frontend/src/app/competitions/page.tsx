"use client";

import { Toast } from "@/components/Toast";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { useCurrentUser } from "@/components/AppShell";
import { CompetitionEditor } from "@/components/CompetitionEditor";
import { TemplateEditor } from "@/components/TemplateEditor";
import { AgeGroup, api, CalendarEntry, Competition, Discipline, ProtocolTemplate } from "@/lib/api";

export default function Competitions() {
  const me = useCurrentUser();
  const [items, setItems] = useState<Competition[]>([]);
  const [disciplines, setDisciplines] = useState<Discipline[]>([]);
  const [groups, setGroups] = useState<AgeGroup[]>([]);
  const [templates, setTemplates] = useState<ProtocolTemplate[]>([]);
  const [calendar, setCalendar] = useState<CalendarEntry[]>([]);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadedFor, setLoadedFor] = useState("");
  const requestId = useRef(0);
  const identity = `${me?.id ?? "guest"}:${me?.active_role ?? "none"}`;
  const [showEditor, setShowEditor] = useState(false);
  const [newGroup, setNewGroup] = useState({ name: "", min_age: "", max_age: "" });
  const [newCalendar, setNewCalendar] = useState({ source: "regional", entry_number: "", title: "", year: String(new Date().getFullYear()), reference_url: "" });
  const reload = useCallback(async () => {
    const request = ++requestId.current;
    setLoading(true);
    setError("");
    try {
      const [nextItems, nextDisciplines, nextGroups, nextTemplates, nextCalendar] = await Promise.all([
        api<Competition[]>("competitions/"), api<Discipline[]>("disciplines/"), api<AgeGroup[]>("age-groups/"), api<ProtocolTemplate[]>("templates/"), api<CalendarEntry[]>("calendar-entries/"),
      ]);
      if (request !== requestId.current) return;
      setItems(nextItems); setDisciplines(nextDisciplines); setGroups(nextGroups); setTemplates(nextTemplates); setCalendar(nextCalendar); setLoadedFor(identity);
    } catch (cause) { if (request === requestId.current) setError(cause instanceof Error ? cause.message : "Не удалось загрузить календарь"); }
    finally { if (request === requestId.current) setLoading(false); }
  }, [identity]);
  useEffect(() => { const counter = requestId; const frame = requestAnimationFrame(() => { void reload(); }); return () => { cancelAnimationFrame(frame); counter.current++; }; }, [reload]);
  async function addGroup(event: FormEvent) {
    event.preventDefault(); setError("");
    try { await api("age-groups/", { method: "POST", body: JSON.stringify({ name: newGroup.name, min_age: Number(newGroup.min_age), max_age: Number(newGroup.max_age) }) }); setNewGroup({ name: "", min_age: "", max_age: "" }); await reload(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось добавить группу"); }
  }
  async function addCalendar(event: FormEvent) {
    event.preventDefault(); setError("");
    try { await api("calendar-entries/", { method: "POST", body: JSON.stringify({ ...newCalendar, year: Number(newCalendar.year) }) }); setNewCalendar({ source: "regional", entry_number: "", title: "", year: String(new Date().getFullYear()), reference_url: "" }); await reload(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось добавить запись календаря"); }
  }
  const visible = items.filter((item) => !filter || item.discipline_name.toLowerCase().includes(filter.toLowerCase()) || item.title.toLowerCase().includes(filter.toLowerCase()));
  return <>
    <header className="dashboard-head"><span className="kick">Соревнования ФСП</span><h1>Календарь</h1><p className="lead">Соревнования, заявки и протоколы из текущей базы данных.</p></header>
    <section className="blk"><h2><b>03</b><span>Календарь</span></h2><div>
      <label className="lb">Поиск по названию и дисциплине<input className="inp workflow-search" value={filter} onChange={(event) => setFilter(event.target.value)} /></label>
      {error && <Toast>{error}</Toast>}
      {loading || (!error && loadedFor !== identity) ? <div className="note" role="status">Загрузка календаря…</div> : loadedFor !== identity ? null : visible.length ? <div className="tw"><table><thead><tr><th>№</th><th>Соревнование</th><th>Дисциплина</th><th>Дата</th><th>Статус</th></tr></thead><tbody>{visible.map((item, index) => <tr key={item.id}><td>{index + 1}</td><td><Link className="workflow-link" href={`/competitions/${item.id}`}>{item.title}</Link></td><td>{item.discipline_name}</td><td className="m">{new Date(item.starts_at).toLocaleDateString("ru-RU")}</td><td><span className={`bd ${item.state === "draft" ? "wn" : ""}`}>{item.state === "draft" ? "Черновик" : item.state === "closed" ? "Завершено" : "Опубликовано"}</span></td></tr>)}</tbody></table></div> : <div className="note">{filter.trim() ? "По вашему запросу соревнования не найдены." : "Соревнований пока нет."}</div>}
    </div></section>
    {me?.active_role === "federation" && loadedFor === identity && !loading && <>
      <section className="blk"><h2><b>+</b><span>Управление</span></h2><div><button className="btn p" type="button" onClick={() => setShowEditor(!showEditor)}>{showEditor ? "Закрыть форму" : "Создать соревнование"}</button>{showEditor && <div className="workflow-spaced"><CompetitionEditor disciplines={disciplines} groups={groups} templates={templates} calendar={calendar} onSaved={(saved) => { setItems((current) => [...current, saved]); setShowEditor(false); }} /></div>}</div></section>
      <section className="blk"><h2><b>+</b><span>Справочники</span></h2><div className="cmp">
        <form className="workflow-form" onSubmit={addGroup}><h3>Возрастная группа</h3><label className="lb">Название<input className="inp" required value={newGroup.name} onChange={(event) => setNewGroup({ ...newGroup, name: event.target.value })} /></label><div className="form-grid"><label className="lb">От лет<input className="inp" required type="number" min="0" value={newGroup.min_age} onChange={(event) => setNewGroup({ ...newGroup, min_age: event.target.value })} /></label><label className="lb">До лет<input className="inp" required type="number" min="0" value={newGroup.max_age} onChange={(event) => setNewGroup({ ...newGroup, max_age: event.target.value })} /></label></div><button className="btn" type="submit">Добавить группу</button></form>
        <form className="workflow-form" onSubmit={addCalendar}><h3>Официальный календарь</h3><label className="lb">Источник<select className="inp" value={newCalendar.source} onChange={(event) => setNewCalendar({ ...newCalendar, source: event.target.value })}><option value="regional">Региональный</option><option value="ekp">ЕКП</option></select></label><label className="lb">Номер записи<input className="inp" required value={newCalendar.entry_number} onChange={(event) => setNewCalendar({ ...newCalendar, entry_number: event.target.value })} /></label><label className="lb">Название<input className="inp" required value={newCalendar.title} onChange={(event) => setNewCalendar({ ...newCalendar, title: event.target.value })} /></label><label className="lb">Год<input className="inp" type="number" required value={newCalendar.year} onChange={(event) => setNewCalendar({ ...newCalendar, year: event.target.value })} /></label><label className="lb">Ссылка на источник<input className="inp" type="url" value={newCalendar.reference_url} onChange={(event) => setNewCalendar({ ...newCalendar, reference_url: event.target.value })} /></label><button className="btn" type="submit">Добавить запись</button></form>
      </div></section>
      <section className="blk"><h2><b>+</b><span>Шаблоны</span></h2><div className="workflow-stack"><p>Версионируемые колонки протокола по дисциплинам. Новые версии применяются к новым соревнованиям.</p><TemplateEditor disciplines={disciplines} onSaved={(template) => setTemplates((current) => [...current, template])} /></div></section>
    </>}
  </>;
}
