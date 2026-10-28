"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useRef, useState } from "react";
import { api, Me, Role } from "@/lib/api";

const roleName: Record<Role, string> = { federation: "Федерация", athlete: "Спортсмен", coach: "Тренер", judge: "Судья" };
const CurrentUserContext = createContext<Me | null>(null);

export function useCurrentUser() {
  return useContext(CurrentUserContext);
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [dark, setDark] = useState(false);
  const [roleError, setRoleError] = useState("");
  const [identityPending, setIdentityPending] = useState(false);
  const identityRevision = useRef(0);
  const roleQueue = useRef<Promise<void>>(Promise.resolve());
  const activeRoleRequest = useRef<AbortController | null>(null);
  const logoutPending = useRef(false);

  function toggleTheme() {
    const next = !dark;
    setDark(next);
    localStorage.setItem("fsp-theme", next ? "dark" : "light");
  }

  useEffect(() => {
    const frame = requestAnimationFrame(() => setDark(localStorage.getItem("fsp-theme") === "dark"));
    return () => cancelAnimationFrame(frame);
  }, []);

  useEffect(() => {
    let current = true;
    const revision = identityRevision.current;
    api<Me>("auth/me/").then((user) => { if (current && revision === identityRevision.current) setMe(user); }).catch(() => { if (current && revision === identityRevision.current) setMe(null); });
    return () => { current = false; };
  }, [path]);

  async function switchRole(role: Role) {
    if (logoutPending.current) return;
    const revision = ++identityRevision.current;
    setIdentityPending(true);
    setRoleError("");
    const operation = roleQueue.current.then(async () => {
      if (revision !== identityRevision.current) return;
      const controller = new AbortController();
      activeRoleRequest.current = controller;
      try {
        const user = await api<Me>("auth/active-role/", { method: "POST", body: JSON.stringify({ role }), signal: controller.signal });
        if (revision === identityRevision.current) setMe(user);
      } catch (error) {
        if (revision === identityRevision.current) setRoleError(error instanceof Error ? error.message : "Ошибка выбора роли");
      } finally {
        if (activeRoleRequest.current === controller) activeRoleRequest.current = null;
        if (revision === identityRevision.current) setIdentityPending(false);
      }
    });
    roleQueue.current = operation;
    await operation;
  }

  async function signOut() {
    if (logoutPending.current) return;
    logoutPending.current = true;
    setIdentityPending(true);
    ++identityRevision.current;
    activeRoleRequest.current?.abort();
    try {
      await roleQueue.current;
      await api<void>("auth/logout/", { method: "POST" });
      setMe(null);
      router.push("/");
      router.refresh();
    } catch (error) {
      setRoleError(error instanceof Error ? error.message : "Не удалось выйти");
    } finally {
      logoutPending.current = false;
      setIdentityPending(false);
    }
  }

  return <>
    <input type="checkbox" id="th" aria-label="Тёмная тема" checked={dark} onChange={toggleTheme} />
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
          <Link className={path.startsWith("/competitions") ? "on" : ""} href="/competitions"><b>03</b>Календарь</Link>
          <Link href="/dashboard"><b>04</b>Кабинет</Link>
          <Link className={path.startsWith("/ratings") ? "on" : ""} href="/ratings"><b>05</b>Рейтинги</Link>
          <Link className={path.startsWith("/teams") ? "on" : ""} href="/teams"><b>06</b>Команды</Link>
          <Link className={path === "/services" ? "on" : ""} href="/services"><b>07</b>Сервисы</Link>
        </nav>
        <div className="rb">
          {me ? <>
            <div className="menu" aria-label="Роль">{!me.active_role && <div className="a">Выбор роли</div>}{me.roles.map((role) => <button type="button" key={role} className={me.active_role === role ? "a" : ""} onClick={() => switchRole(role)} aria-pressed={me.active_role === role}>{roleName[role]}{me.active_role === role && <svg className="ic" viewBox="0 0 24 24" aria-hidden="true" style={{ marginLeft: "auto" }}><path d="M4 12.5l5 5L20 6.5" /></svg>}</button>)}</div>
            {roleError && <p role="alert">{roleError}</p>}
            <div className="rbtn"><span>{me.full_name}<small>Роль: {me.active_role ? roleName[me.active_role] : "не выбрана"}</small></span></div>
            <button type="button" className="tgl" onClick={signOut}>Выйти</button>
          </> : <div className="rbtn"><span>Гость<small><Link href="/login">Войти</Link> · <Link href="/register">Регистрация</Link></small></span></div>}
          <label className="tgl" htmlFor="th"><span className="t-l">Тёмная тема</span><span className="t-d">Светлая тема</span></label>
          <small>Платформа ФСП Оренбургской области</small>
        </div>
      </aside>
      <main className="main" id="top"><div className="mobile-tools">{me && me.roles.length > 1 && <label className="mobile-role">Роль <select aria-label="Активная роль" value={me.active_role ?? ""} onChange={(event) => switchRole(event.target.value as Role)}>{!me.active_role && <option value="" disabled>Выбор роли</option>}{me.roles.map((role) => <option value={role} key={role}>{roleName[role]}{me.active_role === role ? " ✓" : ""}</option>)}</select></label>}<button type="button" className="mobile-theme" onClick={toggleTheme} aria-label={dark ? "Включить светлую тему" : "Включить тёмную тему"} aria-pressed={dark}>{dark ? "Светлая тема" : "Тёмная тема"}</button></div>{roleError && <p className="mobile-role-error" role="alert">{roleError}</p>}<CurrentUserContext.Provider value={identityPending ? null : me}>{children}</CurrentUserContext.Provider><footer>ФСП Оренбургская область · Данные демонстрации вымышлены</footer></main>
    </div>
    <nav className="mobtab" aria-label="Основная навигация"><Link className={path === "/" ? "on" : ""} href="/"><svg className="ic"><use href="#i-home" /></svg>Главная</Link><Link href="/#disciplines"><svg className="ic"><use href="#i-users" /></svg>Дисциплины</Link><Link className={path.startsWith("/competitions") ? "on" : ""} href="/competitions"><svg className="ic"><use href="#i-cal" /></svg>Календарь</Link><Link className={path.startsWith("/teams") ? "on" : ""} href="/teams"><svg className="ic"><use href="#i-dots" /></svg>Команды</Link><Link className={path === "/dashboard" || path === "/history" || path === "/coach-links" ? "on" : ""} href="/dashboard"><svg className="ic"><use href="#i-dots" /></svg>Кабинет</Link></nav>
  </>;
}
