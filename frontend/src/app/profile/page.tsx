"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useCurrentUser } from "@/components/AppShell";
import { api } from "@/lib/api";

type Profile = { full_name: string; date_of_birth: string; organization: string; municipality: string; training_started_year: number | null; disciplines: string[]; coaches: { coach__full_name: string; discipline__name: string }[]; guardians: { full_name: string; relationship: string; confirmation_status: string }[]; antidoping_completed_on: string | null; antidoping_certificate_url: string };

function ProfileForm() {
  const [data, setData] = useState<Profile | null>(null);
  const [when, setWhen] = useState("");
  const [url, setUrl] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const abort = new AbortController();
    void api<Profile>("profile/", { signal: abort.signal }).then((value) => { if (!abort.signal.aborted) { setData(value); setWhen(value.antidoping_completed_on ?? ""); setUrl(value.antidoping_certificate_url); } }).catch(() => { if (!abort.signal.aborted) setMessage("Не удалось загрузить профиль"); });
    return () => abort.abort();
  }, []);
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage("");
    try { await api("profile/", { method: "PATCH", body: JSON.stringify({ antidoping_completed_on: when || null, antidoping_certificate_url: url }) }); setMessage("Отметка РУСАДА сохранена"); }
    catch (cause) { setMessage(cause instanceof Error ? cause.message : "Не удалось сохранить отметку"); }
    finally { setBusy(false); }
  }
  return <>
    {message && <p role="status">{message}</p>}
    {!data ? <p>Загрузка профиля…</p> : <>
      <section className="blk"><h2><b>01</b><span>Профиль</span></h2><div><h3>{data.full_name}</h3><p>Дата рождения: {data.date_of_birth}</p><p>{data.municipality} · {data.organization}</p><p>Год начала занятий: {data.training_started_year ?? "Не указан"}</p><p>Дисциплины: {data.disciplines.join(", ") || "Не указаны"}</p><ul>{data.coaches.map((coach, index) => <li key={index}>{coach.coach__full_name} · {coach.discipline__name}</li>)}</ul><Link className="btn" href="/qualifications">Текущий разряд и срок действия</Link>{data.guardians.map((guardian, index) => <p key={index}>Представитель: {guardian.full_name} · {guardian.relationship} · {guardian.confirmation_status === "verified" ? "Проверен" : "Ожидает проверки"}</p>)}</div></section>
      <section className="blk"><h2><b>02</b><span>Антидопинг</span></h2><div><p><a className="workflow-link" href="https://rusada.ru/" target="_blank" rel="noreferrer">Официальные материалы РУСАДА</a>. Отметка сохраняется со слов спортсмена; подлинность сертификата автоматически не проверяется.</p><form className="workflow-form" onSubmit={save}><label className="lb">Дата прохождения курса<input className="inp" type="date" value={when} onChange={(event) => setWhen(event.target.value)} /></label><label className="lb">Ссылка на сертификат<input className="inp" type="url" value={url} onChange={(event) => setUrl(event.target.value)} /></label><button className="btn p" disabled={busy}>Сохранить отметку РУСАДА</button></form></div></section>
    </>}
  </>;
}

export default function Profile() {
  const me = useCurrentUser();
  return <><header className="dashboard-head"><Link className="workflow-link" href="/dashboard">← Кабинет</Link><h1>Мой профиль</h1></header>{me?.active_role === "athlete" && <ProfileForm key={`${me.id}:${me.active_role}`} />}</>;
}
