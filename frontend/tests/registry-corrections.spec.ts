import { expect, test } from "@playwright/test";

const cases = [
  ["participation", "Участие", {}],
  ["disciplines", "Дисциплины", { discipline: 1, discipline_name: "Программирование" }],
  ["organizations", "Организации", { organization: 1, organization_name: "Демо организация" }],
  ["municipalities", "Муниципалитеты", { municipality: "Оренбург" }],
  ["training-stages", "Этапы подготовки", { stage: "Начальный" }],
] as const;

for (const [kind, heading, fields] of cases) {
  test(`${kind} correction reports conflicts and retains the form`, async ({ page }) => {
    const user = { id: 1, full_name: "Федерация", email: "fiction@example.test", roles: ["federation"], active_role: "federation" };
    let attempts = 0;
    await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
    await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "fixture" } }));
    await page.route("**/api/v1/registry/options/", (route) => route.fulfill({ json: { organizations: [{ id: 1, name: "Демо организация" }], disciplines: [{ id: 1, name: "Программирование" }], age_groups: [], municipalities: ["Оренбург"] } }));
    await page.route("**/api/v1/registry/eligible-users/**", (route) => route.fulfill({ json: { results: [], next: null } }));
    await page.route("**/api/v1/registry/profiles/**/context/", (route) => route.fulfill({ json: { ranks: [], categories: [], coach_links: [], assignments: [] } }));
    await page.route("**/api/v1/athletes/?**", (route) => route.fulfill({ json: { count: 1, next: null, previous: null, results: [{ id: 8, full_name: "Демо спортсмен", date_of_birth: "2000-01-01", organization: null, is_active: true }] } }));
    await page.route("**/api/v1/athletes/**/history/**", (route) => {
      if (route.request().url().includes("/audit/")) return route.fulfill({ json: [] });
      const selected = route.request().url().includes(`/history/${kind}/`);
      return route.fulfill({ json: selected ? [{ id: 1, starts_on: "2024-01-01", ends_on: null, ...fields }] : [] });
    });
    await page.route("**/api/v1/athletes/**/correct/", (route) => {
      attempts += 1;
      return attempts === 1 ? route.fulfill({ status: 409, json: { detail: "conflict" } }) : route.fulfill({ json: { id: 1 } });
    });
    await page.goto("/registry");
    await page.getByRole("button", { name: "Демо спортсмен", exact: true }).click();
    await page.getByRole("heading", { name: heading, exact: true }).locator("..").getByRole("button", { name: "Исправить", exact: true }).click();
    await page.getByLabel("Причина исправления").fill("Уточнение");
    await page.getByRole("button", { name: "Сохранить исправление" }).click();
    await expect(page.locator(".toast-viewport").getByRole("alert")).toContainText("Период изменён");
    await expect(page.getByLabel("Причина исправления")).toHaveValue("Уточнение");
    await page.getByRole("heading", { name: heading, exact: true }).locator("..").getByRole("button", { name: "Исправить", exact: true }).click();
    await expect(page.locator(".toast-viewport").getByRole("alert")).toHaveCount(0);
    await page.getByLabel("Причина исправления").fill("Уточнение");
    await page.getByRole("button", { name: "Сохранить исправление" }).click();
    await expect(page.getByLabel("Причина исправления")).toHaveCount(0);
    expect(attempts).toBe(2);
  });
}
