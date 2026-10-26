"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, Me, Role } from "@/lib/api";

const roleName: Record<Role, string> = { federation: "Федерация", athlete: "Спортсмен", coach: "Тренер", judge: "Судья" };

export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [dark, setDark] = useState(false);
  const [roleError, setRoleError] = useState("");

  useEffect(() => {
    const frame = requestAnimationFrame(() => setDark(localStorage.getItem("fsp-theme") === "dark"));
    return () => cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    api<Me>("auth/me/").then(setMe).catch(() => setMe(null));
  }, [path]);

  async function switchRole(role: Role) {
    try {
      setRoleError("");
      setMe(await api<Me>("auth/active-role/", { method: "POST", body: JSON.stringify({ role }) }));
    } catch (error) { setRoleError(error instanceof Error ? error.message : "Ошибка выбора роли"); }
  }

  async function signOut() {
    await api<void>("auth/logout/", { method: "POST" });
    setMe(null);
    router.push("/");
    router.refresh();
  }

  return <>
    <input type="checkbox" id="th" aria-label="Тёмная тема" checked={dark} onChange={(event) => { setDark(event.target.checked); localStorage.setItem("fsp-theme", event.target.checked ? "dark" : "light"); }} />
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
      <symbol id="i-home" viewBox="0 0 24 24"><path d="M3 11l9-8 9 8M5 10v10h14V10M10 20v-6h4v6" /></symbol>
      <symbol id="i-users" viewBox="0 0 24 24"><circle cx="9" cy="8" r="3.5" /><path d="M2.5 20c0-3.6 3-6 6.5-6s6.5 2.4 6.5 6M16 4.7a3.5 3.5 0 010 6.6M18 14.3c2.2.7 3.5 2.6 3.5 5.7" /></symbol>
      <symbol id="i-cal" viewBox="0 0 24 24"><rect x="3.5" y="5" width="17" height="15.5" /><path d="M3.5 10h17M8 3v4M16 3v4" /></symbol>
      <symbol id="i-dots" viewBox="0 0 24 24"><path d="M6 12h.01M12 12h.01M18 12h.01" /></symbol>
    </svg>
    <div className="lay">
      <aside className="idx">
        <Link className="logo" href="/"><i>ФСП</i><span>Оренбургская<br />область</span></Link>
        <nav aria-label="Разделы">
          <Link className={path === "/" ? "on" : ""} href="/"><b>01</b>Главная</Link>
          <Link href="/#disciplines"><b>02</b>Дисциплины</Link>
          <Link href="/competitions"><b>03</b>Календарь</Link>
          <Link href="/dashboard"><b>04</b>Кабинет</Link>
        </nav>
        <div className="rb">
          {me ? <>
            <div className="menu" aria-label="Роль"><div className="a">{me.active_role ? roleName[me.active_role] : "Выбор роли"}</div>{me.roles.map((role) => <button type="button" key={role} className={me.active_role === role ? "a" : ""} onClick={() => switchRole(role)} aria-pressed={me.active_role === role}>{roleName[role]}</button>)}</div>
            {roleError && <p role="alert">{roleError}</p>}
            <div className="rbtn"><span>{me.full_name}<small>Роль: {me.active_role ? roleName[me.active_role] : "не выбрана"}</small></span></div>
            <button type="button" className="tgl" onClick={signOut}>Выйти</button>
          </> : <div className="rbtn"><span>Гость<small><Link href="/login">Войти</Link> · <Link href="/register">Регистрация</Link></small></span></div>}
          <label className="tgl" htmlFor="th"><span className="t-l">Тёмная тема</span><span className="t-d">Светлая тема</span></label>
          <small>Платформа ФСП Оренбургской области</small>
        </div>
      </aside>
      <main className="main" id="top">{children}<footer>ФСП Оренбургская область · Данные демонстрации вымышлены</footer></main>
    </div>
    <nav className="mobtab" aria-label="Основная навигация"><Link className={path === "/" ? "on" : ""} href="/"><svg className="ic"><use href="#i-home" /></svg>Главная</Link><Link href="/#disciplines"><svg className="ic"><use href="#i-users" /></svg>Дисциплины</Link><Link href="/competitions"><svg className="ic"><use href="#i-cal" /></svg>Календарь</Link><Link href="/dashboard"><svg className="ic"><use href="#i-dots" /></svg>Кабинет</Link></nav>
  </>;
}
