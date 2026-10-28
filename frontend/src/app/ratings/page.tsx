"use client";

import { Toast } from "@/components/Toast";

import { Fragment, useEffect, useMemo, useState } from "react";
import { api, AthleteRating, RatingOptions, RatingsResponse } from "@/lib/api";

export default function RatingsPage() {
  const [options, setOptions] = useState<RatingOptions | null>(null);
  const [season, setSeason] = useState("");
  const [discipline, setDiscipline] = useState("");
  const [ageGroup, setAgeGroup] = useState("");
  const [minRank, setMinRank] = useState("");
  const [data, setData] = useState<RatingsResponse | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<RatingOptions>("rating-options/").then((value) => {
      setOptions(value);
      if (value.seasons[0]) setSeason(String(value.seasons[0].year));
      if (value.disciplines[0]) setDiscipline(value.disciplines[0].code);
    }).catch((failure) => setError(failure instanceof Error ? failure.message : "Не удалось загрузить фильтры"));
  }, []);

  useEffect(() => {
    if (!season || !discipline) return;
    const controller = new AbortController();
    const params = new URLSearchParams({ season, discipline });
    if (ageGroup) params.set("age_group", ageGroup);
    if (minRank) params.set("min_rank", minRank);
    api<RatingsResponse>(`ratings/?${params.toString()}`, { signal: controller.signal })
      .then((value) => { setData(value); setError(""); })
      .catch((failure) => { if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : "Не удалось загрузить рейтинг"); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [season, discipline, ageGroup, minRank]);

  const ranks = useMemo(() => [["youth_3", "III юношеский"], ["youth_2", "II юношеский"], ["youth_1", "I юношеский"], ["adult_3", "III спортивный"], ["adult_2", "II спортивный"], ["adult_1", "I спортивный"], ["cms", "КМС"], ["ms", "МС"]], []);
  return <>
    <header className="dashboard-head"><span className="kick">Результаты · опубликованные протоколы</span><h1>Рейтинг спортсменов</h1><p className="lead">Баллы рассчитываются сервером по последней опубликованной версии протокола. Каждая строка раскрывает источник и правило начисления.</p></header>
    {error && <Toast>{error}</Toast>}
    <section className="blk"><h2><b>01</b><span>Фильтры</span></h2><div className="workflow-form form-grid">
      <label className="lb">Сезон<select className="inp" value={season} onChange={(event) => setSeason(event.target.value)}><option value="">Выберите сезон</option>{options?.seasons.map((item) => <option key={item.id} value={item.year}>{item.name}</option>)}</select></label>
      <label className="lb">Дисциплина<select className="inp" value={discipline} onChange={(event) => setDiscipline(event.target.value)}><option value="">Выберите дисциплину</option>{options?.disciplines.map((item) => <option key={item.id} value={item.code}>{item.name}</option>)}</select></label>
      <label className="lb">Возрастная группа<select className="inp" value={ageGroup} onChange={(event) => setAgeGroup(event.target.value)}><option value="">Все группы</option>{options?.age_groups.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      <label className="lb">Минимальный разряд<select className="inp" value={minRank} onChange={(event) => setMinRank(event.target.value)}><option value="">Любой</option>{ranks.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
    </div></section>
    <section className="blk"><h2><b>02</b><span>Таблица</span></h2><div>
      {loading ? <p role="status">Загрузка рейтинга…</p> : !data?.items.length ? <div className="note">Для выбранных фильтров опубликованных результатов нет.</div> : <div className="tw ratings-scroll" role="region" aria-label="Рейтинг спортсменов" tabIndex={0}><table className="ratings-table"><thead><tr><th scope="col">№</th><th scope="col">Спортсмен</th><th scope="col">Дисциплина</th><th scope="col">База</th><th scope="col">Призы</th><th scope="col">Коэфф.</th><th scope="col">Рейтинг</th><th scope="col">Источник</th></tr></thead><tbody>{data.items.map((row: AthleteRating) => <Fragment key={row.id}><tr className={expanded === row.id ? "sel" : ""}><td>{row.placement}</td><td><button className="rating-athlete" type="button" onClick={() => setExpanded(expanded === row.id ? null : row.id)} aria-expanded={expanded === row.id} aria-controls={`rating-details-${row.id}`}><span>{row.athlete_name}</span><svg className="ic" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7" /></svg></button></td><td>{row.discipline_name}</td><td className="m">{row.base_score}</td><td className="m">{row.prize_count}</td><td className="m">×{row.coefficient}</td><td className="m rating-total"><strong>{row.rating_score}</strong></td><td><span className="bd in">Опубликовано</span></td></tr>{expanded === row.id && <tr className="rating-details"><td colSpan={8}><div id={`rating-details-${row.id}`}><div className="rating-breakdown">{row.breakdown.map((item) => <div className="note" key={`${row.id}-${item.publication_id}`}><strong>{item.awarded_points} б.</strong><span>{item.placement} место · {item.competition_title} · публикация v{item.publication_version}</span><small>Уровень: {item.competition_level}. Снапшот протокола #{item.publication_id}</small></div>)}</div></div></td></tr>}</Fragment>)}</tbody></table></div>}
      {data && data.pages > 1 && <div className="pag" aria-label="Пагинация"><span>Страница {data.page} из {data.pages}</span></div>}
    </div></section>
  </>;
}
