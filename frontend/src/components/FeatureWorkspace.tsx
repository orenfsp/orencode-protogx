"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useCurrentUser } from "@/components/AppShell";
import { api } from "@/lib/api";

export type Field = { name: string; label: string; type?: "text" | "number" | "date" | "url" | "checkbox" | "textarea"; options?: string; choices?: { value: string | number; label: string }[]; optional?: boolean };
export type Action = { label: string; path: string; fields: Field[]; roles?: string[] };
export type WorkspaceProps = { title: string; endpoint: string; columns: { key: string; label: string }[]; actions?: Action[]; publicAccess?: boolean };
type Data = { items: Record<string, unknown>[]; notice?: string; options?: Record<string, { value: string | number; label: string }[]> };

const labels: Record<string, string> = { valid: "Действительна", revoked: "Отозвана", superseded: "Заменена версия протокола", prepared: "Подготовлено", sent: "Направлено", awarded: "Назначено", submitted: "Подано", reviewing: "Рассматривается", needs_materials: "Нужны материалы", accepted: "Удовлетворено", rejected: "Отклонено", demonstration: "Демонстрация", passed: "Выполнено", failed: "Не выполнено", pending: "Ожидает", approved: "Одобрено", published: "Опубликовано", draft: "Черновик", true: "Да", false: "Нет" };
function display(value: unknown): string { if (value == null) return "—"; if (Array.isArray(value)) return value.map(display).join("; "); if (typeof value === "object") return Object.values(value).map(display).join(" · "); return labels[String(value)] ?? String(value); }

function WorkspaceBody({ title, endpoint, columns, actions = [], publicAccess = false }: WorkspaceProps) {
  const me = useCurrentUser();
  actions = actions.filter(action => !action.roles || (me?.active_role && action.roles.includes(me.active_role)));
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const [message, setMessage] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    if (me || publicAccess) api<Data>(endpoint, { signal: controller.signal }).then(setData).catch(e => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, [endpoint, revision, me, publicAccess]);

  async function submit(event: FormEvent<HTMLFormElement>, action: Action) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const body: Record<string, unknown> = {};
    for (const field of action.fields) {
      const raw = values.get(field.name);
      if (field.type === "checkbox") body[field.name] = raw === "on";
      else if (raw !== "" && raw !== null) body[field.name] = field.type === "number" ? Number(raw) : raw;
    }
    const path = action.path.replace(/\{(\w+)\}/g, (_, name) => encodeURIComponent(String(body[name])));
    setBusy(true); setError(""); setMessage("");
    try { await api(path, { method: "POST", body: JSON.stringify(body) }); setMessage("Изменения сохранены"); setRevision(r => r + 1); form.reset(); }
    catch (e) { setError(e instanceof Error ? e.message : "Не удалось сохранить"); }
    finally { setBusy(false); }
  }
  return <>
    <header className="dashboard-head"><span className="kick">ФСП · Дополнительные сервисы</span><h1>{title}</h1><Link className="btn" href="/services">Все сервисы</Link></header>
    {!me && !publicAccess ? <p className="note wn"><Link href="/login">Войдите для доступа к данным</Link></p> : <>
      {error && <div className="note wn" role="alert">{error}<button className="btn" onClick={() => { setError(""); setRevision(r => r + 1); }}>Повторить</button></div>}
      {message && <p role="status" className="note">{message}</p>}
      {!data && !error && <p role="status">Загрузка…</p>}
      {data && <><p className="note wn">{data.notice ?? "Демонстрационные данные и формы. Доступ проверяет сервер."}</p>
        <section className="blk"><h2><b>01</b><span>Данные</span></h2><div className="tw">{data.items.length ? <table><thead><tr>{columns.map(c => <th key={c.key}>{c.label}</th>)}<th>Документы</th></tr></thead><tbody>{data.items.map((item, index) => <tr key={String(item.id ?? index)}>{columns.map(c => <td key={c.key}>{display(item[c.key])}</td>)}<td>{typeof item.download_url === "string" && <a className="btn" href={item.download_url}>Скачать</a>} {typeof item.verify_url === "string" && <Link className="btn" href={item.verify_url}>Проверить</Link>}</td></tr>)}</tbody></table> : <p>Записей пока нет</p>}</div></section>
        {actions.map((action, index) => <section className="blk" key={action.label}><h2><b>{String(index+2).padStart(2,"0")}</b><span>{action.label}</span></h2><form className="workflow-form" onSubmit={event => submit(event, action)}>{action.fields.map(field => <label key={field.name}>{field.label}{field.options || field.choices ? <select name={field.name} required={!field.optional} defaultValue=""><option value="">Выберите…</option>{(field.choices ?? data.options?.[field.options!] ?? []).map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select> : field.type === "textarea" ? <textarea name={field.name} required={!field.optional} maxLength={10000}/> : <input name={field.name} type={field.type ?? "text"} required={!field.optional && field.type !== "checkbox"} min={field.type === "number" ? "0" : undefined} step={field.type === "number" ? "any" : undefined} maxLength={2000}/>}</label>)}<button className="btn p" disabled={busy}>{busy ? "Сохранение…" : action.label}</button></form></section>)}
      </>}
    </>}
  </>;
}

export function FeatureWorkspace(props: WorkspaceProps) {
  const me = useCurrentUser();
  return <WorkspaceBody key={`${me?.id ?? "guest"}:${me?.active_role ?? "none"}`} {...props}/>;
}
