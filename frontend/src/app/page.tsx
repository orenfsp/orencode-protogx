"use client";

import { Toast } from "@/components/Toast";
import { useCurrentUser } from "@/components/AppShell";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, Competition, Discipline } from "@/lib/api";

export default function Home() {
  const me = useCurrentUser();
  const [disciplines, setDisciplines] = useState<Discipline[] | null>(null);
  const [error, setError] = useState("");
  const [upcoming, setUpcoming] = useState<Competition | null>(null);
  const [calendarState, setCalendarState] = useState<"loading" | "ready" | "error">("loading");
  useEffect(() => {
    let current = true;
    api<Discipline[]>("disciplines/").then((items) => { if (current) setDisciplines(items); }).catch(() => { if (current) setError("Каталог временно недоступен"); });
    api<Competition[]>("competitions/").then((items) => {
      if (!current) return;
      const now = Date.now();
      const next = items.filter((item) => item.state === "published" && Date.parse(item.starts_at) >= now)
        .sort((a, b) => Date.parse(a.starts_at) - Date.parse(b.starts_at))[0];
      setUpcoming(next ?? null);
      setCalendarState("ready");
    }).catch(() => { if (current) setCalendarState("error"); });
    return () => { current = false; };
  }, []);
  return <>
    <header className="hd"><div><span className="kick">Навигатор для новичка</span><h1><span>Пиши код.</span><span>Побеждай.</span><span>В&nbsp;Оренбуржье.</span></h1><p className="lead">Спортивное программирование: дисциплины региона и будущие соревнования. Начните с регистрации.</p><div className="cta">{me ? <Link className="btn p" href="/dashboard">Открыть кабинет</Link> : <><Link className="btn p" href="/register">Зарегистрироваться →</Link><Link className="btn" href="/login">Войти</Link></>}</div></div><aside className="soon" aria-label="Ближайшее соревнование"><small>Ближайшее соревнование</small>{calendarState === "loading" ? <p role="status">Загрузка календаря…</p> : calendarState === "error" ? <Toast>Календарь временно недоступен.</Toast> : upcoming ? <><h4><Link className="workflow-link" href={`/competitions/${upcoming.id}`}>{upcoming.title}</Link></h4><p>{new Date(upcoming.starts_at).toLocaleDateString("ru-RU")} · {upcoming.discipline_name}</p></> : <><h4>Предстоящих соревнований пока нет</h4><p>Следите за обновлениями в календаре.</p></>}</aside></header>
    <section className="blk" id="disciplines"><h2><b>01</b><span>Дисциплины</span></h2><div><p className="section-intro">Шесть дисциплин спортивного программирования</p>{error ? <Toast>{error}</Toast> : !disciplines ? <p className="empty" role="status">Загрузка каталога…</p> : disciplines.length === 0 ? <p className="empty">Дисциплин пока нет.</p> : <div className="tw"><table><thead><tr><th>№</th><th>Дисциплина</th><th>Код</th></tr></thead><tbody>{disciplines.map((item, index) => <tr key={item.code}><td>{index + 1}</td><td>{item.name}</td><td className="m">{item.code}</td></tr>)}</tbody></table></div>}</div></section>
  </>;
}
