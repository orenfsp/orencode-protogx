"use client";

import { Toast } from "@/components/Toast";

import { FormEvent, useEffect, useState } from "react";
import { AgeGroup, api, CalendarEntry, Competition, CompetitionStage, Discipline, ProtocolTemplate } from "@/lib/api";

type Props = { initial?: Competition; disciplines: Discipline[]; groups: AgeGroup[]; templates: ProtocolTemplate[]; calendar: CalendarEntry[]; onSaved: (competition: Competition) => void };
type Form = { title: string; discipline: string; age_groups: number[]; level: string; competition_type: string; format: Competition["format"]; starts_at: string; ends_at: string; registration_deadline: string; age_reference_date: string; allow_ties: boolean; location: string; regulations: string; calendar_entry: string; template: string; stages: CompetitionStage[] };
const asLocal = (value: string) => { if (!value) return ""; const date = new Date(value); return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16); };
const empty: Form = { title: "", discipline: "", age_groups: [], level: "", competition_type: "", format: "online", starts_at: "", ends_at: "", registration_deadline: "", age_reference_date: "", allow_ties: false, location: "", regulations: "", calendar_entry: "", template: "", stages: [] };

export function CompetitionEditor({ initial, disciplines, groups, templates, calendar, onSaved }: Props) {
  const [form, setForm] = useState<Form>(() => initial ? { title: initial.title, discipline: String(initial.discipline), age_groups: initial.age_groups, level: initial.level, competition_type: initial.competition_type, format: initial.format, starts_at: asLocal(initial.starts_at), ends_at: asLocal(initial.ends_at), registration_deadline: asLocal(initial.registration_deadline), age_reference_date: initial.age_reference_date, allow_ties: initial.allow_ties, location: initial.location, regulations: initial.regulations, calendar_entry: initial.calendar_entry ? String(initial.calendar_entry) : "", template: String(initial.template), stages: initial.stages.map((stage) => ({ ...stage, starts_at: asLocal(stage.starts_at), ends_at: asLocal(stage.ends_at) })) } : empty);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [types, setTypes] = useState<{ id: number; name: string; is_active: boolean }[]>([]);
  useEffect(() => {
    const abort = new AbortController();
    void api<typeof types>("competition-types/", { signal: abort.signal }).then((value) => { if (!abort.signal.aborted) setTypes(value); }).catch(() => {});
    return () => abort.abort();
  }, []);
  const set = <K extends keyof Form>(key: K, value: Form[K]) => setForm((current) => ({ ...current, [key]: value }));
  const matchingTemplates = templates.filter((template) => String(template.discipline) === form.discipline && (!template.competition_type || template.competition_type === form.competition_type) && (!template.effective_from || !form.starts_at || template.effective_from <= form.starts_at.slice(0, 10)));
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(""); setBusy(true);
    try {
      const body = { ...form, discipline: Number(form.discipline), template: Number(form.template), calendar_entry: form.calendar_entry ? Number(form.calendar_entry) : null, starts_at: new Date(form.starts_at).toISOString(), ends_at: new Date(form.ends_at).toISOString(), registration_deadline: new Date(form.registration_deadline).toISOString(), stages: form.format === "hybrid" ? form.stages.map((stage) => ({ ...stage, starts_at: new Date(stage.starts_at).toISOString(), ends_at: new Date(stage.ends_at).toISOString() })) : [] };
      const saved = await api<Competition>(initial ? `competitions/${initial.id}/` : "competitions/", { method: initial ? "PATCH" : "POST", body: JSON.stringify(body) });
      onSaved(saved);
      if (!initial) setForm(empty);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось сохранить соревнование"); }
    finally { setBusy(false); }
  }
  return <form className="workflow-form" onSubmit={submit}>
    <label className="lb">Название<input className="inp" required value={form.title} onChange={(event) => set("title", event.target.value)} /></label>
    <div className="form-grid">
      <label className="lb">Дисциплина<select className="inp" required value={form.discipline} onChange={(event) => { setForm((current) => ({ ...current, discipline: event.target.value, template: "" })); }}><option value="">Выберите</option>{disciplines.map((item) => <option key={item.code} value={item.id}>{item.name}</option>)}</select></label>
      <label className="lb">Шаблон протокола<select className="inp" required value={form.template} onChange={(event) => set("template", event.target.value)}><option value="">Выберите</option>{matchingTemplates.map((item) => <option key={item.id} value={item.id}>{item.name} · v{item.version}{item.rule_version ? ` · правила ${item.rule_version}` : ""}</option>)}</select></label>
      <label className="lb">Уровень<input className="inp" required value={form.level} onChange={(event) => set("level", event.target.value)} /></label>
      <label className="lb">Вид соревнования<input className="inp" list="competition-type-options" required value={form.competition_type} onChange={(event) => set("competition_type", event.target.value)} /><datalist id="competition-type-options">{types.filter((item) => item.is_active).map((item) => <option key={item.id} value={item.name} />)}</datalist></label>
      <label className="lb">Формат<select className="inp" value={form.format} onChange={(event) => set("format", event.target.value as Form["format"])}><option value="online">Онлайн</option><option value="in_person">Очное</option><option value="hybrid">Гибридное</option></select></label>
      <label className="lb">Место<input className="inp" required value={form.location} onChange={(event) => set("location", event.target.value)} /></label>
      <label className="lb">Начало<input className="inp" type="datetime-local" required value={form.starts_at} onChange={(event) => set("starts_at", event.target.value)} /></label>
      <label className="lb">Конец<input className="inp" type="datetime-local" required value={form.ends_at} onChange={(event) => set("ends_at", event.target.value)} /></label>
      <label className="lb">Приём заявок до<input className="inp" type="datetime-local" required value={form.registration_deadline} onChange={(event) => set("registration_deadline", event.target.value)} /></label>
      <label className="lb">Возраст определяется на дату<input className="inp" type="date" required value={form.age_reference_date} onChange={(event) => set("age_reference_date", event.target.value)} /></label>
      <label className="lb">Календарная запись<select className="inp" value={form.calendar_entry} onChange={(event) => set("calendar_entry", event.target.value)}><option value="">Без ссылки</option>{calendar.map((item) => <option key={item.id} value={item.id}>{item.source.toUpperCase()} {item.entry_number} · {item.title}</option>)}</select></label>
    </div>
    <label className="ck"><input type="checkbox" checked={form.allow_ties} onChange={(event) => set("allow_ties", event.target.checked)} />Разрешить одинаковые места по положению</label>
    <fieldset className="workflow-fieldset"><legend>Возрастные группы</legend><div className="option-row">{groups.map((group) => <label key={group.id} className="ck"><input type="checkbox" checked={form.age_groups.includes(group.id)} onChange={(event) => set("age_groups", event.target.checked ? [...form.age_groups, group.id] : form.age_groups.filter((id) => id !== group.id))} />{group.name}</label>)}</div></fieldset>
    {form.format === "hybrid" && <fieldset className="workflow-fieldset"><legend>Этапы</legend>{form.stages.map((stage, index) => <div className="form-grid stage-row" key={index}>
      <label className="lb">Этап {index + 1}<input className="inp" required value={stage.name} onChange={(event) => set("stages", form.stages.map((item, i) => i === index ? { ...item, name: event.target.value } : item))} /></label>
      <label className="lb">Формат<select className="inp" value={stage.format} onChange={(event) => set("stages", form.stages.map((item, i) => i === index ? { ...item, format: event.target.value as CompetitionStage["format"] } : item))}><option value="online">Онлайн</option><option value="in_person">Очное</option></select></label>
      <label className="lb">Начало<input className="inp" required type="datetime-local" value={stage.starts_at} onChange={(event) => set("stages", form.stages.map((item, i) => i === index ? { ...item, starts_at: event.target.value } : item))} /></label>
      <label className="lb">Конец<input className="inp" required type="datetime-local" value={stage.ends_at} onChange={(event) => set("stages", form.stages.map((item, i) => i === index ? { ...item, ends_at: event.target.value } : item))} /></label>
      <button className="btn" type="button" onClick={() => set("stages", form.stages.filter((_, i) => i !== index).map((item, i) => ({ ...item, order: i + 1 })))}>Удалить этап</button>
    </div>)}<button className="btn" type="button" onClick={() => set("stages", [...form.stages, { order: form.stages.length + 1, name: "", format: "online", starts_at: form.starts_at, ends_at: form.ends_at }])}>Добавить этап</button></fieldset>}
    <label className="lb">Положение<textarea className="inp" required rows={5} value={form.regulations} onChange={(event) => set("regulations", event.target.value)} /></label>
    {error && <Toast>{error}</Toast>}
    <button className="btn p" type="submit" disabled={busy}>{busy ? "Сохранение…" : initial ? "Сохранить изменения" : "Создать черновик"}</button>
  </form>;
}
