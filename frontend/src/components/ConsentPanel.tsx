"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

type Consent = { id: number; text_version: string; recorded_at: string; revoked_at: string | null };
type Data = { text_version: string; history: Consent[] };

export function ConsentPanel() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [guardian, setGuardian] = useState(false);
  const [busy, setBusy] = useState(false);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    const abort = new AbortController(); controller.current = abort;
    void api<Data>("consents/", { signal: abort.signal }).then((value) => { if (!abort.signal.aborted) setData(value); }).catch(() => { if (!abort.signal.aborted) setError("Не удалось загрузить согласия"); });
    return () => abort.abort();
  }, []);
  async function update(action: "renew" | "withdraw") {
    const signal = controller.current?.signal;
    if (!signal || signal.aborted) return;
    setBusy(true); setError("");
    try {
      const value = await api<Data>("consents/", { method: "POST", signal, body: JSON.stringify({ action, consent: agreed, guardian_consent: guardian }) });
      if (!signal.aborted) { setData(value); setAgreed(false); setGuardian(false); }
    } catch (cause) { if (!signal.aborted) setError(cause instanceof Error ? cause.message : "Не удалось сохранить согласие"); }
    finally { if (!signal.aborted) setBusy(false); }
  }
  const active = data?.history[0] && !data.history[0].revoked_at;
  return <section className="blk"><h2><b>05</b><span>Согласия</span></h2><div>
    <p>Демонстрационное согласие на обработку данных для учёта спортсменов и участия в соревнованиях. Версия: {data?.text_version ?? "…"}. Проверка личности представителя через этот интерфейс не проводится.</p>
    {error && <p role="alert">{error}</p>}
    {!data ? <p role="status">Загрузка согласий…</p> : <>
      <p className="bd">{active ? "Согласие действует" : "Согласие не действует"}</p>
      {active ? <><p>После отзыва подача заявок и публикация новых протоколов с вашими данными будут заблокированы. История ранее опубликованных документов сохраняется.</p><button className="btn" disabled={busy} onClick={() => void update("withdraw")}>Отозвать согласие</button></> : <div className="workflow-stack">
        <label><input type="checkbox" checked={agreed} onChange={(event) => setAgreed(event.target.checked)} /> Подтверждаю согласие на обработку персональных данных</label>
        <label><input type="checkbox" checked={guardian} onChange={(event) => setGuardian(event.target.checked)} /> Согласие законного представителя (для несовершеннолетних)</label>
        <button className="btn p" disabled={busy || !agreed} onClick={() => void update("renew")}>Возобновить согласие</button>
      </div>}
      <details><summary>История согласий</summary><ul>{data.history.map((item) => <li key={item.id}>{item.text_version} · {new Date(item.recorded_at).toLocaleString("ru-RU")} · {item.revoked_at ? `Отозвано ${new Date(item.revoked_at).toLocaleString("ru-RU")}` : "Записано"}</li>)}</ul></details>
    </>}
  </div></section>;
}
