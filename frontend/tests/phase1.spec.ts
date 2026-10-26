import { expect, test } from "@playwright/test";

test("fictional multi-role account can switch assigned dashboards", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Электронная почта").fill("demo.federation@example.test");
  await page.getByLabel("Пароль").fill("DemoOnly2026!");
  await page.getByRole("button", { name: "Войти", exact: true }).click();

  await expect(page).toHaveURL(/\/dashboard$/);
  await expect(page.getByText("Активная роль: federation")).toBeVisible();
  await page.getByRole("button", { name: "Спортсмен" }).click();
  await expect(page.getByRole("button", { name: "Спортсмен" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByText("Активная роль: athlete")).toBeVisible();
});
