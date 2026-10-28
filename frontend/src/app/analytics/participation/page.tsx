"use client";

import { useEffect, useRef, useState } from "react";
import { useCurrentUser } from "@/components/AppShell";
import { api, downloadDocument } from "@/lib/api";

type Row = { name: string; participants: number };
type Annual = { year: number; unique_athletes: number; started: number; ceased: number; change: number | null; growth_percent: number | null; breakdowns: Record<string, Row[]> };
const titles: Record<string, string> = { organizations: "Организации", disciplines: "Дисциплины", municipalities: "Муниципалитеты", age_groups: "Возрастные группы" };

export default function ParticipationPage() {
  const user = useCurrentUser();
  if (!user || user.active_role !== "federation") return <p className="note">Для просмотра аналитики выберите роль федерации.</p>;
  return <Workspace key={user.id} />;
}

function Workspace() {
  const [start, setStart] = useState("2024");
  const [end, setEnd] = useState("2025");
  const [organization, setOrganization] = useState("");
  const [discipline, setDiscipline] = useState("");
  const [municipality, setMunicipality] = useState("");
  const [ageGroup, setAgeGroup] = useState("");
  const [query, setQuery] = useState("start_year=2024&end_year=2025");
  const [rows, setRows] = useState<Annual[] | null>(null);
  const [error, setError] = useState("");
  const downloadController = useRef<AbortController | null>(null);
  useEffect(() => () => downloadController.current?.abort(), []);
  useEffect(() => {
    const controller = new AbortController();
    api<Annual[]>(`analytics/participation/?${query}`, { signal: controller.signal }).then((value) => { if (!controller.signal.aborted) { setRows(value); setError(""); } }).catch((failure) => { if (!controller.signal.aborted) { setRows(null); setError(failure.message); } });
    return () => controller.abort();
  }, [query]);
  function apply() {
    const params = new URLSearchParams({ start_year: start, end_year: end });
    if (organization) params.set("organization", organization);
    if (discipline) params.set("discipline", discipline);
    if (municipality) params.set("municipality", municipality);
    if (ageGroup) params.set("age_group", ageGroup);
    setRows(null); setQuery(params.toString());
  }
  async function download() {
    downloadController.current?.abort();
    const controller = new AbortController();
    downloadController.current = controller;
    try { const blob = await downloadDocument(`analytics/participation/export/?${query}`, controller.signal); if (controller.signal.aborted) return; const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = "participation.xlsx"; a.click(); URL.revokeObjectURL(url); } catch (failure) { if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Ошибка скачивания"); }
  }
  return <><header className="dashboard-head"><span className="kick">ФЕДЕРАЦИЯ · исторические данные</span><h1>Участие в спортивном программировании</h1><p className="lead">Уникальные спортсмены за календарный год; записи соревнований не учитываются.</p></header>
    <section className="blk"><h2><b>01</b><span>Период и фильтры</span></h2><div className="form-grid"><label className="lb">С года<input className="inp" type="number" value={start} onChange={(e) => setStart(e.target.value)} /></label><label className="lb">По год<input className="inp" type="number" value={end} onChange={(e) => setEnd(e.target.value)} /></label><label className="lb">ID организации<input className="inp" value={organization} onChange={(e) => setOrganization(e.target.value)} /></label><label className="lb">ID дисциплины<input className="inp" value={discipline} onChange={(e) => setDiscipline(e.target.value)} /></label><label className="lb">Муниципалитет<input className="inp" value={municipality} onChange={(e) => setMunicipality(e.target.value)} /></label><label className="lb">ID возрастной группы<input className="inp" value={ageGroup} onChange={(e) => setAgeGroup(e.target.value)} /></label></div><div className="btns"><button className="btn p" type="button" onClick={apply}>Построить отчёт</button><button className="btn" type="button" onClick={download} disabled={!rows}>Скачать XLSX</button></div></section>
    {error && <p className="note wn" role="alert">{error}</p>}
    <section className="blk"><h2><b>02</b><span>Сравнение</span></h2>{!rows ? <p className="note">{error ? "Отчёт не загружен." : "Загрузка…"}</p> : <div className="tw"><table><thead><tr><th>Год</th><th>Уникальных</th><th>Начали</th><th>Завершили</th><th>Изменение</th><th>Рост, %</th></tr></thead><tbody>{rows.map((r) => <tr key={r.year}><td>{r.year}</td><td>{r.unique_athletes}</td><td>{r.started}</td><td>{r.ceased}</td><td>{r.change ?? "—"}</td><td>{r.growth_percent ?? "—"}</td></tr>)}</tbody></table></div>}<p className="note">Организация, дисциплина и муниципалитет учитываются по пересечению исторических периодов с участием. Категории не суммируются. Возраст определяется на 31 декабря.</p></section>
    {rows && Object.entries(titles).map(([key, title], index) => <section className="blk" key={key}><h2><b>{String(index + 3).padStart(2, "0")}</b><span>{title}</span></h2><div className="tw"><table><thead><tr><th>Год</th><th>Категория</th><th>Участников</th></tr></thead><tbody>{rows.flatMap((row) => row.breakdowns[key].map((item) => <tr key={`${row.year}-${item.name}`}><td>{row.year}</td><td>{item.name}</td><td>{item.participants}</td></tr>))}</tbody></table></div></section>)}</>;
}
