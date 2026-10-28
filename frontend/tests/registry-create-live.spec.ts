import { execFileSync, spawnSync } from "node:child_process";
import path from "node:path";
import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test("live federation creates athlete, coach and judge profiles for a registered consenting user", async ({ page, browser }) => {
  test.setTimeout(240000);
  const name = `Демо участник ${Date.now()}`;
  const email = `registry-${Date.now()}@example.test`;
  const candidateContext = await browser.newContext();
  const candidate = await candidateContext.newPage();
  await candidate.goto("/register");
  await candidate.getByLabel("ФИО").fill(name);
  await candidate.getByLabel("Электронная почта").fill(email);
  await candidate.getByLabel("Дата рождения").fill("2000-01-01");
  await candidate.getByLabel("Пароль", { exact: true }).fill("DemoOnly2026!");
  await candidate.getByRole("checkbox", { name: /Согласие на обработку/ }).check();
  await candidate.getByRole("button", { name: "Создать аккаунт" }).click();
  await expect(candidate).toHaveURL(/\/dashboard$/, { timeout: 20000 });
  await candidateContext.close();

  // Test setup assigns existing non-federation roles only inside the guarded local demo database.
  // Consent itself comes from the normal registration workflow above.
  const project = process.env.FSP_E2E_COMPOSE_PROJECT || process.env.COMPOSE_PROJECT_NAME;
  if (!project || !/^[a-z0-9][a-z0-9_-]*$/.test(project)) throw new Error("Set FSP_E2E_COMPOSE_PROJECT to the isolated local Compose project");
  const fixture = [
    "import os",
    "from django.conf import settings",
    "from apps.accounts.models import User, UserRole",
    "if not (settings.DEBUG and os.environ.get('DEMO_SEED_ENABLED') == '1' and os.environ.get('DEMO_ENVIRONMENT') == 'local'): raise RuntimeError('Local demo flags required')",
    "if settings.DATABASES['default'].get('HOST', '') not in ('', 'db', 'localhost', '127.0.0.1', '::1'): raise RuntimeError('Local database host required')",
    `user = User.objects.get(email=${JSON.stringify(email)})`,
    "UserRole.objects.get_or_create(user=user, role='coach')",
    "UserRole.objects.get_or_create(user=user, role='judge')",
  ].join("\n");
  const denied = spawnSync("docker", ["compose", "-p", project, "exec", "-T", "-e", "DEMO_ENVIRONMENT=production", "api", "python", "manage.py", "shell", "-c", fixture], {
    cwd: path.resolve(process.cwd(), ".."), timeout: 30000, encoding: "utf8",
  });
  expect(denied.error).toBeUndefined();
  expect(denied.status).not.toBeNull();
  expect(denied.status).not.toBe(0);
  expect(denied.stderr).toContain("Local demo flags required");
  execFileSync("docker", ["compose", "-p", project, "exec", "-T", "api", "python", "manage.py", "shell", "-c", fixture], {
    cwd: path.resolve(process.cwd(), ".."), timeout: 30000, stdio: "pipe",
  });

  await signIn(page, "demo.federation@example.test");
  await page.getByRole("button", { name: "Федерация", exact: true }).click();
  await page.goto("/registry");
  for (const [role, label] of [["athlete", "Спортсмены"], ["coach", "Тренеры"], ["judge", "Судьи"]] as const) {
    await page.getByRole("button", { name: label, exact: true }).click();
    await page.getByLabel("Поиск пользователя").fill(name);
    await expect(page.getByRole("option", { name, exact: true })).toHaveCount(1);
    await page.getByLabel("Существующий пользователь").selectOption({ label: name });
    const [response] = await Promise.all([
      page.waitForResponse((result) => result.url().endsWith(`/api/v1/registry/profiles/${role}/`) && result.request().method() === "POST"),
      page.getByRole("button", { name: "Создать профиль", exact: true }).click(),
    ]);
    expect(response.status()).toBe(201);
    expect((await response.json()).full_name).toBe(name);
    const eligible = await page.request.get(`/api/v1/registry/eligible-users/?role=${role}&search=${encodeURIComponent(name)}`);
    expect(eligible.ok()).toBeTruthy();
    expect((await eligible.json()).results).toHaveLength(0);
  }
});
