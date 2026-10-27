import { expect, test } from "@playwright/test";

test("regional teams page supports manual selection and document actions", async ({ page }) => {
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: { id: 1, email: "demo.federation@example.test", full_name: "Демо Федерация", roles: ["federation"], active_role: "federation" } }));
  await page.route("**/api/v1/teams/options/", (route) => route.fulfill({ json: {
    seasons: [{ id: 1, year: 2026, name: "Сезон 2026" }],
    disciplines: [{ id: 1, code: "algorithmic", name: "Алгоритмическое программирование" }],
    age_groups: [{ id: 1, name: "Взрослые", min_age: 18, max_age: 35 }],
  } }));
  const team = { id: 1, name: "Демо-команда", region: "Оренбургская область", status: "draft", season: 1, season_year: 2026, discipline: 1, discipline_code: "algorithmic", discipline_name: "Алгоритмическое программирование", age_group: 1, age_group_name: "Взрослые", created_by: 1, created_at: "2026-01-01", updated_at: "2026-01-01", member_count: 0, members: [] };
  await page.route("**/api/v1/teams/?**", (route) => route.fulfill({ json: [team] }));
  await page.route("**/api/v1/teams/1/candidates/", (route) => route.fulfill({ json: [{ id: 2, full_name: "Демо Спортсмен", email: "demo.athlete@example.test", eligible: true, selected: false, eligibility: { age: 26, consent: true, guardian_verified: true, restriction: null, rating_score: null }, rating: null }] }));
  await page.goto("/teams");
  await expect(page.getByRole("heading", { name: "Региональные команды" })).toBeVisible();
  await page.getByRole("button", { name: "Демо-команда" }).click();
  await expect(page.getByText("Демо Спортсмен")).toBeVisible();
  await expect(page.getByRole("button", { name: "Скачать состав PDF" })).toBeVisible();
});

test("team data is hidden while an active-role switch is pending", async ({ page }) => {
  let releaseSwitch: (() => void) | undefined;
  const gate = new Promise<void>((resolve) => { releaseSwitch = resolve; });
  const user = { id: 1, email: "demo.federation@example.test", full_name: "Демо", roles: ["federation", "athlete"], active_role: "federation" };
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
  await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "test" } }));
  await page.route("**/api/v1/auth/active-role/", async (route) => { await gate; await route.fulfill({ json: { ...user, active_role: "athlete" } }); });
  await page.route("**/api/v1/teams/options/", (route) => route.fulfill({ json: { seasons: [{ id: 1, year: 2026, name: "2026" }], disciplines: [{ id: 1, code: "algorithmic", name: "Алгоритм" }], age_groups: [{ id: 1, name: "Взрослые", min_age: 18, max_age: 35 }] } }));
  await page.route("**/api/v1/teams/?**", (route) => route.fulfill({ json: [{ id: 1, name: "Частная команда", region: "Регион", status: "draft", season: 1, season_year: 2026, discipline: 1, discipline_code: "algorithmic", discipline_name: "Алгоритм", age_group: 1, age_group_name: "Взрослые", created_by: 1, created_at: "2026-01-01", updated_at: "2026-01-01", member_count: 0, members: [] }] }));
  await page.goto("/teams");
  await expect(page.getByText("Частная команда")).toBeVisible();
  await page.getByRole("button", { name: "Спортсмен", exact: true }).click();
  await expect(page.getByText("Частная команда")).toHaveCount(0);
  releaseSwitch?.();
  await expect(page.getByText("Для просмотра команд выберите роль федерации.")).toBeVisible();
});

test("expired session hides previously loaded teams after a denied request", async ({ page }) => {
  const user = { id: 1, email: "federation@example.test", full_name: "Демо", roles: ["federation"], active_role: "federation" };
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
  await page.route("**/api/v1/teams/options/", (route) => route.fulfill({ json: { seasons: [{ id: 1, year: 2026, name: "2026" }], disciplines: [{ id: 1, code: "algorithmic", name: "Алгоритм" }], age_groups: [{ id: 1, name: "Взрослые", min_age: 18, max_age: 35 }] } }));
  await page.route("**/api/v1/teams/?**", (route) => route.fulfill({ json: [{ id: 1, name: "Частная команда", region: "Регион", status: "draft", season: 1, season_year: 2026, discipline: 1, discipline_code: "algorithmic", discipline_name: "Алгоритм", age_group: 1, age_group_name: "Взрослые", created_by: 1, created_at: "2026-01-01", updated_at: "2026-01-01", member_count: 0, members: [] }] }));
  await page.route("**/api/v1/teams/1/candidates/", (route) => route.fulfill({ status: 403, json: { detail: "Session expired" } }));
  await page.goto("/teams");
  await page.getByRole("button", { name: "Частная команда" }).click();
  await expect(page.getByText("Частная команда")).toHaveCount(0);
  await expect(page.getByRole("alert").filter({ hasText: "Войдите снова" })).toBeVisible();
});

test("late candidate response cannot reveal data after switching role", async ({ page }) => {
  let release: (() => void) | undefined;
  let started: (() => void) | undefined;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const requested = new Promise<void>((resolve) => { started = resolve; });
  const user = { id: 1, email: "demo@example.test", full_name: "Демо", roles: ["federation", "coach"], active_role: "federation" };
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
  await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "test" } }));
  await page.route("**/api/v1/auth/active-role/", (route) => route.fulfill({ json: { ...user, active_role: "coach" } }));
  await page.route("**/api/v1/teams/options/", (route) => route.fulfill({ json: { seasons: [{ id: 1, year: 2026, name: "2026" }], disciplines: [{ id: 1, code: "algorithmic", name: "Алгоритм" }], age_groups: [{ id: 1, name: "Взрослые", min_age: 18, max_age: 35 }] } }));
  await page.route("**/api/v1/teams/?**", (route) => route.fulfill({ json: [{ id: 1, name: "Частная команда", region: "Регион", status: "draft", season: 1, season_year: 2026, discipline: 1, discipline_code: "algorithmic", discipline_name: "Алгоритм", age_group: 1, age_group_name: "Взрослые", created_by: 1, created_at: "2026-01-01", updated_at: "2026-01-01", member_count: 0, members: [] }] }));
  await page.route("**/api/v1/teams/1/candidates/", async (route) => { started?.(); await gate; await route.fulfill({ json: [{ id: 2, full_name: "Частный спортсмен", email: "private@example.test", eligible: true, selected: false, eligibility: {}, rating: null }] }).catch(() => {}); });
  await page.goto("/teams");
  await page.getByRole("button", { name: "Частная команда" }).click();
  await requested;
  await page.getByRole("button", { name: "Тренер", exact: true }).click();
  await expect(page.getByText("Для просмотра команд выберите роль федерации.")).toBeVisible();
  release?.();
  await expect(page.getByText("Частный спортсмен")).toHaveCount(0);
  await expect(page.getByText("Частная команда")).toHaveCount(0);
});
