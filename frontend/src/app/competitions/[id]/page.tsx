"use client";

import { Toast } from "@/components/Toast";

import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useCurrentUser } from "@/components/AppShell";
import { CompetitionEditor } from "@/components/CompetitionEditor";
import { ResultEditor } from "@/components/ResultEditor";
import { AgeGroup, api, Application, CalendarEntry, CoachLink, Competition, Discipline, JudgeAssignment, ProtocolPublication, ProtocolSnapshot, ProtocolTemplate, Result } from "@/lib/api";

type JudgeChoice = { id: number; full_name: string };
const statusName: Record<string, string> = { pending: "На рассмотрении", approved: "Одобрена", rejected: "Отклонена", classified: "Классифицирован", no_show: "Не явился", unclassified: "Без результата", disqualified: "Дисквалифицирован", pending_result: "Результат не внесён" };

export default function CompetitionDetail() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const me = useCurrentUser();
  const role = me?.active_role;
  const [competition, setCompetition] = useState<Competition | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [assignments, setAssignments] = useState<JudgeAssignment[]>([]);
  const [results, setResults] = useState<Result[]>([]);
  const [templates, setTemplates] = useState<ProtocolTemplate[]>([]);
  const [groups, setGroups] = useState<AgeGroup[]>([]);
  const [disciplines, setDisciplines] = useState<Discipline[]>([]);
  const [calendar, setCalendar] = useState<CalendarEntry[]>([]);
  const [judges, setJudges] = useState<JudgeChoice[]>([]);
  const [links, setLinks] = useState<CoachLink[]>([]);
  const [publications, setPublications] = useState<ProtocolPublication[]>([]);
  const [snapshot, setSnapshot] = useState<ProtocolSnapshot | null>(null);
  const [edit, setEdit] = useState(false);
  const [ageGroup, setAgeGroup] = useState("");
  const [coachAthlete, setCoachAthlete] = useState("");
  const [judge, setJudge] = useState("");
  const [judgeLabel, setJudgeLabel] = useState("Судья");
  const [reason, setReason] = useState<Record<number, string>>({});
  const [correctionReason, setCorrectionReason] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const load = useCallback(async () => {
    if (!Number.isFinite(id)) return;
    try {
      const [item, allTemplates, allGroups, allDisciplines, allCalendar] = await Promise.all([
        api<Competition>(`competitions/${id}/`), api<ProtocolTemplate[]>("templates/"), api<AgeGroup[]>("age-groups/"), api<Discipline[]>("disciplines/"), api<CalendarEntry[]>("calendar-entries/"),
      ]);
      setCompetition(item); setTemplates(allTemplates); setGroups(allGroups); setDisciplines(allDisciplines); setCalendar(allCalendar);
      if (role && ["federation", "athlete", "coach", "judge"].includes(role)) {
        const list = await api<Application[]>(`applications/?competition=${id}`); setApplications(list);
      } else setApplications([]);
      if (role === "federation" || role === "judge") {
        const [nextAssignments, nextResults] = await Promise.all([api<JudgeAssignment[]>(`judge-assignments/?competition=${id}`), api<Result[]>(`results/?competition=${id}`)]);
        setAssignments(nextAssignments); setResults(nextResults);
      } else { setAssignments([]); setResults([]); }
      if (role === "federation") {
        const [nextJudges, nextPublications] = await Promise.all([api<JudgeChoice[]>("judge-choices/"), api<ProtocolPublication[]>(`competitions/${id}/protocols/`)]);
        setJudges(nextJudges); setPublications(nextPublications);
      }
      if (role === "coach") setLinks(await api<CoachLink[]>("coach-links/"));
      setError("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось загрузить соревнование"); }
  }, [id, role]);
  useEffect(() => { const frame = requestAnimationFrame(() => { void load(); }); return () => cancelAnimationFrame(frame); }, [load]);
  async function action(path: string, body: object = {}, message = "Сохранено") {
    setError(""); setNotice("");
    try { await api(path, { method: "POST", body: JSON.stringify(body) }); setNotice(message); if (path.endsWith("protocol-publish/")) setCorrectionReason(""); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Операция не выполнена"); }
  }
  async function apply(event: FormEvent) {
    event.preventDefault();
    if (!competition || !me) return;
    await action("applications/", { competition: competition.id, athlete: role === "coach" ? Number(coachAthlete) : me.id, age_group: Number(ageGroup) }, "Заявка отправлена");
  }
  async function showPreview() {
    try { setSnapshot(await api<ProtocolSnapshot>(`competitions/${id}/protocol-preview/`)); setError(""); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Предпросмотр недоступен"); }
  }
  const template = templates.find((item) => item.id === competition?.template);
  const approved = applications.filter((item) => item.status === "approved");
  const isAssignedJudge = role === "judge" && assignments.some((item) => item.judge === me?.id);
  const canEnter = role === "federation" || isAssignedJudge;
  const myApplication = applications.find((item) => item.athlete === me?.id);
  const coachOptions = links.filter((link) => link.status === "confirmed" && link.discipline === competition?.discipline);
  return <>
    <header className="dashboard-head"><span className="kick"><Link href="/competitions" className="workflow-link">← Календарь</Link></span><h1>{competition?.title ?? "Соревнование"}</h1>{competition && <p className="lead">{competition.discipline_name} · {new Date(competition.starts_at).toLocaleDateString("ru-RU")} · {competition.location}</p>}</header>
    {error && <Toast>{error}</Toast>}{notice && <Toast tone="success">{notice}</Toast>}
    {!competition ? <section className="blk"><h2><b>…</b><span>Загрузка</span></h2><div>Данные соревнования загружаются.</div></section> : <>
      <section className="blk"><h2><b>01</b><span>Положение</span></h2><div className="workflow-stack">
        <div><span className={`bd ${competition.state === "draft" ? "wn" : ""}`}>{competition.state === "draft" ? "Черновик" : "Опубликовано"}</span></div>
        <p><strong>Уровень:</strong> {competition.level} · <strong>Вид:</strong> {competition.competition_type} · <strong>Формат:</strong> {competition.format}</p>
        <p><strong>Регистрация до:</strong> {new Date(competition.registration_deadline).toLocaleString("ru-RU")}</p>
        <p><strong>Возрастные группы:</strong> {competition.age_group_details.map((group) => group.name).join(", ")} · <strong>Дата определения возраста:</strong> {competition.age_reference_date} · <strong>Одинаковые места:</strong> {competition.allow_ties ? "разрешены" : "не разрешены"}</p>
        {competition.calendar_entry && <p><strong>Календарь:</strong> {calendar.find((entry) => entry.id === competition.calendar_entry)?.title}</p>}
        <div className="workflow-regulations">{competition.regulations}</div>
        <a className="btn" href={`/api/v1/competitions/${id}/regulations/`}>Скачать положение · DOCX</a>
        <p className="bd">{competition.registration_open === false ? "Приём заявок закрыт" : "Приём заявок до установленного срока"}</p>
        {role === "federation" && competition.state === "published" && <button className="btn" onClick={() => void action(`competitions/${id}/registration/`, { registration_open: competition.registration_open === false }, "Приём заявок обновлён")}>{competition.registration_open === false ? "Открыть приём заявок" : "Закрыть приём заявок"}</button>}
        {competition.stages.length > 0 && <ul className="at">{competition.stages.map((stage) => <li key={stage.order}><b>{stage.order}</b><span>{stage.name} · {stage.format}</span><span className="m">{new Date(stage.starts_at).toLocaleDateString("ru-RU")}</span></li>)}</ul>}
      </div></section>
      {role === "federation" && <section className="blk"><h2><b>02</b><span>Настройка</span></h2><div><div className="btns">{competition.state === "draft" && <button className="btn p" type="button" onClick={() => void action(`competitions/${id}/publish/`, {}, "Соревнование опубликовано")}>Опубликовать</button>}<button className="btn" type="button" onClick={() => setEdit(!edit)}>{edit ? "Закрыть редактор" : "Изменить"}</button></div>{edit && <CompetitionEditor initial={competition} disciplines={disciplines} groups={groups} templates={templates} calendar={calendar} onSaved={(saved) => { setCompetition(saved); setEdit(false); setNotice("Изменения сохранены"); }} />}</div></section>}
      {(role === "athlete" || role === "coach") && competition.state === "published" && <section className="blk"><h2><b>02</b><span>Заявка</span></h2><div>{myApplication && role === "athlete" ? <div className="note">Ваша заявка: {statusName[myApplication.status]}{myApplication.decision_reason && ` · ${myApplication.decision_reason}`}</div> : <form className="workflow-form" onSubmit={apply}>{role === "coach" && <><label className="lb">Подтверждённый спортсмен<select className="inp" required value={coachAthlete} onChange={(event) => setCoachAthlete(event.target.value)}><option value="">Выберите</option>{coachOptions.map((link) => <option key={link.id} value={link.athlete ?? ""}>{link.athlete_name}</option>)}</select></label><Link className="workflow-link" href="/coach-links">Управление связями тренера</Link></>}<label className="lb">Возрастная группа<select className="inp" required value={ageGroup} onChange={(event) => setAgeGroup(event.target.value)}><option value="">Выберите</option>{competition.age_group_details.map((group) => <option value={group.id} key={group.id}>{group.name}</option>)}</select></label><button className="btn p" type="submit">Отправить заявку</button></form>}</div></section>}
      {role === "federation" && <section className="blk"><h2><b>03</b><span>Заявки</span></h2><div>{applications.length ? <div className="workflow-stack">{applications.map((item) => <div className="workflow-record" key={item.id}><strong>{item.athlete_name}</strong><span className={`bd ${item.status === "pending" ? "wn" : ""}`}>{statusName[item.status]}</span>{item.status === "pending" && <div className="workflow-actions"><button className="btn" type="button" onClick={() => void action(`applications/${item.id}/decision/`, { status: "approved" }, "Заявка одобрена")}>Одобрить</button><input className="inp" aria-label={`Причина отказа: ${item.athlete_name}`} placeholder="Причина отказа" value={reason[item.id] ?? ""} onChange={(event) => setReason({ ...reason, [item.id]: event.target.value })} /><button className="btn" type="button" onClick={() => void action(`applications/${item.id}/decision/`, { status: "rejected", reason: reason[item.id] ?? "" }, "Заявка отклонена")}>Отклонить</button></div>}</div>)}</div> : <div className="note">Заявок пока нет.</div>}</div></section>}
      {role === "federation" && <section className="blk"><h2><b>04</b><span>Судьи</span></h2><div className="workflow-stack"><form className="workflow-actions" onSubmit={(event) => { event.preventDefault(); void action("judge-assignments/", { competition: id, judge: Number(judge), role_label: judgeLabel }, "Судья назначен"); }}><select className="inp" aria-label="Судья" required value={judge} onChange={(event) => setJudge(event.target.value)}><option value="">Выберите судью</option>{judges.map((item) => <option value={item.id} key={item.id}>{item.full_name}</option>)}</select><input className="inp" aria-label="Роль судьи" required value={judgeLabel} onChange={(event) => setJudgeLabel(event.target.value)} /><button className="btn" type="submit">Назначить</button></form>{assignments.map((item) => <div className="workflow-record" key={item.id}>{item.judge_name} · {item.role_label}</div>)}</div></section>}
      {canEnter && template && <section className="blk"><h2><b>05</b><span>Результаты</span></h2><div className="workflow-stack">{approved.length ? approved.map((item) => { const current = results.find((result) => result.application === item.id); return <div className="workflow-record" key={item.id}><ResultEditor key={`${item.id}-${current?.updated_at ?? ""}`} application={item} template={template} current={current} onSaved={() => { setNotice("Результат записан"); void load(); }} />{current && <div className="workflow-actions"><span className={`bd ${current.validated_by ? "" : "wn"}`}>{current.validated_by ? "Проверен" : "Ожидает проверки"}</span>{role === "federation" && !current.validated_by && <button className="btn" type="button" onClick={() => void action(`results/${current.id}/validate/`, {}, "Результат проверен")}>Проверить</button>}</div>}</div>; }) : <div className="note">Одобренных участников пока нет.</div>}</div></section>}
      {role === "federation" && <section className="blk"><h2><b>06</b><span>Протокол</span></h2><div className="workflow-stack">
        <Toast>Шаблон не подтверждён по первоисточнику. Перед официальным применением требуется проверка.</Toast>
        {publications.length > 0 && <label className="lb">Причина новой версии<input className="inp workflow-search" required value={correctionReason} onChange={(event) => setCorrectionReason(event.target.value)} /></label>}
        <div className="btns"><button className="btn" type="button" onClick={() => void showPreview()}>Предпросмотр</button><button className="btn p" type="button" onClick={() => void action(`competitions/${id}/protocol-publish/`, { correction_reason: correctionReason }, "Новая версия протокола опубликована")}>Опубликовать версию</button></div>
        {publications.length > 0 && <div className="workflow-stack">{publications.map((item) => <div className="workflow-actions" key={item.id}><button className="btn" type="button" onClick={() => setSnapshot(item.snapshot)}>Версия {item.version} · {new Date(item.published_at).toLocaleDateString("ru-RU")}</button><a className="btn" href={`/api/v1/competitions/${id}/protocols/${item.version}/download/?file_format=pdf`}>PDF</a><a className="btn" href={`/api/v1/competitions/${id}/protocols/${item.version}/download/?file_format=docx`}>DOCX</a>{item.correction_reason && <span>{item.correction_reason}</span>}</div>)}</div>}
        {snapshot && <div className="workflow-stack"><h3>Предпросмотр · {snapshot.discipline}</h3><p>{snapshot.metadata.competition_type} · {snapshot.metadata.level} · {new Date(snapshot.metadata.starts_at).toLocaleDateString("ru-RU")} · {snapshot.metadata.location}</p>{snapshot.source_url && <p>Образец: <a className="workflow-link" href={snapshot.source_url} target="_blank" rel="noreferrer">источник для проверки</a></p>}<div className="tw"><table><thead><tr><th>№</th>{snapshot.columns.map((column) => <th key={column.key}>{column.label}</th>)}</tr></thead><tbody>{snapshot.rows.map((row, index) => <tr key={row.application_id}><td>{index + 1}</td>{snapshot.columns.map((column) => <td key={column.key}>{column.key === "status" ? statusName[String(row[column.key])] ?? row[column.key] : row[column.key] ?? "—"}</td>)}</tr>)}</tbody></table></div>{snapshot.sections.includes("judges") && snapshot.judges.length > 0 && <p><strong>Судейская коллегия:</strong> {snapshot.judges.map((item) => `${item.role}: ${item.name}`).join("; ")}</p>}{snapshot.sections.includes("signatures") && snapshot.signature_roles.length > 0 && <p><strong>Поля подписей:</strong> {snapshot.signature_roles.join(", ")} (без электронной подписи)</p>}</div>}
      </div></section>}
    </>}
  </>;
}
