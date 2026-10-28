import { expect, test, type Page } from "@playwright/test";
import type { Role } from "../src/lib/api";

async function mockRole(page: Page, initial: Role | null) {
  let role = initial;
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let data: unknown = [];
    if (path.endsWith("registry/options/")) data = { organizations: [], disciplines: [], age_groups: [], municipalities: [] };
    if (path.endsWith("athletes/") || path.endsWith("registry/eligible-users/")) data = { results: [], next: null };
    if (path.endsWith("auth/active-role/")) role = route.request().postDataJSON().role;
    if (path.endsWith("auth/me/") || path.endsWith("auth/active-role/")) data = { id: 1, full_name: "Демо пользователь", roles: ["federation", "athlete", "coach", "judge"], active_role: role };
    if (path.endsWith("auth/csrf/")) data = { csrfToken: "test" };
    if (path.endsWith("auth/dashboard/")) data = { role, metrics: [], guardian_status: null };
    await route.fulfill({ status: !initial && path.endsWith("auth/me/") ? 401 : 200, json: data });
  });
}

for (const width of [1440, 390]) for (const role of ["federation", "athlete", "coach", "judge", null] as const) {
  test(`${role ?? "guest"} sees only available navigation at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await mockRole(page, role);
    await page.goto("/");
    if (role) await expect(page.locator(".rbtn")).toContainText("Демо пользователь");
    const nav = page.getByRole("navigation", { name: width === 1440 ? "Разделы" : "Основная навигация" });
    await expect(nav.locator('a[href="/competitions"]')).toBeVisible();
    await expect(nav.locator('a[href="/teams"]')).toHaveCount(role === "federation" ? 1 : 0);
    await expect(nav.locator('a[href="/dashboard"]')).toHaveCount(role ? 1 : 0);
    if (width === 1440) for (const href of ["/registry", "/analytics/participation"]) await expect(nav.locator(`a[href="${href}"]`)).toHaveCount(role === "federation" ? 1 : 0);
    if (role) await expect(page.locator('main a[href="/register"]')).toHaveCount(0);
  });
}

test("switching active role removes federation navigation and moves off a restricted page", async ({ page }) => {
  await mockRole(page, "federation");
  await page.goto("/registry");
  await expect(page.locator('.idx nav a[href="/registry"]')).toBeVisible();
  await page.getByRole("button", { name: "Спортсмен", exact: true }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
  for (const href of ["/teams", "/registry", "/analytics/participation"]) await expect(page.locator(`nav a[href="${href}"]`)).toHaveCount(0);
  await expect(page.locator('main a[href="/history"]')).toBeVisible();
  await expect(page.locator('main a[href="/coach-links"]')).toBeVisible();
});

test("a direct URL does not render another role's controls or fetch its data", async ({ page }) => {
  const protectedRequests: string[] = [];
  page.on("request", (request) => { if (request.url().includes("/api/v1/registry/") || request.url().includes("/api/v1/athletes/")) protectedRequests.push(request.url()); });
  await mockRole(page, "judge");
  await page.goto("/registry");
  await expect(page.locator(".rbtn")).toContainText("Демо пользователь");
  await expect(page.locator('main a[href="/dashboard"]')).toBeVisible();
  await expect(page.getByRole("heading", { name: "Реестры", exact: true })).toHaveCount(0);
  expect(protectedRequests).toEqual([]);
});
