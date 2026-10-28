"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Check = { status: string; number: string; competition?: string; date?: string; athlete?: string; version?: number };
export default function VerifyPage() {
  const [data, setData] = useState<Check | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const code = new URLSearchParams(window.location.search).get("code");
    const controller = new AbortController();
    if (!code || !/^[0-9a-f-]{36}$/i.test(code)) { queueMicrotask(() => setError("Некорректный код справки")); return; }
    api<Check>(`certificates/verify/${code}/`, { signal: controller.signal }).then(setData).catch(e => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, []);
  return <><header className="dashboard-head"><h1>Проверка справки</h1></header><section className="blk"><h2><b>QR</b><span>Подлинность</span></h2><div>{error ? <p role="alert" className="note wn">{error}</p> : data ? <><p className="bd">{data.status === "valid" ? "Действительна" : data.status === "superseded" ? "Заменена версия протокола" : "Отозвана"}</p><p>{data.number}</p>{data.competition && <p>{data.competition} · {data.date} · протокол v{data.version}</p>}{data.athlete && <p>{data.athlete}</p>}<p className="note wn">Проверка записи в платформе. Демонстрационная форма.</p></> : <p role="status">Проверяем…</p>}</div></section></>;
}
