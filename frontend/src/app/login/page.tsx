"use client";

import { Toast } from "@/components/Toast";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, Me } from "@/lib/api";

export default function Login() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      await api<{ user: Me }>("auth/login/", { method: "POST", body: JSON.stringify({ email: form.get("email"), password: form.get("password") }) });
      router.push("/dashboard");
      router.refresh();
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Не удалось войти"); }
    finally { setBusy(false); }
  }
  return <section className="blk"><h2><b>01</b><span>Вход</span></h2><div><h1>Войти</h1><form className="auth-form" onSubmit={submit}><label className="lb" htmlFor="email">Электронная почта</label><input className="inp" id="email" name="email" type="email" required autoComplete="email" /><label className="lb" htmlFor="password">Пароль</label><input className="inp" id="password" name="password" type="password" required autoComplete="current-password" />{error && <Toast>{error}</Toast>}<button className="btn p" disabled={busy}>Войти</button></form><p className="form-foot">Нет аккаунта? <Link href="/register">Зарегистрироваться</Link></p></div></section>;
}
