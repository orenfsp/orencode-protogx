"use client";
import { useEffect, useState } from "react";
import { useCurrentUser } from "@/components/AppShell";
import { api } from "@/lib/api";
export default function NotificationsPage() {
  const me = useCurrentUser();
  const [result, setResult] = useState<{owner:number;items:{id:number;title:string;created_at:string}[]}|null>(null);
  const [error,setError] = useState("");
  useEffect(() => { const controller = new AbortController(); if (me) api<{id:number;title:string;created_at:string}[]>("notifications/",{signal:controller.signal}).then(items=>setResult({owner:me.id,items})).catch(e=>{if(!controller.signal.aborted)setError(e.message);}); return ()=>controller.abort(); },[me]);
  return <><header className="dashboard-head"><h1>Уведомления</h1></header>{error&&<p role="alert">{error}</p>}{!me?<p>Войдите в кабинет</p>:result?.owner===me.id?<ul>{result.items.map(n=><li key={n.id}>{n.title} · {new Date(n.created_at).toLocaleDateString("ru-RU")}</li>)}</ul>:<p role="status">Загрузка…</p>}</>;
}
