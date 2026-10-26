"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, Discipline } from "@/lib/api";

export default function Home() {
  const [disciplines, setDisciplines] = useState<Discipline[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { api<Discipline[]>("disciplines/").then(setDisciplines).catch(() => setError("Каталог временно недоступен")); }, []);
  return <>
    <header className="hd"><div><span className="kick">Навигатор для новичка</span><h1><span>Пиши код.</span><span>Побеждай.</span><span>В&nbsp;Оренбуржье.</span></h1><p className="lead">Спортивное программирование: дисциплины региона и будущие соревнования. Начните с регистрации.</p><div className="cta"><Link className="btn p" href="/register">Зарегистрироваться →</Link><Link className="btn" href="/login">Войти</Link></div></div><aside className="soon" aria-label="Ближайшее соревнование"><small>Ближайшее соревнование</small><h4>Календарь формируется</h4><p>Опубликованные события появятся здесь после запуска календаря.</p></aside></header>
    <section className="blk" id="disciplines"><h2><b>01</b><span>Дисциплины</span></h2><div><p className="section-intro">Шесть дисциплин спортивного программирования</p>{error ? <div className="note wn" role="alert">{error}</div> : <div className="tw"><table><thead><tr><th>№</th><th>Дисциплина</th><th>Код</th></tr></thead><tbody>{disciplines.map((item, index) => <tr key={item.code}><td>{index + 1}</td><td>{item.name}</td><td className="m">{item.code}</td></tr>)}</tbody></table>{disciplines.length === 0 && <p className="empty">Загрузка каталога…</p>}</div>}</div></section>
  </>;
}
