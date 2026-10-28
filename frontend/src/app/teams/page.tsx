"use client";

import { Toast } from "@/components/Toast";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { api, ApiError, downloadDocument, RegionalTeam, TeamCandidate, TeamOptions } from "@/lib/api";
import { useCurrentUser } from "@/components/AppShell";

async function loadAllPages<T>(path: string, signal?: AbortSignal): Promise<T[]> {
  const result: T[] = [];
  let page = 1;
  while (true) {
    const separator = path.includes("?") ? "&" : "?";
    const pagePath = page === 1 ? path : `${path}${separator}page=${page}`;
    const response = await api<T[] | { results: T[]; next: string | null }>(pagePath, { signal });
    if (Array.isArray(response)) return response;
    result.push(...response.results);
    if (!response.next) return result;
    page += 1;
  }
}

export default function TeamsPage() {
  const user = useCurrentUser();
  if (!user || user.active_role !== "federation") return <p className="note">Для просмотра команд выберите роль федерации.</p>;
  return <TeamsWorkspace key={user.id} />;
}

function TeamsWorkspace() {
  const [options, setOptions] = useState<TeamOptions | null>(null);
  const [teams, setTeams] = useState<RegionalTeam[] | null>(null);
  const [selected, setSelected] = useState<RegionalTeam | null>(null);
  const [candidates, setCandidates] = useState<TeamCandidate[] | null>(null);
  const [season, setSeason] = useState("");
  const [discipline, setDiscipline] = useState("");
  const [ageGroup, setAgeGroup] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [accessDenied, setAccessDenied] = useState(false);
  const [candidateFailed, setCandidateFailed] = useState(false);
  const [teamName, setTeamName] = useState("Новая региональная команда");
  const [search, setSearch] = useState("");
  const [candidatePage, setCandidatePage] = useState(1);
  const candidateRevision = useRef(0);

  function handleFailure(failure: unknown, fallback: string) {
    if (failure instanceof ApiError && (failure.status === 401 || failure.status === 403)) setAccessDenied(true);
    setError(failure instanceof Error ? failure.message : fallback);
  }

  async function loadTeams() {
    const params = new URLSearchParams();
    if (season) params.set("season", season);
    if (discipline) params.set("discipline", discipline);
    if (ageGroup) params.set("age_group", ageGroup);
    const value = await loadAllPages<RegionalTeam>(`teams/?${params.toString()}`);
    setTeams(value);
    if (selected) setSelected(value.find((item) => item.id === selected.id) ?? null);
  }

  useEffect(() => {
    api<TeamOptions>("teams/options/").then((value) => {
      setOptions(value);
      if (value.seasons[0]) setSeason(String(value.seasons[0].year));
      if (value.disciplines[0]) setDiscipline(value.disciplines[0].code);
      if (value.age_groups[0]) setAgeGroup(String(value.age_groups[0].id));
    }).catch((failure) => handleFailure(failure, "Не удалось загрузить справочники"));
  }, []);

  useEffect(() => {
    if (!options) return;
    candidateRevision.current += 1;
    const controller = new AbortController();
    const params = new URLSearchParams();
    if (season) params.set("season", season);
    if (discipline) params.set("discipline", discipline);
    if (ageGroup) params.set("age_group", ageGroup);
    loadAllPages<RegionalTeam>(`teams/?${params.toString()}`, controller.signal)
      .then((value) => {
        if (controller.signal.aborted) return;
        setTeams(value);
        setSelected((current) => current ? value.find((item) => item.id === current.id) ?? null : null);
      })
      .catch((failure) => { if (!controller.signal.aborted) handleFailure(failure, "Не удалось загрузить команды"); });
    return () => controller.abort();
  }, [options, season, discipline, ageGroup]);

  async function openTeam(team: RegionalTeam) {
    const revision = ++candidateRevision.current;
    setSelected(team);
    setCandidatePage(1);
    setCandidates(null);
    setCandidateFailed(false);
    try {
      const value = await loadAllPages<TeamCandidate>(`teams/${team.id}/candidates/`);
      if (revision === candidateRevision.current) setCandidates(value);
    } catch (failure) {
      if (revision === candidateRevision.current) { setCandidates([]); setCandidateFailed(true); }
      if (revision === candidateRevision.current || (failure instanceof ApiError && (failure.status === 401 || failure.status === 403))) handleFailure(failure, "Не удалось загрузить кандидатов");
    }
  }

  async function createTeam() {
    if (!options || !season || !discipline || !ageGroup) return;
    setBusy(true); setError("");
    try {
      const created = await api<RegionalTeam>("teams/", { method: "POST", body: JSON.stringify({ name: teamName, season: options.seasons.find((item) => String(item.year) === season)?.id, discipline: options.disciplines.find((item) => item.code === discipline)?.id, age_group: Number(ageGroup), region: "Оренбургская область" }) });
      await loadTeams(); await openTeam(created);
    } catch (failure) { handleFailure(failure, "Не удалось создать команду"); } finally { setBusy(false); }
  }

  async function selectCandidate(candidate: TeamCandidate) {
    if (!selected || !candidate.eligible || candidate.selected) return;
    setBusy(true); setError("");
    try { const updated = await api<RegionalTeam>(`teams/${selected.id}/members/`, { method: "POST", body: JSON.stringify({ athlete: candidate.id }) }); setSelected(updated); setCandidates(await loadAllPages<TeamCandidate>(`teams/${selected.id}/candidates/`)); await loadTeams(); } catch (failure) { handleFailure(failure, "Не удалось сохранить выбор"); } finally { setBusy(false); }
  }

  async function removeMember(memberId: number) {
    if (!selected) return;
    setBusy(true);
    try { const updated = await api<RegionalTeam>(`teams/${selected.id}/members/${memberId}/remove/`, { method: "POST", body: JSON.stringify({ reason: "Ручное решение федерации" }) }); setSelected(updated); setCandidates(await loadAllPages<TeamCandidate>(`teams/${selected.id}/candidates/`)); await loadTeams(); } catch (failure) { handleFailure(failure, "Не удалось снять участника"); } finally { setBusy(false); }
  }

  async function moveMember(index: number, direction: -1 | 1) {
    if (!selected) return;
    const members = [...selected.members]; const target = index + direction;
    if (target < 0 || target >= members.length) return;
    [members[index], members[target]] = [members[target], members[index]];
    setBusy(true);
    try { await api(`teams/${selected.id}/reorder/`, { method: "POST", body: JSON.stringify({ member_ids: members.map((item) => item.id) }) }); await openTeam(selected); await loadTeams(); } catch (failure) { handleFailure(failure, "Не удалось изменить порядок"); } finally { setBusy(false); }
  }

  async function download(kind: "roster" | "draft-order", format: "pdf" | "docx") {
    if (!selected) return;
    try { const blob = await downloadDocument(`teams/${selected.id}/documents/?type=${kind}&document_format=${format}`); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = `team-${selected.id}-${kind}.${format}`; link.click(); URL.revokeObjectURL(url); } catch (failure) { handleFailure(failure, "Не удалось скачать документ"); }
  }

  async function publishSelected() {
    if (!selected) return;
    setBusy(true); setError("");
    try { const updated = await api<RegionalTeam>(`teams/${selected.id}/publish/`, { method: "POST", body: JSON.stringify({}) }); setSelected(updated); await loadTeams(); } catch (failure) { handleFailure(failure, "Не удалось утвердить состав"); } finally { setBusy(false); }
  }

  const selectedIds = useMemo(() => new Set(selected?.members.map((item) => item.athlete) ?? []), [selected]);
  const filteredCandidates = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return (candidates ?? []).filter((candidate) => `${candidate.full_name} ${candidate.email}`.toLocaleLowerCase().includes(query));
  }, [candidates, search]);
  const candidatePageSize = 10;
  const candidatePageCount = Math.ceil(filteredCandidates.length / candidatePageSize);
  const visibleCandidatePage = Math.min(candidatePage, Math.max(1, candidatePageCount));
  const pagedCandidates = filteredCandidates.slice((visibleCandidatePage - 1) * candidatePageSize, visibleCandidatePage * candidatePageSize);
  if (accessDenied) return <Toast>Доступ к командам недоступен. Войдите снова или выберите роль федерации.</Toast>;
  return <>
    <header className="dashboard-head"><span className="kick">ФЕДЕРАЦИЯ · ручное решение состава</span><h1>Региональные команды</h1><p className="lead">Рейтинг и ограничения показывают контекст. Состав, порядок и выпуск документов утверждает представитель федерации вручную.</p></header>
    {error && <Toast>{error}</Toast>}
    <section className="blk"><h2><b>01</b><span>Фильтры</span></h2><div className="workflow-form form-grid"><label className="lb">Сезон<select className="inp" disabled={busy} value={season} onChange={(event) => setSeason(event.target.value)}>{options?.seasons.map((item) => <option key={item.id} value={item.year}>{item.name}</option>)}</select></label><label className="lb">Дисциплина<select className="inp" disabled={busy} value={discipline} onChange={(event) => setDiscipline(event.target.value)}>{options?.disciplines.map((item) => <option key={item.id} value={item.code}>{item.name}</option>)}</select></label><label className="lb">Возрастная группа<select className="inp" disabled={busy} value={ageGroup} onChange={(event) => setAgeGroup(event.target.value)}>{options?.age_groups.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label></div></section>
    <section className="blk"><h2><b>02</b><span>Команды</span></h2><div><div className="cta team-create"><input className="inp" value={teamName} onChange={(event) => setTeamName(event.target.value)} aria-label="Название новой команды" /><button className="btn p" type="button" onClick={createTeam} disabled={busy}>Создать команду</button></div>{teams === null ? <div className="note">{error ? "Команды не загружены." : "Загрузка команд…"}</div> : !teams.length ? <div className="note">Команд по выбранным фильтрам нет.</div> : <div className="tw"><table><thead><tr><th>№</th><th>Команда</th><th>Дисциплина</th><th>Состав</th><th>Статус</th></tr></thead><tbody>{teams.map((team) => <tr key={team.id} className={selected?.id === team.id ? "sel" : ""}><td>{team.id}</td><td><button className="workflow-link" type="button" disabled={busy} onClick={() => openTeam(team)}>{team.name}</button><small>{team.region} · {team.season_year}</small></td><td>{team.discipline_name}</td><td className="m">{team.member_count}</td><td><span className="bd in">{team.status === "draft" ? "Черновик" : "Сформирован"}</span></td></tr>)}</tbody></table></div>}</div></section>
    {selected && <section className="blk team-selection"><h2><b>03</b><span>Ручной отбор</span></h2><div className="cmp"><div><h3>{selected.name}</h3><p className="hint">Выбрано вручную: {selected.member_count}. Смена рейтинга не меняет состав автоматически.</p>{!selected.members.length ? <div className="note">Состав пока пуст.</div> : <ol className="at">{selected.members.map((member, index) => <li key={member.id}><b>{String(index + 1).padStart(2, "0")}</b><span><strong>{member.athlete_name}</strong><small>{member.eligibility_snapshot.rating_score ? `Рейтинг ${member.eligibility_snapshot.rating_score}` : "Рейтинг не рассчитан"}</small>{member.current_eligibility && !member.current_eligibility.eligible && <small className="wn">Текущий допуск требует проверки</small>}</span><span><button className="btn" type="button" onClick={() => moveMember(index, -1)} disabled={busy || index === 0}>↑</button><button className="btn" type="button" onClick={() => moveMember(index, 1)} disabled={busy || index === selected.members.length - 1}>↓</button><button className="btn er" type="button" onClick={() => removeMember(member.id)} disabled={busy}>Снять</button></span></li>)}</ol>}</div><div><h3>Кандидаты</h3><p><Link className="workflow-link" href="/ratings">Расшифровка рейтинга и результаты</Link></p><label className="lb">Поиск спортсмена<input className="inp" value={search} onChange={(event) => { setSearch(event.target.value); setCandidatePage(1); }} /></label>{candidates === null ? <div className="note">Загрузка кандидатов…</div> : candidateFailed ? <Toast>Кандидаты не загружены. Откройте команду снова.</Toast> : filteredCandidates.length === 0 ? <div className="note">Кандидатов по вашему запросу нет.</div> : <div className="tw"><table className="team-candidates-table"><thead><tr><th>Спортсмен</th><th>Рейтинг</th><th>Проверка</th><th /></tr></thead><tbody>{pagedCandidates.map((candidate) => <tr key={candidate.id}><td>{candidate.full_name}<small>{candidate.email}</small><small>{candidate.sport_rank ?? "Разряд не указан"}</small></td><td className="m">{candidate.rating?.score ?? "—"}{candidate.rating?.position && <small>Место {candidate.rating.position}</small>}</td><td>{candidate.eligible ? <span className="bd in">Допущен</span> : <span className="bd wn">Проверить{candidate.eligibility.restriction ? `: ${candidate.eligibility.restriction}` : ""}</span>}</td><td><button className="btn p" type="button" onClick={() => selectCandidate(candidate)} disabled={busy || !candidate.eligible || candidate.selected}>{candidate.selected || selectedIds.has(candidate.id) ? "Выбран" : "Добавить"}</button></td></tr>)}</tbody></table></div>}{candidatePageCount > 1 && <nav className="team-candidate-pages" aria-label="Страницы кандидатов"><button className="btn" type="button" disabled={visibleCandidatePage === 1} onClick={() => setCandidatePage(visibleCandidatePage - 1)}>Назад</button><span>Страница {visibleCandidatePage} из {candidatePageCount}</span><button className="btn" type="button" disabled={visibleCandidatePage === candidatePageCount} onClick={() => setCandidatePage(visibleCandidatePage + 1)}>Вперёд</button></nav>}</div></div></section>}
    {selected && <section className="blk"><h2><b>04</b><span>Документы</span></h2><div className="btns">{selected.status === "draft" && <button className="btn p" type="button" onClick={publishSelected} disabled={busy}>Утвердить состав</button>}<button className="btn p" type="button" onClick={() => download("roster", "pdf")}>Скачать состав PDF</button><button className="btn" type="button" onClick={() => download("roster", "docx")}>Состав DOCX</button><button className="btn p" type="button" onClick={() => download("draft-order", "pdf")}>Проект порядка PDF</button><button className="btn" type="button" onClick={() => download("draft-order", "docx")}>Порядок DOCX</button></div></section>}
  </>;
}
