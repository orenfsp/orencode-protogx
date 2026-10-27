"use client";

import { FormEvent, useState } from "react";
import { api, Discipline, MetricField, ProtocolTemplate } from "@/lib/api";

export function TemplateEditor({ disciplines, onSaved }: { disciplines: Discipline[]; onSaved: (template: ProtocolTemplate) => void }) {
  const [discipline, setDiscipline] = useState("");
  const [name, setName] = useState("");
  const [competitionType, setCompetitionType] = useState("");
  const [ruleVersion, setRuleVersion] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState("");
  const [fields, setFields] = useState<MetricField[]>([]);
  const [baseColumns, setBaseColumns] = useState(["athlete", "age_group", "status", "place", "score"]);
  const [sections, setSections] = useState(["header", "participants", "judges", "signatures"]);
  const [signatureRoles, setSignatureRoles] = useState("Главный судья, Секретарь");
  const [sortKey, setSortKey] = useState("place");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
  const [sourceUrl, setSourceUrl] = useState("https://sudact.ru/law/pravila-vida-sporta-sportivnoe-programmirovanie-utv-prikazom/prilozhenie-n-5/rekomenduemyi-obrazets-protokola-po-programmirovaniiu/");
  const [sourceNote, setSourceNote] = useState("");
  const [error, setError] = useState("");
  const optional = [{ key: "age_group", label: "Возрастная группа" }, { key: "place", label: "Место" }, { key: "score", label: "Баллы" }];
  function update(index: number, patch: Partial<MetricField>) { setFields(fields.map((field, i) => i === index ? { ...field, ...patch } : field)); }
  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    try {
      const columns = ["athlete", ...baseColumns.filter((item) => item !== "athlete" && item !== "status"), "status", ...fields.map((field) => field.key)];
      const saved = await api<ProtocolTemplate>("templates/", { method: "POST", body: JSON.stringify({ discipline: Number(discipline), name, competition_type: competitionType, rule_version: ruleVersion, effective_from: effectiveFrom || null, metric_fields: fields, columns, sections, signature_roles: sections.includes("signatures") ? signatureRoles.split(",").map((item) => item.trim()).filter(Boolean) : [], sort: { key: sortKey, direction: sortDirection }, source_url: sourceUrl, source_note: sourceNote }) });
      onSaved(saved); setName(""); setCompetitionType(""); setRuleVersion(""); setEffectiveFrom(""); setFields([]); setSourceNote("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось сохранить шаблон"); }
  }
  return <form className="workflow-form" onSubmit={submit}>
    <label className="lb">Дисциплина<select className="inp" required value={discipline} onChange={(event) => setDiscipline(event.target.value)}><option value="">Выберите</option>{disciplines.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
    <label className="lb">Название версии<input className="inp" required value={name} onChange={(event) => setName(event.target.value)} /></label>
    <div className="form-grid"><label className="lb">Вид соревнования (если только для него)<input className="inp" value={competitionType} onChange={(event) => setCompetitionType(event.target.value)} /></label><label className="lb">Версия правил<input className="inp" value={ruleVersion} onChange={(event) => setRuleVersion(event.target.value)} /></label><label className="lb">Действует с<input className="inp" type="date" value={effectiveFrom} onChange={(event) => setEffectiveFrom(event.target.value)} /></label></div>
    <fieldset className="workflow-fieldset"><legend>Колонки протокола</legend><div className="option-row"><span className="bd">Спортсмен</span><span className="bd">Статус</span>{optional.map((item) => <label className="ck" key={item.key}><input type="checkbox" checked={baseColumns.includes(item.key)} onChange={(event) => setBaseColumns(event.target.checked ? [...baseColumns, item.key] : baseColumns.filter((key) => key !== item.key))} />{item.label}</label>)}</div></fieldset>
    <fieldset className="workflow-fieldset"><legend>Поля дисциплины</legend>{fields.map((field, index) => <div className="form-grid stage-row" key={index}><label className="lb">Код поля<input className="inp" required pattern="[A-Za-z_][A-Za-z0-9_]*" value={field.key} onChange={(event) => update(index, { key: event.target.value })} /></label><label className="lb">Название колонки<input className="inp" required value={field.label} onChange={(event) => update(index, { label: event.target.value })} /></label><label className="lb">Тип<select className="inp" value={field.type} onChange={(event) => update(index, { type: event.target.value as MetricField["type"] })}><option value="number">Число</option><option value="string">Текст</option></select></label><label className="ck"><input type="checkbox" checked={field.required} onChange={(event) => update(index, { required: event.target.checked })} />Обязательное поле</label><button className="btn" type="button" onClick={() => setFields(fields.filter((_, i) => i !== index))}>Удалить поле</button></div>)}<button className="btn" type="button" onClick={() => setFields([...fields, { key: "", label: "", type: "number", required: false }])}>Добавить поле</button></fieldset>
    <fieldset className="workflow-fieldset"><legend>Разделы</legend><div className="option-row"><span className="bd">Заголовок</span><span className="bd">Участники</span>{[{ key: "judges", label: "Судьи" }, { key: "signatures", label: "Поля подписей" }].map((item) => <label className="ck" key={item.key}><input type="checkbox" checked={sections.includes(item.key)} onChange={(event) => setSections(event.target.checked ? [...sections, item.key] : sections.filter((key) => key !== item.key))} />{item.label}</label>)}</div></fieldset>
    <label className="lb">Сортировка<select className="inp" value={sortKey} onChange={(event) => setSortKey(event.target.value)}>{["athlete", ...baseColumns.filter((key) => key !== "athlete"), ...fields.map((field) => field.key).filter(Boolean)].map((key) => <option key={key} value={key}>{key}</option>)}</select></label>
    <label className="lb">Направление<select className="inp" value={sortDirection} onChange={(event) => setSortDirection(event.target.value as "asc" | "desc")}><option value="asc">По возрастанию</option><option value="desc">По убыванию</option></select></label>
    {sections.includes("signatures") && <label className="lb">Должности для подписей (через запятую)<input className="inp" value={signatureRoles} onChange={(event) => setSignatureRoles(event.target.value)} /></label>}
    <label className="lb">Ссылка на источник образца<input className="inp" type="url" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} /></label>
    <label className="lb">Примечание об источнике<input className="inp" value={sourceNote} onChange={(event) => setSourceNote(event.target.value)} placeholder="Что нужно сверить с первоисточником" /></label>
    <div className="note wn">Новая версия остаётся демо-шаблоном до проверки действующих правил и первоисточника.</div>
    {error && <div className="note wn" role="alert">{error}</div>}<button className="btn p" type="submit">Создать версию шаблона</button>
  </form>;
}
