import { expect, test } from "@playwright/test";

for (const role of ["athlete", "coach", "judge"]) for (const staleStatus of [200, 500]) {
  test(`registry discards a delayed ${staleStatus} response after switching to ${role}`, async ({ page }) => {
    const user = { id: 1, full_name: "Тест", email: "fiction@example.test", roles: ["federation", "athlete", "coach", "judge"], active_role: "federation" };
    let release: () => void = () => {};
    let started: () => void = () => {};
    const wait = new Promise<void>((resolve) => { release = resolve; });
    const requestStarted = new Promise<void>((resolve) => { started = resolve; });
    await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
    await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "fixture" } }));
    await page.route("**/api/v1/auth/active-role/", (route) => { user.active_role = route.request().postDataJSON().role; return route.fulfill({ json: user }); });
    await page.route("**/api/v1/registry/options/", (route) => route.fulfill({ json: { organizations: [], disciplines: [], age_groups: [], municipalities: [] } }));
    await page.route("**/api/v1/registry/eligible-users/**", (route) => route.fulfill({ json: { results: [], next: null } }));
    await page.route("**/api/v1/athletes/**", async (route) => { started(); await wait; await route.fulfill(staleStatus === 500 ? { status: 500, json: { detail: "obsolete request failure" } } : { json: { count: 1, next: null, previous: null, results: [{ id: 4, full_name: "Приватный спортсмен", organization: null, is_active: true }] } }).catch(() => {}); });
    await page.goto("/registry");
    await requestStarted;
    const labels: Record<string, string> = { athlete: "Спортсмен", coach: "Тренер", judge: "Судья" };
    await page.getByRole("button", { name: labels[role], exact: true }).click();
    release();
    await expect(page.getByText("Приватный спортсмен")).toHaveCount(0);
    await expect(page.getByText("obsolete request failure")).toHaveCount(0);
    await expect(page.getByText("Для просмотра реестров выберите роль федерации.")).toBeVisible();
  });
}

test("logout clears a registry with a pending read", async ({ page }) => {
  const user = { id: 1, full_name: "Тест", email: "fiction@example.test", roles: ["federation"], active_role: "federation" };
  let release: () => void = () => {};
  let started: () => void = () => {};
  const wait = new Promise<void>((resolve) => { release = resolve; });
  const requestStarted = new Promise<void>((resolve) => { started = resolve; });
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
  await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "fixture" } }));
  await page.route("**/api/v1/auth/logout/", (route) => route.fulfill({ status: 204 }));
  await page.route("**/api/v1/registry/options/", (route) => route.fulfill({ json: { organizations: [], disciplines: [], age_groups: [], municipalities: [] } }));
  await page.route("**/api/v1/registry/eligible-users/**", (route) => route.fulfill({ json: { results: [], next: null } }));
  await page.route("**/api/v1/athletes/**", async (route) => { started(); await wait; await route.fulfill({ json: { count: 1, next: null, results: [{ id: 4, full_name: "Приватный спортсмен", is_active: true }] } }).catch(() => {}); });
  await page.goto("/registry");
  await requestStarted;
  await page.getByRole("button", { name: "Выйти", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  release();
  await expect(page.getByText("Приватный спортсмен")).toHaveCount(0);
});

test("old analytics response cannot overwrite newer filters", async ({ page }) => {
  const user = { id: 1, full_name: "Тест", email: "fiction@example.test", roles: ["federation"], active_role: "federation" };
  let release: () => void = () => {};
  let started: () => void = () => {};
  const wait = new Promise<void>((resolve) => { release = resolve; });
  const requestStarted = new Promise<void>((resolve) => { started = resolve; });
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
  await page.route("**/api/v1/registry/options/", (route) => route.fulfill({ json: { organizations: [], disciplines: [], age_groups: [], municipalities: [] } }));
  await page.route("**/api/v1/registry/eligible-users/**", (route) => route.fulfill({ json: { results: [], next: null } }));
  await page.route("**/api/v1/analytics/participation/?**", async (route) => {
    const old = route.request().url().includes("start_year=2024");
    if (old) { started(); await wait; }
    const year = old ? 2024 : 2025;
    await route.fulfill({ json: [{ year, unique_athletes: old ? 99 : 1, started: 0, ceased: 0, change: null, growth_percent: null, breakdowns: { organizations: [], disciplines: [], municipalities: [], age_groups: [] } }] }).catch(() => {});
  });
  await page.goto("/analytics/participation");
  await requestStarted;
  await page.getByLabel("С года").fill("2025");
  await page.getByLabel("По год").fill("2026");
  await page.getByRole("button", { name: "Построить отчёт" }).click();
  await expect(page.getByRole("row").filter({ hasText: "2025" }).getByText("1", { exact: true }).first()).toBeVisible();
  release();
  await expect(page.getByText("99", { exact: true })).toHaveCount(0);
});

