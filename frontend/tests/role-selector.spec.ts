import { expect, test } from "@playwright/test";

for (const width of [1440, 390]) {
  test(`active profile checkmark follows successful role switches at ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    const user = { id: 1, full_name: "Тестовый пользователь", email: "user@example.test", roles: ["federation", "athlete"], active_role: "federation" };
    await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
    await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "test" } }));
    await page.route("**/api/v1/auth/active-role/", async (route) => {
      user.active_role = route.request().postDataJSON().role;
      await route.fulfill({ json: user });
    });
    await page.route("**/api/v1/disciplines/", (route) => route.fulfill({ json: [] }));
    await page.route("**/api/v1/competitions/", (route) => route.fulfill({ json: [] }));
    await page.goto("/");

    if (width > 900) {
      const federation = page.getByRole("button", { name: "Федерация", exact: true });
      const athlete = page.getByRole("button", { name: "Спортсмен", exact: true });
      await expect(federation).toHaveAttribute("aria-pressed", "true");
      await expect(federation.locator("svg")).toBeVisible();
      await expect(athlete.locator("svg")).toHaveCount(0);
      await athlete.click();
      await expect(athlete).toHaveAttribute("aria-pressed", "true");
      await expect(athlete.locator("svg")).toBeVisible();
      await expect(federation.locator("svg")).toHaveCount(0);
    } else {
      const selector = page.getByRole("combobox", { name: "Активная роль" });
      await expect(selector).toHaveValue("federation");
      await expect(selector.locator('option[value="federation"]')).toHaveText("Федерация ✓");
      await selector.selectOption("athlete");
      await expect(selector.locator('option[value="athlete"]')).toHaveText("Спортсмен ✓");
      await expect(selector.locator('option[value="federation"]')).toHaveText("Федерация");
    }
    await page.screenshot({ path: testInfo.outputPath(`role-${width}.png`) });
  });
}
