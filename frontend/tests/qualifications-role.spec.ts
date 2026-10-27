import { expect, test } from "@playwright/test";

for (const initialRole of ["federation", "coach"]) {
  test(`${initialRole} data and delayed responses do not leak after switching to athlete`, async ({ page }) => {
    const user = { id: 1, full_name: "Тест", email: "fiction@example.test", roles: ["federation", "coach", "athlete"], active_role: initialRole };
    let release: (() => void) | undefined;
    let markStarted: (() => void) | undefined;
    const started = new Promise<void>((resolve) => { markStarted = resolve; });
    const pending = new Promise<void>((resolve) => { release = resolve; });
    await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
    await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "test" } }));
    await page.route("**/api/v1/auth/active-role/", async (route) => {
      user.active_role = route.request().postDataJSON().role;
      await route.fulfill({ json: user });
    });
    await page.route("**/api/v1/qualification-options/", (route) => route.fulfill({ json: { ranks: [], categories: [], request_types: [], hint_disclaimer: "" } }));
    await page.route("**/api/v1/qualification-deadlines/**", (route) => route.fulfill({ json: { items: [] } }));
    await page.route("**/api/v1/rank-results/**", (route) => route.fulfill({ json: { items: [], pages: 1 } }));
    await page.route("**/api/v1/rank-history/", (route) => route.fulfill({ json: [] }));
    await page.route("**/api/v1/judge-category-*/", (route) => route.fulfill({ json: [] }));
    await page.route("**/api/v1/rank-applications/", async (route) => {
      const role = user.active_role;
      if (role === initialRole) { markStarted?.(); await pending; }
      const rows = role === initialRole ? [{ id: 1, athlete_name: "Секретный спортсмен", status: "pending", request_type: "assign", requested_rank_label: "III", discipline_name: "Тест", competition: 1, competition_title: "Тест" }] : [];
      await route.fulfill({ json: rows }).catch(() => {});
    });
    await page.goto("/qualifications");
    await expect(page.getByRole("button", { name: "Спортсмен", exact: true })).toBeVisible();
    await started;
    await page.getByRole("button", { name: "Спортсмен", exact: true }).click();
    release?.();
    await expect(page.getByText("Секретный спортсмен")).toHaveCount(0);
    await page.getByRole("button", { name: "Тренер", exact: true }).click();
    await page.getByRole("button", { name: "Спортсмен", exact: true }).click();
    await expect(page.getByText("Секретный спортсмен")).toHaveCount(0);
  });
}

for (const width of [1440, 390]) {
  test(`dashboard links to qualifications at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    const user = { id: 1, full_name: "Тест", email: "fiction@example.test", roles: ["athlete"], active_role: "athlete" };
    await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
    await page.route("**/api/v1/auth/dashboard/", (route) => route.fulfill({ json: { role: "athlete", metrics: [], guardian_status: null } }));
    await page.goto("/dashboard");
    await expect(page.getByRole("link", { name: "Разряды и категории" })).toHaveAttribute("href", "/qualifications");
    await expect(page.getByRole("link", { name: "Разряды и категории" })).toBeVisible();
  });
}