test("logout clears the workspace while a registry write is pending", async ({ page }) => {
  const user = { id: 1, full_name: "Тест", email: "fiction@example.test", roles: ["federation"], active_role: "federation" };
  let release: () => void = () => {};
  let started: () => void = () => {};
  const wait = new Promise<void>((resolve) => { release = resolve; });
  const requestStarted = new Promise<void>((resolve) => { started = resolve; });
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
  await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "fixture" } }));
  await page.route("**/api/v1/auth/logout/", (route) => route.fulfill({ status: 204 }));
  await page.route("**/api/v1/registry/options/", (route) => route.fulfill({ json: { organizations: [], disciplines: [], age_groups: [], municipalities: [] } }));
  await page.route("**/api/v1/registry/eligible-users/**", (route) => route.fulfill({ json: { results: [], next: null } }));
  await page.route("**/api/v1/athletes/**", (route) => route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } }));
  await page.route("**/api/v1/organizations/**", async (route) => {
    if (route.request().method() === "POST") { started(); await wait; await route.fulfill({ status: 201, json: { id: 1 } }).catch(() => {}); }
    else await route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } });
  });
  await page.goto("/registry");
  await page.getByRole("button", { name: "Организации", exact: true }).click();
  await page.getByLabel("Код", { exact: true }).fill("fixture");
  await page.getByLabel("Название", { exact: true }).fill("Тестовая организация");
  await page.getByRole("button", { name: "Создать", exact: true }).click();
  await requestStarted;
  await page.getByRole("button", { name: "Выйти", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  release();
  await expect(page.getByText("Тестовая организация")).toHaveCount(0);
});

test("late correction cannot close the next athlete's correction form", async ({ page }) => {
  const user = { id: 1, full_name: "Федерация", email: "fiction@example.test", roles: ["federation"], active_role: "federation" };
  let release: () => void = () => {};
  let started: () => void = () => {};
  const wait = new Promise<void>((resolve) => { release = resolve; });
  const requestStarted = new Promise<void>((resolve) => { started = resolve; });
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
  await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "fixture" } }));
  await page.route("**/api/v1/registry/options/", (route) => route.fulfill({ json: { organizations: [], disciplines: [], age_groups: [], municipalities: [] } }));
  await page.route("**/api/v1/registry/eligible-users/**", (route) => route.fulfill({ json: { results: [], next: null } }));
  await page.route("**/api/v1/registry/profiles/**", (route) => route.fulfill({ json: { ranks: [], categories: [], coach_links: [], assignments: [] } }));
  await page.route("**/api/v1/athletes/**", async (route) => {
    const url = route.request().url();
    if (url.includes("/correct/")) { started(); await wait; await route.fulfill({ json: {} }).catch(() => {}); }
    else if (url.includes("/audit/")) await route.fulfill({ json: [] });
    else if (url.includes("/history/")) await route.fulfill({ json: [{ id: 1, starts_on: "2024-01-01", ends_on: null }] });
    else await route.fulfill({ json: { count: 2, next: null, previous: null, results: [{ id: 2, full_name: "Первый", date_of_birth: "2000-01-01", is_active: true }, { id: 3, full_name: "Второй", date_of_birth: "2000-01-01", is_active: true }] } });
  });
  await page.goto("/registry");
  await page.getByRole("button", { name: "Первый", exact: true }).click();
  await page.getByRole("button", { name: "Исправить", exact: true }).first().click();
  await page.getByLabel("Причина исправления").fill("Уточнение даты");
  await page.getByRole("button", { name: "Сохранить исправление" }).click();
  await requestStarted;
  await page.getByRole("button", { name: "Второй", exact: true }).click();
  await page.getByRole("button", { name: "Исправить", exact: true }).first().click();
  release();
  await expect(page.getByLabel("Причина исправления")).toBeVisible();
});

for (const screen of ["registry", "analytics"]) for (const denial of [401, 403]) {
  test(`${screen} clears privileged data after a ${denial} server denial`, async ({ page }) => {
    const user = { id: 1, full_name: "Тест", email: "fiction@example.test", roles: ["federation"], active_role: "federation" };
    await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
    await page.route("**/api/v1/registry/options/", (route) => route.fulfill({ json: { organizations: [], disciplines: [], age_groups: [], municipalities: [] } }));
    await page.route("**/api/v1/registry/eligible-users/**", (route) => route.fulfill({ json: { results: [], next: null } }));
    if (screen === "registry") {
      await page.route("**/api/v1/athletes/**", (route) => route.request().url().includes("search=deny") ? route.fulfill({ status: denial, json: { detail: "denied" } }) : route.fulfill({ json: { count: 1, next: null, previous: null, results: [{ id: 4, full_name: "Закрытые данные", organization: null, is_active: true }] } }));
      await page.goto("/registry");
      await expect(page.getByText("Закрытые данные")).toBeVisible();
      await page.getByLabel("Поиск", { exact: true }).fill("deny");
    } else {
      await page.route("**/api/v1/analytics/participation/?**", (route) => route.request().url().includes("start_year=2025") ? route.fulfill({ status: denial, json: { detail: "denied" } }) : route.fulfill({ json: [{ year: 2024, unique_athletes: 987, started: 0, ceased: 0, change: null, growth_percent: null, breakdowns: { organizations: [], disciplines: [], municipalities: [], age_groups: [] } }] }));
      await page.goto("/analytics/participation");
      await expect(page.getByText("987", { exact: true }).first()).toBeVisible();
      await page.getByLabel("С года").fill("2025");
      await page.getByLabel("По год").fill("2026");
      await page.getByRole("button", { name: "Построить отчёт" }).click();
    }
    await expect(page.locator(".toast-viewport").getByRole("alert")).toContainText("Доступ");
    await expect(page.getByText(screen === "registry" ? "Закрытые данные" : "987", { exact: true })).toHaveCount(0);
  });
}
