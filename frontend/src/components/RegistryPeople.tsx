"use client";

import { Toast } from "@/components/Toast";

import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { RegistryOptions } from "@/components/RegistryOptions";

type Kind = "athletes" | "coaches" | "judges";
type Person = { id: number; full_name: string };
type Context = { ranks: Record<string, string | boolean | null>[]; categories: Record<string, string | boolean | null>[]; coach_links: Record<string, string | boolean | null>[]; assignments: Record<string, string | boolean | null>[] };
type Staff = { organization: number | null; disciplines: number[] };
const roles = { athletes: "athlete", coaches: "coach", judges: "judge" } as const;

function contextText(row: Record<string, string | boolean | null>) {
  const validity: Record<string, string> = { active: "Действует", expiring: "Скоро истекает", expired: "Срок истёк" };
  const relationshipStatus: Record<string, string> = { pending: "Ожидает подтверждения", confirmed: "Подтверждена", rejected: "Отклонена" };
  return Object.entries(row).map(([key, value]) => {
    if (key === "current") return value ? "Текущая запись" : "История";
    if (key === "validity") return validity[String(value)] ?? String(value ?? "");
    if (key === "status") return relationshipStatus[String(value)] ?? String(value ?? "");
    return String(value ?? "");
  }).join(" · ");
}

export function RegistryPeople({ kind, selectedId, options, onChange, onDenied }: { kind: Kind; selectedId: number | null; options: RegistryOptions | null; onChange: () => void; onDenied: () => void }) {
  const role = roles[kind];
  const [search, setSearch] = useState("");
  const [candidates, setCandidates] = useState<Person[]>([]);
  const [candidate, setCandidate] = useState("");
  const [organization, setOrganization] = useState("");
  const [context, setContext] = useState<Context | null>(null);
  const [staff, setStaff] = useState<Staff | null>(null);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const writes = useRef(new Set<AbortController>());
  useEffect(() => { const pending = writes.current; return () => { for (const c of pending) c.abort(); }; }, []);
  async function mutate(path: string, method: string, payload: object) {
    const controller = new AbortController(); writes.current.add(controller);
    try { await api(path, { method, body: JSON.stringify(payload), signal: controller.signal }); return !controller.signal.aborted; }
    catch (e) { if (!controller.signal.aborted) { if (e instanceof ApiError && (e.status === 401 || e.status === 403)) onDenied(); else setError(e instanceof Error ? e.message : "Ошибка сохранения"); } return false; }
    finally { writes.current.delete(controller); }
  }
  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams({ role, search, page: String(page) });
    api<{ results: Person[]; next: string | null }>(`registry/eligible-users/?${query}`, { signal: controller.signal }).then((data) => { if (!controller.signal.aborted) { setCandidates(data.results); setHasNext(!!data.next); } }).catch((e) => { if (!controller.signal.aborted) { if (e instanceof ApiError && (e.status === 401 || e.status === 403)) onDenied(); else setError(e.message); } });
    return () => controller.abort();
  }, [role, search, revision, page, onDenied]);
  useEffect(() => {
    if (!selectedId) return;
    const controller = new AbortController();
    api<Context>(`registry/profiles/${role}/${selectedId}/context/`, { signal: controller.signal }).then((data) => { if (!controller.signal.aborted) setContext(data); }).catch((e) => { if (!controller.signal.aborted) { if (e instanceof ApiError && (e.status === 401 || e.status === 403)) onDenied(); else setError(e.message); } });
    if (role !== "athlete") api<Staff>(`registry/profiles/${role}/${selectedId}/staff/`, { signal: controller.signal }).then((data) => { if (!controller.signal.aborted) setStaff(data); }).catch((e) => { if (!controller.signal.aborted) { if (e instanceof ApiError && (e.status === 401 || e.status === 403)) onDenied(); else setStaff(null); } });
    return () => controller.abort();
  }, [selectedId, role, revision, onDenied]);
  async function create() {
    if (await mutate(`registry/profiles/${role}/`, "POST", { user: Number(candidate), organization: organization ? Number(organization) : null })) { setCandidate(""); setError(""); setRevision((n) => n + 1); onChange(); }
  }
  async function saveStaff() {
    if (!staff || !selectedId) return;
    if (await mutate(`registry/profiles/${role}/${selectedId}/staff/`, "PATCH", staff)) { setError(""); setRevision((n) => n + 1); onChange(); }
  }
  return <><section className="blk"><h2><b>04</b><span>Создать профиль</span></h2><label className="lb">Поиск пользователя<input className="inp" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); setCandidate(""); }} /></label><label className="lb">Существующий пользователь<select className="inp" value={candidate} onChange={(e) => setCandidate(e.target.value)}><option value="">Выберите</option>{candidates.map((item) => <option value={item.id} key={item.id}>{item.full_name}</option>)}</select></label><div className="btns"><button className="btn" disabled={page === 1} onClick={() => { setCandidate(""); setPage(page - 1); }}>Предыдущие пользователи</button><span>Страница {page}</span><button className="btn" disabled={!hasNext} onClick={() => { setCandidate(""); setPage(page + 1); }}>Следующие пользователи</button></div><label className="lb">Организация профиля<select className="inp" value={organization} onChange={(e) => setOrganization(e.target.value)}><option value="">Не указана</option>{options?.organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><p className="note">Профиль создаётся для пользователя с уже назначенной ролью и действующим согласием. Для несовершеннолетних требуется подтверждённый представитель.</p><button className="btn" disabled={!candidate} onClick={create}>Создать профиль</button></section>{error && <Toast>{error}</Toast>}
    {selectedId && <section className="blk"><h2><b>05</b><span>Связи и квалификации</span></h2>{!context ? <p className="note">Загрузка…</p> : <div>{Object.entries({ ranks: "Разряды", categories: "Судейские категории", coach_links: "Связи тренера и спортсмена", assignments: "Судейские назначения" }).map(([key, label]) => <div key={key}><h3>{label}</h3>{context[key as keyof Context].length ? <ul>{context[key as keyof Context].map((row, index) => <li key={index}>{contextText(row)}</li>)}</ul> : <p className="note">Нет записей.</p>}</div>)}</div>}{staff && <div><h3>Профиль специалиста</h3><label className="lb">Организация<select className="inp" value={staff.organization ?? ""} onChange={(e) => setStaff({ ...staff, organization: e.target.value ? Number(e.target.value) : null })}><option value="">Не указана</option>{options?.organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><fieldset><legend>Дисциплины</legend>{options?.disciplines.map((item) => <label key={item.id}><input type="checkbox" checked={staff.disciplines.includes(item.id)} onChange={(e) => setStaff({ ...staff, disciplines: e.target.checked ? [...staff.disciplines, item.id] : staff.disciplines.filter((id) => id !== item.id) })} /> {item.name}</label>)}</fieldset><button className="btn" onClick={saveStaff}>Сохранить профиль специалиста</button></div>}</section>}</>;
}
