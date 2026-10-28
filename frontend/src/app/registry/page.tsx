"use client";

import { useEffect, useState } from "react";
import { useCurrentUser } from "@/components/AppShell";
import { api } from "@/lib/api";

type Person = { id: number; full_name: string; organization: string | null; is_active: boolean };
type Org = { id: number; name: string; municipality: string; code: string; is_active: boolean };
type Page = { count: number; next: string | null; previous: string | null; results: (Person | Org)[] };
type Period = { id: number; starts_on: string; ends_on: string | null; organization_name?: string; discipline_name?: string; municipality?: string; stage?: string };
const labels = { athletes: "Спортсмены", coaches: "Тренеры", judges: "Судьи", organizations: "Организации" } as const;
type Kind = keyof typeof labels;

export default function RegistryPage() {
  const user = useCurrentUser();
  if (!user || user.active_role !== "federation") return <p className="note">Для просмотра реестров выберите роль федерации.</p>;
  return <RegistryWorkspace key={user.id} />;
}

function RegistryWorkspace() {
  const [kind, setKind] = useState<Kind>("athletes");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Person | null>(null);
  const [history, setHistory] = useState<Record<string, Period[]> | null>(null);
  const [orgCode, setOrgCode] = useState("");
  const [orgName, setOrgName] = useState("");
  const [transferOrg, setTransferOrg] = useState("");
  const [transferDate, setTransferDate] = useState("");
  const [periodKind, setPeriodKind] = useState("participation");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [periodValue, setPeriodValue] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({ search, page: String(page) });
    api<Page>(`${kind}/?${query}`, { signal: controller.signal }).then((result) => { if (!controller.signal.aborted) { setData(result); setError(""); } }).catch((failure) => { if (!controller.signal.aborted) { setData(null); setError(failure.message); } });
    return () => controller.abort();
  }, [kind, search, page, revision]);
  useEffect(() => {
    if (!selected || kind !== "athletes") return;
    const controller = new AbortController();
    const kinds = ["participation", "disciplines", "organizations", "municipalities", "training-stages"];
    Promise.all(kinds.map((name) => api<Period[]>(`athletes/${selected.id}/history/${name}/`, { signal: controller.signal }))).then((values) => { if (!controller.signal.aborted) setHistory(Object.fromEntries(kinds.map((name, index) => [name, values[index]]))); }).catch((failure) => { if (!controller.signal.aborted) setError(failure.message); });
    return () => controller.abort();
  }, [selected, kind, revision]);
  async function createOrganization() {
    try { await api("organizations/", { method: "POST", body: JSON.stringify({ code: orgCode, name: orgName }) }); setOrgCode(""); setOrgName(""); setError(""); setRevision((n) => n + 1); } catch (failure) { setError(failure instanceof Error ? failure.message : "Ошибка сохранения"); }
  }
  async function transfer() {
    if (!selected) return;
    try { await api(`athletes/${selected.id}/transfer/`, { method: "POST", body: JSON.stringify({ organization: Number(transferOrg), effective_on: transferDate }) }); setError(""); setRevision((n) => n + 1); } catch (failure) { setError(failure instanceof Error ? failure.message : "Ошибка перевода"); }
  }
  async function addHistory() {
    if (!selected) return;
    const values: Record<string, string | number | null> = { starts_on: periodStart, ends_on: periodEnd || null };
    if (periodKind === "organizations") values.organization = Number(periodValue);
    if (periodKind === "disciplines") values.discipline = Number(periodValue);
    if (periodKind === "municipalities") values.municipality = periodValue;
    if (periodKind === "training-stages") values.stage = periodValue;
    try { await api(`athletes/${selected.id}/history/${periodKind}/`, { method: "POST", body: JSON.stringify(values) }); setError(""); setRevision((n) => n + 1); } catch (failure) { setError(failure instanceof Error ? failure.message : "Ошибка сохранения периода"); }
  }
  return <><header className="dashboard-head"><span className="kick">ФЕДЕРАЦИЯ · данные реестра</span><h1>Реестры</h1></header>
    <section className="blk"><h2><b>01</b><span>Поиск</span></h2><div className="btns">{(Object.keys(labels) as Kind[]).map((key) => <button key={key} className="btn" type="button" onClick={() => { setKind(key); setPage(1); setSelected(null); setHistory(null); }}>{labels[key]}</button>)}</div><label className="lb">Поиск<input className="inp" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></label></section>
    {error && <p className="note wn" role="alert">{error}</p>}
    <section className="blk"><h2><b>02</b><span>{labels[kind]}</span></h2>{!data ? <p className="note">{error ? "Данные не загружены." : "Загрузка…"}</p> : !data.results.length ? <p className="note">Записей не найдено.</p> : <div className="tw"><table><thead><tr><th>Имя / название</th><th>Организация / муниципалитет</th><th>Статус</th></tr></thead><tbody>{data.results.map((row) => <tr key={row.id}><td>{"full_name" in row ? <button className="workflow-link" type="button" onClick={() => { setHistory(null); setSelected(row); }}>{row.full_name}</button> : row.name}</td><td>{"full_name" in row ? row.organization ?? "Не указана" : row.municipality || "Не указан"}</td><td>{row.is_active ? "Активен" : "Неактивен"}</td></tr>)}</tbody></table></div>}<div className="btns"><button className="btn" type="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>Назад</button><span>Страница {page}</span><button className="btn" type="button" disabled={!data?.next} onClick={() => setPage(page + 1)}>Далее</button></div></section>
    {kind === "organizations" && <section className="blk"><h2><b>03</b><span>Новая организация</span></h2><label className="lb">Код<input className="inp" value={orgCode} onChange={(e) => setOrgCode(e.target.value)} /></label><label className="lb">Название<input className="inp" value={orgName} onChange={(e) => setOrgName(e.target.value)} /></label><button className="btn p" type="button" onClick={createOrganization}>Создать</button></section>}
    {selected && kind === "athletes" && <section className="blk"><h2><b>03</b><span>История · {selected.full_name}</span></h2>{history ? Object.entries(history).map(([name, periods]) => <div key={name}><h3>{({ participation: "Участие", disciplines: "Дисциплины", organizations: "Организации", municipalities: "Муниципалитеты", "training-stages": "Этапы подготовки" } as Record<string, string>)[name]}</h3>{periods.length ? <ul>{periods.map((p) => <li key={p.id}>{p.starts_on} — {p.ends_on ?? "по настоящее время"} · {p.organization_name || p.discipline_name || p.municipality || p.stage || "участие"}</li>)}</ul> : <p className="note">История не указана.</p>}</div>) : <p className="note">Загрузка истории…</p>}<h3>Добавить известный период</h3><label className="lb">Тип<select className="inp" value={periodKind} onChange={(e) => setPeriodKind(e.target.value)}><option value="participation">Участие</option><option value="disciplines">Дисциплина</option><option value="organizations">Организация</option><option value="municipalities">Муниципалитет</option><option value="training-stages">Этап подготовки</option></select></label><label className="lb">Начало<input className="inp" type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} /></label><label className="lb">Окончание, если известно<input className="inp" type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} /></label>{periodKind !== "participation" && <label className="lb">Значение (ID для организации и дисциплины)<input className="inp" value={periodValue} onChange={(e) => setPeriodValue(e.target.value)} /></label>}<button className="btn" type="button" onClick={addHistory}>Добавить период</button><h3>Перевод организации</h3><label className="lb">ID новой организации<input className="inp" type="number" value={transferOrg} onChange={(e) => setTransferOrg(e.target.value)} /></label><label className="lb">Дата перевода<input className="inp" type="date" value={transferDate} onChange={(e) => setTransferDate(e.target.value)} /></label><button className="btn p" type="button" onClick={transfer}>Сохранить перевод</button></section>}</>;
}
