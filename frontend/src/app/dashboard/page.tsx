"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Me } from "@/lib/api";

export default function Dashboard() {
  const [me, setMe] = useState<Me | null>(null);
  useEffect(() => { api<Me>("auth/me/").then(setMe).catch(() => setMe(null)); }, []);
  return <section className="blk"><h2><b>04</b><span>Кабинет</span></h2><div>{me ? <><h1>{me.full_name}</h1><p>Активная роль: {me.active_role ?? "не выбрана"}</p><p>Доступные роли: {me.roles.join(", ")}</p></> : <div className="note wn">Для доступа к кабинету <Link href="/login">войдите</Link>.</div>}</div></section>;
}
