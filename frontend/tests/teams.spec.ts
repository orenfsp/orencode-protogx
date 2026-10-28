import { expect, test } from "@playwright/test";

test("regional teams page supports manual selection and document actions", async ({ page }) => {
  let release: (() => void) | undefined;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: { id: 1, email: "demo.federation@example.test", full_name: "Демо Федерация", roles: ["federation"], active_role: "federation" } }));
  await page.route("**/api/v1/teams/options/", (route) => route.fulfill({ json: {
    seasons: [{ id: 1, year: 2026, name: "Сезон 2026" }],
    disciplines: [{ id: 1, code: "algorithmic", name: "Алгоритмическое программирование" }],
    age_groups: [{ id: 1, name: "Взрослые", min_age: 18, max_age: 35 }],
  } }));
  const team = { id: 1, name: "Демо-команда", region: "Оренбургская область", status: "draft", season: 1, season_year: 2026, discipline: 1, discipline_code: "algorithmic", discipline_name: "Алгоритмическое программирование", age_group: 1, age_group_name: "Взрослые", created_by: 1, created_at: "2026-01-01", updated_at: "2026-01-01", member_count: 1, members: [{ id: 7, athlete: 3, athlete_name: "Участник состава", eligibility_snapshot: { eligible: true, rating_score: "80.00" }, current_eligibility: { eligible: false, restriction: "suspension" } }] };
  await page.route("**/api/v1/teams/?**", (route) => route.fulfill({ json: [team] }));
  await page.route("**/api/v1/teams/1/candidates/", (route) => route.fulfill({ json: [{ id: 2, full_name: "Демо Спортсмен", email: "demo.athlete@example.test", sport_rank: "III спортивный разряд", eligible: true, selected: false, eligibility: { age: 26, consent: true, guardian_verified: true, restriction: null, rating_score: "100.00" }, rating: { score: "100.00", base_score: "100.00", prize_count: 1, position: 1 } }] }));
  await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "test" } }));
  await page.route("**/api/v1/teams/1/members/", async (route) => { await gate; await route.fulfill({ json: team, status: 201 }); });
  await page.goto("/teams");
  await expect(page.getByRole("heading", { name: "Региональные команды" })).toBeVisible();
  await page.getByRole("button", { name: "Демо-команда" }).click();
  await expect(page.getByText("Текущий допуск требует проверки")).toBeVisible();
  await expect(page.getByText("Демо Спортсмен")).toBeVisible();
  await expect(page.getByText("III спортивный разряд")).toBeVisible();
  await expect(page.getByText("Место 1")).toBeVisible();
  await expect(page.getByRole("link", { name: "Расшифровка рейтинга и результаты" })).toHaveAttribute("href", "/ratings");
  await page.getByLabel("Поиск спортсмена").fill("нет такого");
  await expect(page.getByText("Демо Спортсмен")).toHaveCount(0);
  await expect(page.getByText("Кандидатов по вашему запросу нет.")).toBeVisible();
  await page.getByLabel("Поиск спортсмена").fill("спортсмен");
  await expect(page.getByText("Демо Спортсмен")).toBeVisible();
  await page.getByRole("button", { name: "Добавить" }).click();
  await expect(page.getByLabel("Сезон")).toBeDisabled();
  await expect(page.getByLabel("Дисциплина")).toBeDisabled();
  await expect(page.getByLabel("Возрастная группа")).toBeDisabled();
  release?.();
  await expect(page.getByLabel("Сезон")).toBeEnabled();
  await expect(page.getByRole("button", { name: "Скачать состав PDF" })).toBeVisible();
});

test("late candidate response from another team is discarded", async ({ page }) => {
  let release: (() => void) | undefined;
  let started: (() => void) | undefined;
  let finished: (() => void) | undefined;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const requested = new Promise<void>((resolve) => { started = resolve; });
  const completed = new Promise<void>((resolve) => { finished = resolve; });
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: { id: 1, email: "demo@example.test", full_name: "Демо", roles: ["federation"], active_role: "federation" } }));
  await page.route("**/api/v1/teams/options/", (route) => route.fulfill({ json: { seasons: [{ id: 1, year: 2026, name: "2026" }], disciplines: [{ id: 1, code: "algorithmic", name: "Алгоритм" }], age_groups: [{ id: 1, name: "Взрослые", min_age: 18, max_age: 35 }] } }));
  const team = { region: "Регион", status: "draft", season: 1, season_year: 2026, discipline: 1, discipline_code: "algorithmic", discipline_name: "Алгоритм", age_group: 1, age_group_name: "Взрослые", created_by: 1, created_at: "2026-01-01", updated_at: "2026-01-01", member_count: 0, members: [] };
  await page.route("**/api/v1/teams/?**", (route) => route.fulfill({ json: [{ ...team, id: 1, name: "Первая команда" }, { ...team, id: 2, name: "Вторая команда" }] }));
  await page.route("**/api/v1/teams/1/candidates/", async (route) => { started?.(); await gate; await route.fulfill({ json: [{ id: 3, full_name: "Первый кандидат", email: "first@example.test", eligible: true, selected: false, eligibility: {}, rating: null }] }); finished?.(); });
  await page.route("**/api/v1/teams/2/candidates/", (route) => route.fulfill({ json: [{ id: 4, full_name: "Второй кандидат", email: "second@example.test", eligible: true, selected: false, eligibility: {}, rating: null }] }));
  await page.goto("/teams");
  await page.getByRole("button", { name: "Первая команда" }).click();
  await requested;
  await expect(page.getByText("Загрузка кандидатов…")).toBeVisible();
  await page.getByRole("button", { name: "Вторая команда" }).click();
  await expect(page.getByText("Второй кандидат")).toBeVisible();
  release?.();
  await completed;
  await expect(page.getByText("Первый кандидат")).toHaveCount(0);
  await expect(page.getByText("Второй кандидат")).toBeVisible();
});

