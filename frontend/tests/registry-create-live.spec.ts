import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test("live federation creates an athlete profile for a registered consenting user", async ({ page, browser }) => {
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

  await signIn(page, "demo.federation@example.test");
  await page.getByRole("button", { name: "Федерация", exact: true }).click();
  await page.goto("/registry");
  await page.getByLabel("Поиск пользователя").fill(name);
  const option = page.getByRole("option", { name, exact: true });
  await expect(option).toHaveCount(1);
  await page.getByLabel("Существующий пользователь").selectOption({ label: name });
  const [response] = await Promise.all([
    page.waitForResponse((result) => result.url().endsWith("/api/v1/registry/profiles/athlete/") && result.request().method() === "POST"),
    page.getByRole("button", { name: "Создать профиль", exact: true }).click(),
  ]);
  expect(response.status()).toBe(201);
  const created = await response.json();
  expect(created.full_name).toBe(name);
  const eligible = await page.request.get(`/api/v1/registry/eligible-users/?role=athlete&search=${encodeURIComponent(name)}`);
  expect(eligible.ok()).toBeTruthy();
  expect((await eligible.json()).results).toHaveLength(0);
});
