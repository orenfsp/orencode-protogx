import { expect, test } from "@playwright/test";

for (const width of [1440, 768, 390]) for (const theme of ["light", "dark"]) {
  test(`registry editing and focus at ${width}px in ${theme} theme`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript((value) => localStorage.setItem("fsp-theme", value), theme);
    const user = { id: 1, full_name: "Демо Федерация", email: "fiction@example.test", roles: ["federation"], active_role: "federation" };
    await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
    await page.route("**/api/v1/registry/options/", (route) => route.fulfill({ json: { organizations: [{ id: 1, name: "Демо организация" }], disciplines: [{ id: 1, name: "Алгоритмическое программирование" }], age_groups: [], municipalities: ["Оренбург"] } }));
    await page.route("**/api/v1/registry/eligible-users/**", (route) => route.fulfill({ json: { results: [{ id: 8, full_name: "Демо кандидат" }], next: null } }));
    await page.route("**/api/v1/registry/profiles/**", (route) => route.fulfill({ json: { ranks: [], categories: [], coach_links: [], assignments: [] } }));
    await page.route("**/api/v1/athletes/**/audit/", (route) => route.fulfill({ json: [] }));
    await page.route("**/api/v1/athletes/**/history/**", (route) => route.fulfill({ json: [{ id: 1, starts_on: "2024-01-01", ends_on: null }] }));
    await page.route("**/api/v1/athletes/?**", (route) => route.fulfill({ json: { count: 1, next: null, previous: null, results: [{ id: 8, full_name: "Демо спортсмен", date_of_birth: "2000-01-01", organization: null, is_active: true }] } }));
    await page.goto("/registry");
    await page.getByRole("button", { name: "Демо спортсмен", exact: true }).click();
    await page.getByRole("button", { name: "Исправить", exact: true }).first().click();
    await expect(page.getByLabel("Причина исправления")).toBeVisible();
    await page.getByLabel("Причина исправления").focus();
    await expect(page.getByLabel("Причина исправления")).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy();
    if (width <= 900) await expect(page.getByRole("navigation", { name: "Основная навигация" })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath(`registry-form-${width}-${theme}.png`), fullPage: true });
  });
}
