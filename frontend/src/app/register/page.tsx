"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, Me } from "@/lib/api";

export default function Register() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [minor, setMinor] = useState(false);
  function updateAge(value: string) {
    if (!value) { setMinor(false); return; }
    const born = new Date(`${value}T12:00:00`);
    const now = new Date();
    const eighteen = new Date(born); eighteen.setFullYear(born.getFullYear() + 18);
    setMinor(eighteen > now);
  }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true); setError("");
    const form = new FormData(event.currentTarget);
    const body = { email: form.get("email"), password: form.get("password"), full_name: form.get("full_name"), date_of_birth: form.get("date_of_birth"), consent: form.get("consent") === "on", consent_version: "v1-demo-2026-10-27", guardian_name: form.get("guardian_name") || "", guardian_relationship: form.get("guardian_relationship") || "", guardian_consent: form.get("guardian_consent") === "on" };
    try {
      await api<{ user: Me }>("auth/register/", { method: "POST", body: JSON.stringify(body) });
      router.push("/dashboard"); router.refresh();
    } catch (failure) { setError(failure instanceof Error ? failure.message : "Не удалось зарегистрироваться"); }
    finally { setBusy(false); }
  }
  return <section className="blk"><h2><b>02</b><span>Регистрация</span></h2><div><h1>Начните здесь.</h1><form className="auth-form" onSubmit={submit}><label className="lb" htmlFor="full_name">ФИО</label><input className="inp" id="full_name" name="full_name" required autoComplete="name" /><label className="lb" htmlFor="email">Электронная почта</label><input className="inp" id="email" name="email" type="email" required autoComplete="email" /><label className="lb" htmlFor="date_of_birth">Дата рождения</label><input className="inp" id="date_of_birth" name="date_of_birth" type="date" required onChange={(event) => updateAge(event.target.value)} /><label className="lb" htmlFor="password">Пароль</label><input className="inp" id="password" name="password" type="password" required minLength={8} autoComplete="new-password" /><label className="ck"><input type="checkbox" name="consent" required />Согласие на обработку персональных данных (<Link href="/privacy" target="_blank">текст</Link>)</label>{minor && <fieldset className="guardian"><legend>Законный представитель</legend><label className="lb" htmlFor="guardian_name">ФИО представителя</label><input className="inp" id="guardian_name" name="guardian_name" required /><label className="lb" htmlFor="guardian_relationship">Степень родства</label><input className="inp" id="guardian_relationship" name="guardian_relationship" required /><label className="ck"><input type="checkbox" name="guardian_consent" required />Подтверждаю согласие представителя</label><small>Подтверждение будет ожидать проверки федерацией.</small></fieldset>}{error && <div className="note wn" role="alert">{error}</div>}<button className="btn p" disabled={busy}>Создать аккаунт</button></form><p className="form-foot">Уже есть аккаунт? <Link href="/login">Войти</Link></p></div></section>;
}
