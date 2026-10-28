"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useCurrentUser } from "@/components/AppShell";
import { api, apiForm, ApiError } from "@/lib/api";

type Option = { value: string | number; label: string };
export type Field = { name: string; label: string; type?: "text" | "number" | "date" | "datetime-local" | "url" | "checkbox" | "textarea" | "file"; options?: string; choices?: Option[]; optional?: boolean; array?: boolean };
export type Action = { label: string; path: string; fields: Field[]; roles?: string[]; method?: "POST" | "PUT" };
export type WorkspaceProps = { title: string; endpoint: string; columns: { key: string; label: string }[]; actions?: Action[]; publicAccess?: boolean };
type Data = { items: Record<string, unknown>[]; notice?: string; options?: Record<string, Option[]> };
type Saved = { token?: string; webhook_secret?: string; client_secret?: string; client_id?: string };
const labels: Record<string, string> = { valid: "Действительна", revoked: "Отозвана", superseded: "Заменена версия протокола", prepared: "Подготовлено", sent: "Направлено", awarded: "Назначено", submitted: "Подано", reviewing: "Рассматривается", needs_materials: "Нужны материалы", accepted: "Удовлетворено", rejected: "Отклонено", demonstration: "Демонстрация", passed: "Выполнено", failed: "Не выполнено", pending: "Ожидает", approved: "Одобрено", published: "Опубликовано", draft: "Черновик", active: "Действует", expired: "Истёк срок", staged: "На рассмотрении", rolled_back: "Импорт отменён", true: "Да", false: "Нет" };
function safeLink(value: string) { return /^\/(?!\/)|^https?:\/\//i.test(value); }
function nestedBody(flat: Record<string, unknown>): Record<string, unknown> {
  const output: Record<string, unknown> = {};
  for (const [name,value] of Object.entries(flat)) {
    const parts=name.split(".");
    let cursor: Record<string, unknown> = output;
    for (let i=0;i<parts.length-1;i++) {
      const part=parts[i];
      if (!(part in cursor)) cursor[part]=/^\d+$/.test(parts[i+1]) ? [] : {};
      cursor=cursor[part] as Record<string,unknown>;
    }
    cursor[parts[parts.length-1]]=value;
  }
  return output;
}
function Cell({ value }: { value: unknown }) {
  if (value == null) return <>—</>;
  if (Array.isArray(value)) return <>{value.map((entry, i) => <div key={i}><Cell value={entry}/></div>)}</>;
  if (typeof value === "object") return <>{Object.entries(value).map(([key, entry]) => <div key={key}>{key === "download_url" && typeof entry === "string" && safeLink(entry) ? <a className="btn" href={entry}>Скачать доказательство</a> : <Cell value={entry}/>}</div>)}</>;
  if (typeof value === "string" && safeLink(value)) return <a href={value} rel="noreferrer">Открыть источник</a>;
  return <>{labels[String(value)] ?? String(value)}</>;
}

function FieldControl({ field, data }: { field: Field; data: Data }) {
  const choices = field.choices ?? data.options?.[field.options ?? ""] ?? [];
  if (field.options || field.choices) return <select className="inp" aria-label={field.label} name={field.name} multiple={field.array} required={!field.optional} defaultValue={field.array ? [] : ""}>
    {!field.array && <option value="">Выберите…</option>}{choices.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
  </select>;
  if (field.type === "textarea") return <textarea className="inp" aria-label={field.label} name={field.name} required={!field.optional} maxLength={10000}/>;
  return <input className={field.type === "checkbox" ? undefined : "inp"} aria-label={field.label} name={field.name} type={field.type ?? "text"} required={!field.optional && field.type !== "checkbox"} min={field.type === "number" ? "0" : undefined} step={field.type === "number" ? "any" : undefined} maxLength={2000} accept={field.type === "file" ? ".png,.jpg,.jpeg,.txt" : undefined}/>;
}

function WorkspaceBody({ title, endpoint, columns, actions = [], publicAccess = false }: WorkspaceProps) {
  const me = useCurrentUser();
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const [message, setMessage] = useState("");
  const visibleActions = actions.filter(action => !action.roles || (me?.active_role && action.roles.includes(me.active_role)));
  useEffect(() => {
    const controller = new AbortController();
    if (me || publicAccess) api<Data>(endpoint, { signal: controller.signal }).then(setData).catch(e => { if (!controller.signal.aborted) { setError(e.message); if (e instanceof ApiError && [401,403].includes(e.status)) setData(null); } });
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
      else if (field.array) body[field.name] = field.options || field.choices ? values.getAll(field.name) : raw ? [String(raw)] : [];
      else if (raw !== "" && raw !== null && field.type !== "file") body[field.name] = field.type === "number" ? Number(raw) : field.type === "datetime-local" ? new Date(String(raw)).toISOString() : raw;
    }
    const path = action.path.replace(/\{(\w+)\}/g, (_, name) => encodeURIComponent(String(body[name])));
    setBusy(true); setError(""); setMessage("");
    try {
      const result = action.fields.some(f => f.type === "file") ? await apiForm<Saved>(path, values) : await api<Saved>(path, { method: action.method ?? "POST", body: JSON.stringify(nestedBody(body)) });
      setMessage(result?.token ? `Сохраните токен сейчас: ${result.token}${result.webhook_secret ? `; секрет вебхука: ${result.webhook_secret}` : ""}. Повторно они не показываются.` : result?.client_secret ? `Client ID: ${result.client_id}. Сохраните секрет клиента сейчас: ${result.client_secret}` : "Изменения сохранены");
      setRevision(r => r + 1); form.reset();
    } catch (e) { setError(e instanceof Error ? e.message : "Не удалось сохранить"); if (e instanceof ApiError && [401,403].includes(e.status)) setData(null); }
    finally { setBusy(false); }
  }
  return <>
    <header className="dashboard-head"><span className="kick">ФСП · Дополнительные сервисы</span><h1>{title}</h1><Link className="btn" href="/services">Все сервисы</Link></header>
    {!me && !publicAccess ? <p className="note wn"><Link href="/login">Войдите для доступа к данным</Link></p> : <>
      {error && <div className="note wn" role="alert">{error}<button className="btn" onClick={() => { setError(""); setRevision(r => r + 1); }}>Повторить</button></div>}
      {message && <p role="status" className="note" style={{ overflowWrap: "anywhere" }}>{message}</p>}
      {!data && !error && <p role="status">Загрузка…</p>}
      {data && <><p className="note wn">{data.notice ?? "Демонстрационные данные и формы. Доступ проверяет сервер."}</p>
        <section className="blk"><h2><b>01</b><span>Данные</span></h2><div className="tw">{data.items.length ? <table><thead><tr>{columns.map(c => <th key={c.key}>{c.label}</th>)}<th>Документы</th></tr></thead><tbody>{data.items.map((item, index) => <tr key={String(item.id ?? index)}>{columns.map(c => <td key={c.key}><Cell value={item[c.key]}/></td>)}<td>{typeof item.download_url === "string" && safeLink(item.download_url) && <a className="btn" href={item.download_url}>Скачать</a>} {typeof item.verify_url === "string" && safeLink(item.verify_url) && <Link className="btn" href={item.verify_url}>Проверить</Link>}</td></tr>)}</tbody></table> : <p>Записей пока нет</p>}</div></section>
        {visibleActions.map((action, index) => <section className="blk" key={action.label}><h2><b>{String(index+2).padStart(2,"0")}</b><span>{action.label}</span></h2><form className="workflow-form" onSubmit={event => submit(event, action)}>{action.fields.map(field => <label key={field.name}>{field.label}<FieldControl field={field} data={data}/></label>)}<button className="btn p" disabled={busy}>{busy ? "Сохранение…" : action.label}</button></form></section>)}
      </>}
    </>}
  </>;
}

export function FeatureWorkspace(props: WorkspaceProps) {
  const me = useCurrentUser();
  return <WorkspaceBody key={`${me?.id ?? "guest"}:${me?.active_role ?? "none"}:${props.endpoint}`} {...props}/>;
}
