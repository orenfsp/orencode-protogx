"use client";

import { Toast } from "@/components/Toast";
import { NotificationCenter } from "@/components/NotificationCenter";
import { ConsentPanel } from "@/components/ConsentPanel";
import { FederationOperations } from "@/components/FederationOperations";
import { UpcomingEvents } from "@/components/UpcomingEvents";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useCurrentUser } from "@/components/AppShell";
import { api, Dashboard as DashboardData, Role } from "@/lib/api";

const roleContent: Record<Role, { title: string; intro: string; next: string }> = {
  federation: { title: "Федерация", intro: "Сводка реестра по назначенным ролям и проверке согласий представителей.", next: "Создавайте соревнования и управляйте заявками, судьями, результатами и протоколами в календаре." },
  athlete: { title: "Спортсмен", intro: "Личные данные согласия и доступные дисциплины.", next: "Подавайте заявки в календаре и смотрите опубликованные результаты в своей истории." },
  coach: { title: "Тренер", intro: "Ваш доступ тренера и каталог дисциплин.", next: "Запросите связь со спортсменом; после подтверждения подавайте его заявки." },
  judge: { title: "Судья", intro: "Ваш доступ судьи и каталог дисциплин.", next: "Назначения и ввод результатов доступны в карточках соревнований." },
};

export default function Dashboard() {
  const me = useCurrentUser();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const role = me?.active_role;

  useEffect(() => {
    if (!role) return;
    let current = true;
    api<DashboardData>("auth/dashboard/")
      .then((result) => { if (current) { setData(result); setError(""); } })
      .catch((failure) => { if (current) { setData(null); setError(failure instanceof Error ? failure.message : "Не удалось загрузить кабинет"); } });
    return () => { current = false; };
  }, [me?.id, role]);

  const dashboard = data?.role === role ? data : null;
  return <>
    <header className="dashboard-head"><span className="kick">Личный кабинет · {role ? roleContent[role].title : "Вход"}</span><h1>{role ? roleContent[role].title : "Личный кабинет"}</h1><p className="lead">{role ? roleContent[role].intro : "Войдите, чтобы открыть свой кабинет."}</p></header>
    {role && <p className="section-intro"><Link className="btn" href="/services">Дополнительные сервисы</Link></p>}
    {!me ? <section className="blk"><h2><b>01</b><span>Вход</span></h2><Toast>Для доступа к кабинету <Link href="/login">войдите</Link>.</Toast></section>
      : !role ? <section className="blk"><h2><b>01</b><span>Роль</span></h2><Toast>Активная роль недоступна. Выберите назначенную роль в боковой панели.</Toast></section>
        : <>
          <section className="blk"><h2><b>01</b><span>Обзор</span></h2><div>
            <p className="section-intro">{me.full_name} · {roleContent[role].title}</p>
            {error ? <Toast>{error}</Toast> : dashboard ? <div className="kp dashboard-metrics">{dashboard.metrics.map((metric) => <div key={metric.label}><div className="v">{metric.value}</div><div className="l">{metric.label}</div></div>)}</div> : <p role="status">Загрузка данных кабинета…</p>}
            {dashboard?.guardian_status && <Toast>Согласие представителя: {dashboard.guardian_status === "pending_verification" ? "ожидает проверки" : dashboard.guardian_status}</Toast>}
          </div></section>
          <section className="blk"><h2><b>02</b><span>Действия</span></h2><div><div className="note">{roleContent[role].next}</div><div className="cta"><Link className="btn i" href="/competitions">Открыть календарь</Link><Link className="btn" href="/ratings">Открыть рейтинги</Link>{role !== "federation" && <Link className="btn" href="/my-competitions">Мои соревнования</Link>}<Link className="btn" href="/qualifications">Разряды и категории</Link>{role === "athlete" && <><Link className="btn" href="/history">История результатов</Link><Link className="btn" href="/coach-links">Связи тренера</Link></>}{role === "coach" && <Link className="btn" href="/coach-links">Связи со спортсменами</Link>}<Link className="btn" href="/#disciplines">Смотреть дисциплины</Link></div></div></section>
          <UpcomingEvents key={`upcoming:${me.id}:${role}`} role={role} />
          <NotificationCenter key={`${me.id}:${role}`} />
          {role === "athlete" && <p><Link className="btn" href="/profile">Мой профиль и РУСАДА</Link></p>}
          <ConsentPanel key={`consent:${me.id}:${role}`} />
          {role === "federation" && <FederationOperations key={`federation:${me.id}`} />}
        </>}
  </>;
}
