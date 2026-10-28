"use client";

import { Toast } from "@/components/Toast";

import { FormEvent, useState } from "react";
import { api, Application, ProtocolTemplate, Result } from "@/lib/api";

export function ResultEditor({ application, template, current, onSaved }: { application: Application; template: ProtocolTemplate; current?: Result; onSaved: () => void }) {
  const [resultStatus, setResultStatus] = useState<Result["status"]>(current?.status ?? "classified");
  const [place, setPlace] = useState(current?.place ? String(current.place) : "");
  const [score, setScore] = useState(current?.score ?? "");
  const [metrics, setMetrics] = useState<Record<string, string>>(Object.fromEntries(Object.entries(current?.metrics ?? {}).map(([key, value]) => [key, String(value)])));
  const [error, setError] = useState("");
  async function save(event: FormEvent) {
    event.preventDefault(); setError("");
    try {
      const classified = resultStatus === "classified";
      const values = classified ? Object.fromEntries(template.metric_fields.filter((field) => metrics[field.key]).map((field) => [field.key, field.type === "number" ? Number(metrics[field.key]) : metrics[field.key]])) : {};
      await api("results/", { method: "POST", body: JSON.stringify({ application: application.id, status: resultStatus, place: classified && place ? Number(place) : null, score: classified && score ? score : null, metrics: values }) });
      onSaved();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Не удалось записать результат"); }
  }
  return <form className="workflow-form result-editor" onSubmit={save}>
    <strong>{application.athlete_name}</strong>
    <div className="form-grid"><label className="lb">Статус<select className="inp" value={resultStatus} onChange={(event) => setResultStatus(event.target.value as Result["status"])}><option value="classified">Классифицирован</option><option value="no_show">Не явился</option><option value="unclassified">Без результата</option><option value="disqualified">Дисквалифицирован</option></select></label>
    {resultStatus === "classified" && <><label className="lb">Место<input className="inp" type="number" min="1" value={place} onChange={(event) => setPlace(event.target.value)} /></label><label className="lb">Баллы<input className="inp" type="number" step="0.001" value={score} onChange={(event) => setScore(event.target.value)} /></label>{template.metric_fields.map((field) => <label className="lb" key={field.key}>{field.label}<input className="inp" type={field.type === "number" ? "number" : "text"} step={field.type === "number" ? "any" : undefined} required={field.required} value={metrics[field.key] ?? ""} onChange={(event) => setMetrics({ ...metrics, [field.key]: event.target.value })} /></label>)}</>}
    </div>{error && <Toast>{error}</Toast>}<button className="btn" type="submit">{current ? "Исправить результат" : "Записать результат"}</button>
  </form>;
}
