"use client";

import { Toast } from "@/components/Toast";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useCurrentUser } from "@/components/AppShell";
import { api, Application, Competition, JudgeAssignment } from "@/lib/api";

type ParticipantRole = "athlete" | "coach" | "judge";
type PageData = { competitions: Competition[]; applications: Application[]; assignments: JudgeAssignment[] };

const statusName: Record<Application["status"], string> = {
  pending: "На рассмотрении",
  approved: "Одобрена",
  rejected: "Отклонена",
};

function CompetitionList({ role }: { role: ParticipantRole }) {
  const [data, setData] = useState<PageData | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let current = true;
    const list = role === "judge"
      ? api<JudgeAssignment[]>("judge-assignments/").then((assignments) => ({ assignments, applications: [] as Application[] }))
      : api<Application[]>("applications/").then((applications) => ({ applications, assignments: [] as JudgeAssignment[] }));
    Promise.all([api<Competition[]>("competitions/"), list])
      .then(([competitions, related]) => { if (current) setData({ competitions, ...related }); })
      .catch((cause) => { if (current) setError(cause instanceof Error ? cause.message : "Не удалось загрузить соревнования"); });
    return () => { current = false; };
  }, [role, attempt]);

  if (error) return <div className="workflow-stack"><Toast>{error}</Toast><button className="btn" type="button" onClick={() => { setError(""); setData(null); setAttempt((value) => value + 1); }}>Попробовать снова</button></div>;
  if (!data) return <div className="note" role="status">Загрузка соревнований…</div>;

  const competitions = new Map(data.competitions.map((item) => [item.id, item]));
  if (role === "judge") {
    if (!data.assignments.length) return <div className="note">Назначений пока нет.</div>;
    return <><p>На узком экране прокрутите таблицу по горизонтали.</p><div className="tw" role="region" aria-label="Судейские назначения" tabIndex={0}><table><thead><tr><th>Соревнование</th><th>Дисциплина</th><th>Дата</th><th>Роль</th></tr></thead><tbody>{data.assignments.map((assignment) => {
      const item = competitions.get(assignment.competition);
      return <tr key={assignment.id}><td>{item ? <Link className="workflow-link" href={`/competitions/${item.id}`}>{item.title}</Link> : "Соревнование недоступно"}</td><td>{item?.discipline_name ?? "—"}</td><td className="m">{item ? new Date(item.starts_at).toLocaleDateString("ru-RU") : "—"}</td><td>{assignment.role_label}</td></tr>;
    })}</tbody></table></div></>;
  }

  if (!data.applications.length) return <div className="note">Заявок пока нет. <Link className="workflow-link" href="/competitions">Открыть календарь</Link></div>;
  return <><p>На узком экране прокрутите таблицу по горизонтали.</p><div className="tw" role="region" aria-label="Заявки на соревнования" tabIndex={0}><table><thead><tr><th>Соревнование</th>{role === "coach" && <th>Спортсмен</th>}<th>Дисциплина</th><th>Дата</th><th>Статус заявки</th></tr></thead><tbody>{data.applications.map((application) => {
    const item = competitions.get(application.competition);
    return <tr key={application.id}><td>{item ? <Link className="workflow-link" href={`/competitions/${item.id}`}>{item.title}</Link> : "Соревнование недоступно"}</td>{role === "coach" && <td>{application.athlete_name}</td>}<td>{item?.discipline_name ?? "—"}</td><td className="m">{item ? new Date(item.starts_at).toLocaleDateString("ru-RU") : "—"}</td><td><span className={`bd ${application.status === "pending" ? "wn" : ""}`}>{statusName[application.status]}</span>{application.decision_reason && <p>{application.decision_reason}</p>}</td></tr>;
  })}</tbody></table></div></>;
}

export default function MyCompetitions() {
  const me = useCurrentUser();
  const role = me?.active_role;
  const supported = role === "athlete" || role === "coach" || role === "judge";

  return <>
    <header className="dashboard-head"><span className="kick"><Link className="workflow-link" href="/dashboard">← Кабинет</Link></span><h1>Мои соревнования</h1><p className="lead">{role === "judge" ? "Ваши судейские назначения." : "Заявки на соревнования и решения по ним."}</p></header>
    <section className="blk"><h2><b>01</b><span>{role === "judge" ? "Назначения" : "Заявки"}</span></h2><div style={{ minWidth: 0 }}>{!me ? <Toast>Для доступа <Link className="workflow-link" href="/login">войдите</Link>.</Toast> : supported ? <CompetitionList key={`${me.id}:${role}`} role={role} /> : <div className="note">Выберите роль спортсмена, тренера или судьи.</div>}</div></section>
  </>;
}
