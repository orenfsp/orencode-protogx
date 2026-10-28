"use client";
import { FormEvent, useRef, useState, useEffect } from "react";
import { api, Discipline } from "@/lib/api";

type Athlete = { id: number; full_name: string };
export function CoachAthleteSearch({ disciplines, onSaved }: { disciplines: Discipline[]; onSaved: () => Promise<void> }) {
  const [search, setSearch] = useState("");
  const [searched, setSearched] = useState("");
  const [discipline, setDiscipline] = useState("");
  const [rows, setRows] = useState<Athlete[] | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => { const abort = new AbortController(); controller.current = abort; return () => abort.abort(); }, []);
  async function find(event: FormEvent) {
    event.preventDefault(); const signal = controller.current?.signal;
    if (!signal || signal.aborted) return;
    setBusy(true); setMessage(""); setRows(null);
    try { const result = await api<Athlete[]>(`coach-athlete-directory/?search=${encodeURIComponent(search.trim())}`, { signal }); if (!signal.aborted) { setRows(result); setSearched(search.trim()); } }
    catch (cause) { if (!signal.aborted) setMessage(cause instanceof Error ? cause.message : "Не удалось выполнить поиск"); }
    finally { if (!signal.aborted) setBusy(false); }
  }
  async function request(athlete: Athlete) {
    const signal = controller.current?.signal;
    if (!signal || signal.aborted) return;
    setBusy(true); setMessage("");
    try { await api("coach-athlete-directory/", { method: "POST", signal, body: JSON.stringify({ athlete: athlete.id, discipline: Number(discipline), search: searched }) }); if (!signal.aborted) { setMessage("Запрос сохранён. Связь станет активной после подтверждения спортсменом."); await onSaved(); } }
    catch (cause) { if (!signal.aborted) setMessage(cause instanceof Error ? cause.message : "Запрос не сохранён"); }
    finally { if (!signal.aborted) setBusy(false); }
  }
  return <section className="blk"><h2><b>01</b><span>Найти спортсмена</span></h2><div className="workflow-stack"><p>Поиск показывает минимум данных о совершеннолетних с действующим согласием. Несовершеннолетние доступны здесь только своему подтверждённому тренеру; новый запрос можно направить по известному email ниже.</p><form className="workflow-form" onSubmit={find}><label className="lb">Имя спортсмена<input className="inp" required minLength={3} maxLength={100} value={search} onChange={(event) => setSearch(event.target.value)} /></label><button className="btn" disabled={busy}>Найти в реестре</button><label className="lb">Дисциплина для новой связи<select className="inp" value={discipline} onChange={(event) => setDiscipline(event.target.value)}><option value="">Выберите дисциплину</option>{disciplines.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label></form>{message && <p role="status">{message}</p>}{rows && (rows.length ? <ul>{rows.map((item) => <li key={item.id}><p>{item.full_name} · №{item.id}</p><button className="btn" disabled={busy || !discipline} onClick={() => void request(item)}>Запросить связь: {item.full_name}</button></li>)}</ul> : <p>Спортсмены не найдены.</p>)}</div></section>;
}