test("team workspace loads subsequent API pages", async ({ page }) => {
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: { id: 1, email: "demo@example.test", full_name: "Демо", roles: ["federation"], active_role: "federation" } }));
  await page.route("**/api/v1/teams/options/", (route) => route.fulfill({ json: { seasons: [{ id: 1, year: 2026, name: "2026" }], disciplines: [{ id: 1, code: "algorithmic", name: "Алгоритм" }], age_groups: [{ id: 1, name: "Взрослые", min_age: 18, max_age: 35 }] } }));
  const team = { region: "Регион", status: "draft", season: 1, season_year: 2026, discipline: 1, discipline_code: "algorithmic", discipline_name: "Алгоритм", age_group: 1, age_group_name: "Взрослые", created_by: 1, created_at: "2026-01-01", updated_at: "2026-01-01", member_count: 0, members: [] };
  await page.route("**/api/v1/teams/?**", (route) => {
    const second = new URL(route.request().url()).searchParams.get("page") === "2";
    return route.fulfill({ json: { count: 2, next: second ? null : "http://example.test/?page=2", previous: null, results: [{ ...team, id: second ? 2 : 1, name: second ? "Вторая страница" : "Первая страница" }] } });
  });
  await page.goto("/teams");
  await expect(page.getByRole("button", { name: "Первая страница" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Вторая страница" })).toBeVisible();
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
  await expect(page).toHaveURL(/\/dashboard$/);
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
  await expect(page).toHaveURL(/\/dashboard$/);
  release?.();
  await expect(page.getByText("Частный спортсмен")).toHaveCount(0);
  await expect(page.getByText("Частная команда")).toHaveCount(0);
});

test("logout hides a pending team response", async ({ page }) => {
  let release: (() => void) | undefined;
  let started: (() => void) | undefined;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const requested = new Promise<void>((resolve) => { started = resolve; });
  let signedOut = false;
  const user = { id: 1, email: "demo@example.test", full_name: "Демо", roles: ["federation"], active_role: "federation" };
  await page.route("**/api/v1/auth/me/", (route) => signedOut ? route.fulfill({ status: 403 }) : route.fulfill({ json: user }));
  await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "test" } }));
  await page.route("**/api/v1/auth/logout/", (route) => { signedOut = true; return route.fulfill({ status: 204 }); });
  await page.route("**/api/v1/teams/options/", (route) => route.fulfill({ json: { seasons: [{ id: 1, year: 2026, name: "2026" }], disciplines: [{ id: 1, code: "algorithmic", name: "Алгоритм" }], age_groups: [{ id: 1, name: "Взрослые", min_age: 18, max_age: 35 }] } }));
  await page.route("**/api/v1/teams/?**", (route) => route.fulfill({ json: [{ id: 1, name: "Частная команда", region: "Регион", status: "draft", season: 1, season_year: 2026, discipline: 1, discipline_code: "algorithmic", discipline_name: "Алгоритм", age_group: 1, age_group_name: "Взрослые", created_by: 1, created_at: "2026-01-01", updated_at: "2026-01-01", member_count: 0, members: [] }] }));
  await page.route("**/api/v1/teams/1/candidates/", async (route) => { started?.(); await gate; await route.fulfill({ json: [{ id: 2, full_name: "Частный спортсмен", email: "private@example.test", eligible: true, selected: false, eligibility: {}, rating: null }] }).catch(() => {}); });
  await page.goto("/teams");
  await page.getByRole("button", { name: "Частная команда" }).click();
  await requested;
  await page.getByRole("button", { name: "Выйти", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  release?.();
  await expect(page.getByText("Частный спортсмен")).toHaveCount(0);
  await expect(page.getByText("Частная команда")).toHaveCount(0);
});
