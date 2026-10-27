"use client";

import { useEffect, useMemo, useState } from "react";
import { api, downloadDocument, RegionalTeam, TeamCandidate, TeamOptions } from "@/lib/api";
import { useCurrentUser } from "@/components/AppShell";

export default function TeamsPage() {
  const user = useCurrentUser();
  if (!user || user.active_role !== "federation") return <p className="note">Для просмотра команд выберите роль федерации.</p>;
  return <TeamsWorkspace key={user.id} />;
}

function TeamsWorkspace() {
  const [options, setOptions] = useState<TeamOptions | null>(null);
  const [teams, setTeams] = useState<RegionalTeam[]>([]);
  const [selected, setSelected] = useState<RegionalTeam | null>(null);
  const [candidates, setCandidates] = useState<TeamCandidate[]>([]);
  const [season, setSeason] = useState("");
  const [discipline, setDiscipline] = useState("");
  const [ageGroup, setAgeGroup] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [teamName, setTeamName] = useState("Новая региональная команда");

  async function loadTeams() {
    const params = new URLSearchParams();
    if (season) params.set("season", season);
    if (discipline) params.set("discipline", discipline);
    if (ageGroup) params.set("age_group", ageGroup);
    const value = await api<RegionalTeam[]>(`teams/?${params.toString()}`);
    setTeams(value);
    if (selected) setSelected(value.find((item) => item.id === selected.id) ?? null);
  }

  useEffect(() => {
    api<TeamOptions>("teams/options/").then((value) => {
      setOptions(value);
      if (value.seasons[0]) setSeason(String(value.seasons[0].year));
      if (value.disciplines[0]) setDiscipline(value.disciplines[0].code);
      if (value.age_groups[0]) setAgeGroup(String(value.age_groups[0].id));
    }).catch((failure) => setError(failure instanceof Error ? failure.message : "Не удалось загрузить справочники"));
  }, []);

  useEffect(() => { if (options) loadTeams().catch((failure) => setError(failure instanceof Error ? failure.message : "Не удалось загрузить команды")); }, [options, season, discipline, ageGroup]);

  async function openTeam(team: RegionalTeam) {
    setSelected(team);
    try { setCandidates(await api<TeamCandidate[]>(`teams/${team.id}/candidates/`)); } catch (failure) { setError(failure instanceof Error ? failure.message : "Не удалось загрузить кандидатов"); }
  }

  async function createTeam() {
    if (!options || !season || !discipline || !ageGroup) return;
    setBusy(true); setError("");
    try {
      const created = await api<RegionalTeam>("teams/", { method: "POST", body: JSON.stringify({ name: teamName, season: options.seasons.find((item) => String(item.year) === season)?.id, discipline: options.disciplines.find((item) => item.code === discipline)?.id, age_group: Number(ageGroup), region: "Оренбургская область" }) });
      await loadTeams(); await openTeam(created);
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Не удалось создать команду"); } finally { setBusy(false); }
  }

  async function selectCandidate(candidate: TeamCandidate) {
    if (!selected || !candidate.eligible || candidate.selected) return;
    setBusy(true); setError("");
    try { const updated = await api<RegionalTeam>(`teams/${selected.id}/members/`, { method: "POST", body: JSON.stringify({ athlete: candidate.id }) }); setSelected(updated); setCandidates(await api<TeamCandidate[]>(`teams/${selected.id}/candidates/`)); await loadTeams(); } catch (failure) { setError(failure instanceof Error ? failure.message : "Не удалось сохранить выбор"); } finally { setBusy(false); }
  }

  async function removeMember(memberId: number) {
    if (!selected) return;
    setBusy(true);
    try { const updated = await api<RegionalTeam>(`teams/${selected.id}/members/${memberId}/remove/`, { method: "POST", body: JSON.stringify({ reason: "Ручное решение федерации" }) }); setSelected(updated); setCandidates(await api<TeamCandidate[]>(`teams/${selected.id}/candidates/`)); await loadTeams(); } catch (failure) { setError(failure instanceof Error ? failure.message : "Не удалось снять участника"); } finally { setBusy(false); }
  }

  async function moveMember(index: number, direction: -1 | 1) {
    if (!selected) return;
    const members = [...selected.members]; const target = index + direction;
    if (target < 0 || target >= members.length) return;
    [members[index], members[target]] = [members[target], members[index]];
    setBusy(true);
    try { await api(`teams/${selected.id}/reorder/`, { method: "POST", body: JSON.stringify({ member_ids: members.map((item) => item.id) }) }); await openTeam(selected); await loadTeams(); } catch (failure) { setError(failure instanceof Error ? failure.message : "Не удалось изменить порядок"); } finally { setBusy(false); }
  }

  async function download(kind: "roster" | "draft-order", format: "pdf" | "docx") {
    if (!selected) return;
    try { const blob = await downloadDocument(`teams/${selected.id}/documents/?type=${kind}&document_format=${format}`); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = `team-${selected.id}-${kind}.${format}`; link.click(); URL.revokeObjectURL(url); } catch (failure) { setError(failure instanceof Error ? failure.message : "Не удалось скачать документ"); }
  }

  async function publishSelected() {
    if (!selected) return;
    setBusy(true); setError("");
    try { const updated = await api<RegionalTeam>(`teams/${selected.id}/publish/`, { method: "POST", body: JSON.stringify({}) }); setSelected(updated); await loadTeams(); } catch (failure) { setError(failure instanceof Error ? failure.message : "Не удалось утвердить состав"); } finally { setBusy(false); }
  }

  const selectedIds = useMemo(() => new Set(selected?.members.map((item) => item.athlete) ?? []), [selected]);
  return <>
    <header className="dashboard-head"><span className="kick">ФЕДЕРАЦИЯ · ручное решение состава</span><h1>Региональные команды</h1><p className="lead">Рейтинг и ограничения показывают контекст. Состав, порядок и выпуск документов утверждает представитель федерации вручную.</p></header>
    {error && <div className="note wn workflow-spaced" role="alert">{error}</div>}
    <section className="blk"><h2><b>01</b><span>Фильтры</span></h2><div className="workflow-form form-grid"><label className="lb">Сезон<select className="inp" value={season} onChange={(event) => setSeason(event.target.value)}>{options?.seasons.map((item) => <option key={item.id} value={item.year}>{item.name}</option>)}</select></label><label className="lb">Дисциплина<select className="inp" value={discipline} onChange={(event) => setDiscipline(event.target.value)}>{options?.disciplines.map((item) => <option key={item.id} value={item.code}>{item.name}</option>)}</select></label><label className="lb">Возрастная группа<select className="inp" value={ageGroup} onChange={(event) => setAgeGroup(event.target.value)}>{options?.age_groups.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label></div></section>
    <section className="blk"><h2><b>02</b><span>Команды</span></h2><div><div className="cta"><input className="inp" value={teamName} onChange={(event) => setTeamName(event.target.value)} aria-label="Название новой команды" /><button className="btn p" type="button" onClick={createTeam} disabled={busy}>Создать команду</button></div>{!teams.length ? <div className="note">Команд по выбранным фильтрам нет.</div> : <div className="tw"><table><thead><tr><th>№</th><th>Команда</th><th>Дисциплина</th><th>Состав</th><th>Статус</th></tr></thead><tbody>{teams.map((team) => <tr key={team.id} className={selected?.id === team.id ? "sel" : ""}><td>{team.id}</td><td><button className="workflow-link" type="button" onClick={() => openTeam(team)}>{team.name}</button><small>{team.region} · {team.season_year}</small></td><td>{team.discipline_name}</td><td className="m">{team.member_count}</td><td><span className="bd in">{team.status === "draft" ? "Черновик" : "Сформирован"}</span></td></tr>)}</tbody></table></div>}</div></section>
    {selected && <section className="blk"><h2><b>03</b><span>Ручной отбор</span></h2><div className="cmp"><div><h3>{selected.name}</h3><p className="hint">Выбрано вручную: {selected.member_count}. Смена рейтинга не меняет состав автоматически.</p>{!selected.members.length ? <div className="note">Состав пока пуст.</div> : <ol className="at">{selected.members.map((member, index) => <li key={member.id}><b>{String(index + 1).padStart(2, "0")}</b><span><strong>{member.athlete_name}</strong><small>{member.eligibility_snapshot.rating_score ? `Рейтинг ${member.eligibility_snapshot.rating_score}` : "Рейтинг не рассчитан"}</small></span><span><button className="btn" type="button" onClick={() => moveMember(index, -1)} disabled={busy || index === 0}>↑</button><button className="btn" type="button" onClick={() => moveMember(index, 1)} disabled={busy || index === selected.members.length - 1}>↓</button><button className="btn er" type="button" onClick={() => removeMember(member.id)} disabled={busy}>Снять</button></span></li>)}</ol>}</div><div><h3>Кандидаты</h3><div className="tw"><table><thead><tr><th>Спортсмен</th><th>Рейтинг</th><th>Проверка</th><th /></tr></thead><tbody>{candidates.map((candidate) => <tr key={candidate.id}><td>{candidate.full_name}<small>{candidate.email}</small></td><td className="m">{candidate.rating?.score ?? "—"}</td><td>{candidate.eligible ? <span className="bd in">Допущен</span> : <span className="bd wn">Проверить</span>}</td><td><button className="btn p" type="button" onClick={() => selectCandidate(candidate)} disabled={busy || !candidate.eligible || candidate.selected}>{candidate.selected || selectedIds.has(candidate.id) ? "Выбран" : "Добавить"}</button></td></tr>)}</tbody></table></div></div></div></section>}
    {selected && <section className="blk"><h2><b>04</b><span>Документы</span></h2><div className="btns">{selected.status === "draft" && <button className="btn p" type="button" onClick={publishSelected} disabled={busy}>Утвердить состав</button>}<button className="btn p" type="button" onClick={() => download("roster", "pdf")}>Скачать состав PDF</button><button className="btn" type="button" onClick={() => download("roster", "docx")}>Состав DOCX</button><button className="btn p" type="button" onClick={() => download("draft-order", "pdf")}>Проект порядка PDF</button><button className="btn" type="button" onClick={() => download("draft-order", "docx")}>Порядок DOCX</button></div></section>}
  </>;
}
