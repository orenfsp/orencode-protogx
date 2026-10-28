"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useCurrentUser } from "@/components/AppShell";
import { useRegistryOptions } from "@/components/RegistryOptions";
import { RegistryPeople } from "@/components/RegistryPeople";
import { api, ApiError } from "@/lib/api";

type Person = { id: number; full_name: string; date_of_birth: string | null; organization: string | null; is_active: boolean };
type Org = { id: number; name: string; municipality: string; code: string; organization_type: string; contact: string; is_active: boolean };
type Page = { count: number; next: string | null; previous: string | null; results: (Person | Org)[] };
type Period = { id: number; starts_on: string; ends_on: string | null; organization?: number; discipline?: number; organization_name?: string; discipline_name?: string; municipality?: string; stage?: string };
type PeriodAudit = { actor: string; action: string; created_at: string; before: unknown; after: unknown };
const labels = { athletes: "Спортсмены", coaches: "Тренеры", judges: "Судьи", organizations: "Организации" } as const;
type Kind = keyof typeof labels;

export default function RegistryPage() {
  const user = useCurrentUser();
  if (!user || user.active_role !== "federation") return <p className="note">Для просмотра реестров выберите роль федерации.</p>;
  return <RegistryWorkspace key={user.id} />;
}

function RegistryWorkspace() {
  const { options, optionsError, optionsForbidden } = useRegistryOptions();
  const pendingWrites = useRef(new Set<AbortController>());
  useEffect(() => {
    const pending = pendingWrites.current;
    return () => { for (const controller of pending) controller.abort(); };
  }, []);
  async function write(path: string, payload: object, method = "POST") {
    const controller = new AbortController();
    pendingWrites.current.add(controller);
    try { await api(path, { method, body: JSON.stringify(payload), signal: controller.signal }); return !controller.signal.aborted; }
    catch (failure) { if (!controller.signal.aborted) { if (failure instanceof ApiError && (failure.status === 401 || failure.status === 403)) setDenied(true); else setError(failure instanceof ApiError && failure.status === 409 ? "Период изменён другим пользователем. Обновите историю и повторите исправление." : failure instanceof Error ? failure.message : "Ошибка сохранения"); } return false; }
    finally { pendingWrites.current.delete(controller); }
  }
  const [kind, setKind] = useState<Kind>("athletes");
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState("");
  const [orgFilter, setOrgFilter] = useState("");
  const [disciplineFilter, setDisciplineFilter] = useState("");
  const [municipalityFilter, setMunicipalityFilter] = useState("");
  const [organizationType, setOrganizationType] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<Page | null>(null);
  const [error, setError] = useState("");
  const [denied, setDenied] = useState(false);
  const setDeniedTrue = useCallback(() => setDenied(true), [setDenied]);
  useEffect(() => { if (denied || optionsForbidden) for (const controller of pendingWrites.current) controller.abort(); }, [denied, optionsForbidden]);
  const [selected, setSelected] = useState<Person | null>(null);
  const [selectedOrg, setSelectedOrg] = useState<Org | null>(null);
  const [editName, setEditName] = useState("");
  const [editBirth, setEditBirth] = useState("");
  const [history, setHistory] = useState<Record<string, Period[]> | null>(null);
  const [orgCode, setOrgCode] = useState("");
  const [orgName, setOrgName] = useState("");
  const [transferOrg, setTransferOrg] = useState("");
  const [transferDate, setTransferDate] = useState("");
  const [periodKind, setPeriodKind] = useState("participation");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [periodValue, setPeriodValue] = useState("");
  const [correctionTrigger, setCorrectionTrigger] = useState<HTMLButtonElement | null>(null);
  const [correction, setCorrection] = useState<{ kind: string; period: Period } | null>(null);
  useEffect(() => {
    if (correction) document.getElementById("correction-reason")?.focus();
  }, [correction]);
  const [auditHistory, setAuditHistory] = useState<PeriodAudit[] | null>(null);
  const [closing, setClosing] = useState<{ kind: string; period: Period } | null>(null);
  const [closeDate, setCloseDate] = useState("");
  const [correctStart, setCorrectStart] = useState("");
  const [correctEnd, setCorrectEnd] = useState("");
  const [correctReason, setCorrectReason] = useState("");
  const [correctValue, setCorrectValue] = useState("");
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const pending = pendingWrites.current;
    return () => { for (const controller of pending) controller.abort(); };
  }, [kind, selected?.id, selectedOrg?.id, correction?.period.id]);
  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({ search, page: String(page) });
    if (kind !== "organizations") {
      if (activeFilter) query.set("active", activeFilter);
      if (orgFilter) query.set("organization", orgFilter);
      if (disciplineFilter) query.set("discipline", disciplineFilter);
      if (municipalityFilter) query.set("municipality", municipalityFilter);
    } else {
      if (activeFilter) query.set("active", activeFilter);
      if (municipalityFilter) query.set("municipality", municipalityFilter);
      if (organizationType) query.set("organization_type", organizationType);
    }
    api<Page>(`${kind}/?${query}`, { signal: controller.signal }).then((result) => { if (!controller.signal.aborted) { setData(result); setError(""); } }).catch((failure) => { if (!controller.signal.aborted) { setData(null); if (failure instanceof ApiError && (failure.status === 401 || failure.status === 403)) setDenied(true); else setError(failure.message); } });
    return () => controller.abort();
  }, [kind, search, page, revision, activeFilter, orgFilter, disciplineFilter, municipalityFilter, organizationType]);
  useEffect(() => {
    if (!selected || kind !== "athletes") return;
    const controller = new AbortController();
    const kinds = ["participation", "disciplines", "organizations", "municipalities", "training-stages"];
    Promise.all(kinds.map((name) => api<Period[]>(`athletes/${selected.id}/history/${name}/`, { signal: controller.signal }))).then((values) => { if (!controller.signal.aborted) setHistory(Object.fromEntries(kinds.map((name, index) => [name, values[index]]))); }).catch((failure) => { if (!controller.signal.aborted) { if (failure instanceof ApiError && (failure.status === 401 || failure.status === 403)) setDenied(true); else setError(failure.message); } });
    return () => controller.abort();
  }, [selected, kind, revision]);
  useEffect(() => {
    if (!selected || !correction) return;
    const controller = new AbortController();
    api<PeriodAudit[]>(`athletes/${selected.id}/history/${correction.kind}/${correction.period.id}/audit/`, { signal: controller.signal }).then((rows) => { if (!controller.signal.aborted) setAuditHistory(rows); }).catch((failure) => { if (!controller.signal.aborted) { if (failure instanceof ApiError && (failure.status === 401 || failure.status === 403)) setDenied(true); else setError(failure.message); } });
    return () => controller.abort();
  }, [selected, correction]);
  async function createOrganization() {
    if (await write("organizations/", { code: orgCode, name: orgName })) { setOrgCode(""); setOrgName(""); setError(""); setRevision((n) => n + 1); }
  }
  async function saveOrganization() {
    if (!selectedOrg) return;
    const { name, municipality, organization_type, contact, is_active } = selectedOrg;
    if (await write(`organizations/${selectedOrg.id}/`, { name, municipality, organization_type, contact, is_active }, "PATCH")) { setError(""); setRevision((n) => n + 1); }
  }
  async function savePerson() {
    if (!selected || kind === "organizations") return;
    if (await write(`${kind}/${selected.id}/`, { full_name: editName, date_of_birth: editBirth || null }, "PATCH")) { setSelected({ ...selected, full_name: editName, date_of_birth: editBirth || null }); setError(""); setRevision((n) => n + 1); }
  }
  async function transfer() {
    if (!selected) return;
    if (await write(`athletes/${selected.id}/transfer/`, { organization: Number(transferOrg), effective_on: transferDate })) { setError(""); setRevision((n) => n + 1); }
  }
  async function addHistory() {
    if (!selected) return;
    const values: Record<string, string | number | null> = { starts_on: periodStart, ends_on: periodEnd || null };
    if (periodKind === "organizations") values.organization = Number(periodValue);
    if (periodKind === "disciplines") values.discipline = Number(periodValue);
    if (periodKind === "municipalities") values.municipality = periodValue;
    if (periodKind === "training-stages") values.stage = periodValue;
    if (await write(`athletes/${selected.id}/history/${periodKind}/`, values)) { setError(""); setRevision((n) => n + 1); }
  }
  function rememberCorrectionTrigger(button: HTMLButtonElement) { setCorrectionTrigger(button); }
  function cancelCorrection() { setCorrection(null); correctionTrigger?.focus(); }
  async function correctHistory() {
    if (!selected || !correction) return;
    const p = correction.period;
    const expected: Record<string, string | number | null> = { starts_on: p.starts_on, ends_on: p.ends_on };
    for (const key of ["organization", "discipline", "municipality", "stage"] as const) if (p[key] !== undefined) expected[key] = p[key] ?? null;
    const corrected: Record<string, string | number | null> = { ...expected, starts_on: correctStart, ends_on: correctEnd || null };
    if (correction.kind === "organizations") corrected.organization = Number(correctValue);
    if (correction.kind === "disciplines") corrected.discipline = Number(correctValue);
    if (correction.kind === "municipalities") corrected.municipality = correctValue;
    if (correction.kind === "training-stages") corrected.stage = correctValue;
    if (await write(`athletes/${selected.id}/history/${correction.kind}/${p.id}/correct/`, { expected, corrected, reason: correctReason })) { setCorrection(null); setCorrectReason(""); setError(""); setRevision((n) => n + 1); }
  }
  async function closeHistory() {
    if (!selected || !closing) return;
    if (await write(`athletes/${selected.id}/history/${closing.kind}/${closing.period.id}/close/`, { ends_on: closeDate })) { setClosing(null); setCloseDate(""); setError(""); setRevision((n) => n + 1); }
  }
  if (denied || optionsForbidden) return <p className="note wn" role="alert">Доступ к реестру недоступен. Войдите снова или выберите роль федерации.</p>;
  return <div className="registry-workspace"><header className="dashboard-head"><span className="kick">ФЕДЕРАЦИЯ · данные реестра</span><h1>Реестры</h1></header>
    <section className="blk"><h2><b>01</b><span>Поиск</span></h2><div className="btns">{(Object.keys(labels) as Kind[]).map((key) => <button key={key} className="btn" type="button" onClick={() => { setError(""); setKind(key); setPage(1); setSelected(null); setSelectedOrg(null); setCorrection(null); setHistory(null); }}>{labels[key]}</button>)}</div><label className="lb">Поиск<input className="inp" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} /></label>{kind !== "organizations" && <div className="form-grid"><label className="lb">Статус<select className="inp" value={activeFilter} onChange={(e) => { setActiveFilter(e.target.value); setPage(1); }}><option value="">Все</option><option value="true">Активные</option><option value="false">Неактивные</option></select></label><label className="lb">Организация<select className="inp" value={orgFilter} onChange={(e) => { setOrgFilter(e.target.value); setPage(1); }} disabled={!options}><option value="">Все</option>{options?.organizations.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label className="lb">Дисциплина<select className="inp" value={disciplineFilter} onChange={(e) => { setDisciplineFilter(e.target.value); setPage(1); }} disabled={!options}><option value="">Все</option>{options?.disciplines.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label><label className="lb">Муниципалитет<select className="inp" value={municipalityFilter} onChange={(e) => { setMunicipalityFilter(e.target.value); setPage(1); }} disabled={!options}><option value="">Все</option>{options?.municipalities.map((name) => <option value={name} key={name}>{name}</option>)}</select></label></div>}</section>
    {kind === "organizations" && <section className="blk"><h2><b>02</b><span>Фильтры</span></h2><div className="form-grid">
      <label className="lb">Статус организации<select className="inp" value={activeFilter} onChange={(e) => { setActiveFilter(e.target.value); setPage(1); }}><option value="">Все</option><option value="true">Активные</option><option value="false">Неактивные</option></select></label>
      <label className="lb">Муниципалитет в фильтре<select className="inp" value={municipalityFilter} onChange={(e) => { setMunicipalityFilter(e.target.value); setPage(1); }} disabled={!options}><option value="">Все</option>{options?.municipalities.map((name) => <option value={name} key={name}>{name}</option>)}</select></label>
      <label className="lb">Тип организации<input className="inp" value={organizationType} onChange={(e) => { setOrganizationType(e.target.value); setPage(1); }} /></label>
    </div></section>}
    {(optionsError || (error && !correction)) && <p className="note wn" role="alert">{optionsError || error}</p>}
    <section className="blk"><h2><b>{kind === "organizations" ? "03" : "02"}</b><span>{labels[kind]}</span></h2>{!data ? <p className="note">{error ? "Данные не загружены." : "Загрузка…"}</p> : !data.results.length ? <p className="note">Записей не найдено.</p> : <div className="tw"><table><thead><tr><th>Имя / название</th><th>Организация / муниципалитет</th><th>Статус</th></tr></thead><tbody>{data.results.map((row) => <tr key={row.id}><td>{"full_name" in row ? <button className="workflow-link" type="button" onClick={() => { setError(""); setHistory(null); setCorrection(null); setClosing(null); setSelected(row); setEditName(row.full_name); setEditBirth(row.date_of_birth ?? ""); }}>{row.full_name}</button> : <button className="workflow-link" type="button" onClick={() => { setSelectedOrg(row); }}>{row.name}</button>}</td><td>{"full_name" in row ? row.organization ?? "Не указана" : row.municipality || "Не указан"}</td><td>{row.is_active ? "Активен" : "Неактивен"}</td></tr>)}</tbody></table></div>}<div className="btns"><button className="btn" type="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>Назад</button><span>Страница {page}</span><button className="btn" type="button" disabled={!data?.next} onClick={() => setPage(page + 1)}>Далее</button></div></section>
    {selected && kind !== "organizations" && <section className="blk"><h2><b>03</b><span>Профиль · {selected.full_name}</span></h2><label className="lb">Имя<input className="inp" value={editName} onChange={(e) => setEditName(e.target.value)} /></label><label className="lb">Дата рождения<input className="inp" type="date" value={editBirth} onChange={(e) => setEditBirth(e.target.value)} /></label><button className="btn" type="button" onClick={savePerson}>Сохранить профиль</button></section>}
    {kind !== "organizations" && <RegistryPeople key={`${kind}-${selected?.id ?? "none"}`} kind={kind} selectedId={selected?.id ?? null} options={options} onDenied={setDeniedTrue} onChange={() => setRevision((n) => n + 1)} />}
    {kind === "organizations" && selectedOrg && <section className="blk"><h2><b>04</b><span>Организация · {selectedOrg.code}</span></h2><label className="lb">Название<input className="inp" value={selectedOrg.name} onChange={(e) => setSelectedOrg({ ...selectedOrg, name: e.target.value })} /></label><label className="lb">Тип<input className="inp" value={selectedOrg.organization_type} onChange={(e) => setSelectedOrg({ ...selectedOrg, organization_type: e.target.value })} /></label><label className="lb">Муниципалитет организации<input className="inp" value={selectedOrg.municipality} onChange={(e) => setSelectedOrg({ ...selectedOrg, municipality: e.target.value })} /></label><label className="lb">Контакт<input className="inp" value={selectedOrg.contact} onChange={(e) => setSelectedOrg({ ...selectedOrg, contact: e.target.value })} /></label><label className="lb"><input type="checkbox" checked={selectedOrg.is_active} onChange={(e) => setSelectedOrg({ ...selectedOrg, is_active: e.target.checked })} /> Активна</label><button className="btn" type="button" onClick={saveOrganization}>Сохранить организацию</button></section>}
    {kind === "organizations" && <section className="blk"><h2><b>05</b><span>Новая организация</span></h2><label className="lb">Код<input className="inp" value={orgCode} onChange={(e) => setOrgCode(e.target.value)} /></label><label className="lb">Название<input className="inp" value={orgName} onChange={(e) => setOrgName(e.target.value)} /></label><button className="btn p" type="button" onClick={createOrganization}>Создать</button></section>}
    {selected && kind === "athletes" && <section className="blk"><h2><b>06</b><span>История · {selected.full_name}</span></h2>{history ? Object.entries(history).map(([name, periods]) => <div key={name}><h3>{({ participation: "Участие", disciplines: "Дисциплины", organizations: "Организации", municipalities: "Муниципалитеты", "training-stages": "Этапы подготовки" } as Record<string, string>)[name]}</h3>{periods.length ? <ul>{periods.map((p) => <li key={p.id}>{p.starts_on} — {p.ends_on ?? "по настоящее время"} · {p.organization_name || p.discipline_name || p.municipality || p.stage || "участие"} <button className="btn" type="button" onClick={(event) => { rememberCorrectionTrigger(event.currentTarget); setError(""); setAuditHistory(null); setCorrection({ kind: name, period: p }); setCorrectStart(p.starts_on); setCorrectEnd(p.ends_on ?? ""); setCorrectValue(String(p.organization ?? p.discipline ?? p.municipality ?? p.stage ?? "")); setCorrectReason(""); }}>Исправить</button>{p.ends_on === null && name !== "organizations" && <button className="btn" type="button" onClick={() => { setClosing({ kind: name, period: p }); setCloseDate(""); }}>Завершить</button>}</li>)}</ul> : <p className="note">История не указана.</p>}</div>) : <p className="note">Загрузка истории…</p>}{closing && <div><h3>Завершить период</h3><label className="lb">Дата окончания<input className="inp" type="date" value={closeDate} onChange={(e) => setCloseDate(e.target.value)} /></label><button className="btn" type="button" onClick={closeHistory}>Сохранить окончание</button></div>}{correction && <div onKeyDown={(event) => { if (event.key === "Escape") cancelCorrection(); }}><h3>Исправить период</h3>{error && <p id="correction-error" className="note wn" role="alert">{error}</p>}{auditHistory ? <div><h4>Журнал изменений</h4>{auditHistory.length ? <ul>{auditHistory.map((item, index) => <li key={index}>{item.created_at} · {item.actor} · {item.action} · {JSON.stringify(item.before)} → {JSON.stringify(item.after)}</li>)}</ul> : <p className="note">Записей аудита нет.</p>}</div> : <p className="note">Загрузка журнала…</p>}<label className="lb">Исправленное начало<input className="inp" type="date" value={correctStart} onChange={(e) => setCorrectStart(e.target.value)} /></label><label className="lb">Исправленное окончание<input className="inp" type="date" value={correctEnd} onChange={(e) => setCorrectEnd(e.target.value)} /></label>{(correction.kind === "organizations" || correction.kind === "disciplines") ? <label className="lb">Исправленное значение<select className="inp" value={correctValue} onChange={(e) => setCorrectValue(e.target.value)}><option value="">Выберите</option>{options?.[correction.kind].map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label> : correction.kind !== "participation" && <label className="lb">Исправленное значение<input className="inp" list={correction.kind === "municipalities" ? "municipality-options" : undefined} value={correctValue} onChange={(e) => setCorrectValue(e.target.value)} /></label>}<label className="lb">Причина исправления<input className="inp" id="correction-reason" aria-required="true" aria-invalid={Boolean(error)} aria-describedby={error ? "correction-error" : undefined} value={correctReason} onChange={(e) => setCorrectReason(e.target.value)} /></label><button className="btn" type="button" onClick={correctHistory}>Сохранить исправление</button></div>}<h3>Добавить известный период</h3><label className="lb">Тип<select className="inp" value={periodKind} onChange={(e) => setPeriodKind(e.target.value)}><option value="participation">Участие</option><option value="disciplines">Дисциплина</option><option value="organizations">Организация</option><option value="municipalities">Муниципалитет</option><option value="training-stages">Этап подготовки</option></select></label><label className="lb">Начало<input className="inp" type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} /></label><label className="lb">Окончание, если известно<input className="inp" type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} /></label>{(periodKind === "organizations" || periodKind === "disciplines") ? <label className="lb">{periodKind === "organizations" ? "Организация" : "Дисциплина"}<select className="inp" value={periodValue} onChange={(e) => setPeriodValue(e.target.value)} disabled={!options}><option value="">Выберите</option>{options?.[periodKind].map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label> : periodKind !== "participation" && <label className="lb">{periodKind === "municipalities" ? "Муниципалитет" : "Этап подготовки"}<input className="inp" list={periodKind === "municipalities" ? "municipality-options" : undefined} value={periodValue} onChange={(e) => setPeriodValue(e.target.value)} /></label>}<datalist id="municipality-options">{options?.municipalities.map((name) => <option key={name} value={name} />)}</datalist><button className="btn" type="button" onClick={addHistory}>Добавить период</button><h3>Перевод организации</h3><label className="lb">Новая организация<select className="inp" value={transferOrg} onChange={(e) => setTransferOrg(e.target.value)} disabled={!options}><option value="">Выберите</option>{options?.organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label className="lb">Дата перевода<input className="inp" type="date" value={transferDate} onChange={(e) => setTransferDate(e.target.value)} /></label><button className="btn p" type="button" onClick={transfer}>Сохранить перевод</button></section>}</div>;
}
