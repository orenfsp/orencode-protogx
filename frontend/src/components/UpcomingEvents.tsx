"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, Competition, JudgeAssignment, Role } from "@/lib/api";

export function UpcomingEvents({ role }: { role: Role }) {
  const [items, setItems] = useState<Competition[] | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const abort = new AbortController();
    const signal = abort.signal;
    const path = role === "athlete" ? "competitions/?eligible_age=true" : "competitions/";
    void Promise.all([api<Competition[]>(path, { signal }), role === "judge" ? api<JudgeAssignment[]>("judge-assignments/", { signal }) : Promise.resolve(null)]).then(([events, assignments]) => {
      if (!signal.aborted) setItems(events.filter((event) => event.state === "published" && new Date(event.ends_at).getTime() >= Date.now() && (!assignments || assignments.some((assignment) => assignment.competition === event.id))).sort((a, b) => a.starts_at.localeCompare(b.starts_at)).slice(0, 3));
    }).catch(() => { if (!signal.aborted) setError("Не удалось загрузить ближайшие соревнования"); });
    return () => abort.abort();
  }, [role]);
  return <section className="blk"><h2><b>03</b><span>Ближайшие соревнования</span></h2><div className="workflow-stack">{error ? <p role="alert">{error}</p> : !items ? <p role="status">Загрузка соревнований…</p> : items.length ? items.map((item) => <div className="workflow-record" key={item.id}><Link className="workflow-link" href={`/competitions/${item.id}`}>{item.title}</Link><p>{item.discipline_name} · {new Date(item.starts_at).toLocaleDateString("ru-RU")}</p><p>Заявки до {new Date(item.registration_deadline).toLocaleString("ru-RU")} · {item.registration_open === false ? "Приём закрыт" : "По установленному сроку"}</p></div>) : <p className="note">Ближайших соревнований пока нет.</p>}</div></section>;
}
