export type Role = "federation" | "athlete" | "coach" | "judge";
export type Me = { id: number; email: string; full_name: string; roles: Role[]; active_role: Role | null };
export type Discipline = { code: string; name: string };

async function csrfToken(): Promise<string> {
  const response = await fetch("/api/v1/auth/csrf/", { credentials: "include" });
  if (!response.ok) throw new Error("Не удалось подготовить запрос");
  const data = await response.json();
  return data.csrfToken;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const unsafe = init?.method && !["GET", "HEAD", "OPTIONS"].includes(init.method.toUpperCase());
  const token = unsafe ? await csrfToken() : undefined;
  const response = await fetch(`/api/v1/${path}`, {
    credentials: "include",
    ...init,
    headers: { "Content-Type": "application/json", ...(token ? { "X-CSRFToken": token } : {}), ...init?.headers },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === "string" ? error.detail : JSON.stringify(error));
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
