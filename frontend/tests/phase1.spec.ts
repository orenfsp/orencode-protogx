import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test("multi-role account loads role-specific data after switching", async ({ page }) => {
  await signIn(page, "demo.federation@example.test");
  await expect(page.getByRole("heading", { name: "Федерация" })).toBeVisible();
  await expect(page.locator(".dashboard-metrics").getByText("Спортсменов", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Спортсмен", exact: true }).click();
  await expect(page.getByRole("button", { name: "Спортсмен", exact: true })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("heading", { name: "Спортсмен" })).toBeVisible();
  await expect(page.getByText("Согласие", { exact: true })).toBeVisible();
  await expect(page.locator(".dashboard-metrics").getByText("Спортсменов", { exact: true })).toHaveCount(0);
  const dashboard = await page.evaluate(async () => (await fetch("/api/v1/auth/dashboard/")).json());
  expect(dashboard.role).toBe("athlete");
});

for (const [email, heading] of [
  ["demo.athlete@example.test", "Спортсмен"],
  ["demo.coach@example.test", "Тренер"],
  ["demo.judge@example.test", "Судья"],
] as const) {
  test(`${heading} dashboard loads for its assigned account`, async ({ page }) => {
    await signIn(page, email);
    await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    await expect(page.getByText("Дисциплин в каталоге")).toBeVisible();
  });
}

test("mobile theme control persists and bottom navigation works", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByRole("navigation", { name: "Основная навигация" })).toBeVisible();
  const theme = page.getByRole("button", { name: "Тёмная тема: включить" });
  await theme.click();
  await expect(page.locator("#th")).toBeChecked();
  await expect.poll(() => page.locator("body").evaluate((body) => getComputedStyle(body).backgroundColor)).toBe("rgb(28, 27, 69)");
  await page.reload();
  await expect(page.locator("#th")).toBeChecked();
  await page.getByRole("navigation", { name: "Основная навигация" }).getByRole("link", { name: "Календарь" }).click();
  await expect(page).toHaveURL(/\/competitions$/);
  await page.getByRole("button", { name: "Светлая тема: включить" }).click();
  await expect.poll(() => page.locator("body").evaluate((body) => getComputedStyle(body).backgroundColor)).toBe("rgb(255, 255, 255)");
});

test("mobile multi-role account switches dashboard", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await signIn(page, "demo.federation@example.test");
  await expect(page.getByRole("heading", { name: "Федерация" })).toBeVisible();
  await page.getByRole("combobox", { name: "Активная роль" }).selectOption("athlete");
  await expect(page.getByRole("heading", { name: "Спортсмен" })).toBeVisible();
  await expect(page.getByText("Согласие", { exact: true })).toBeVisible();
  const dashboard = await page.evaluate(async () => (await fetch("/api/v1/auth/dashboard/")).json());
  expect(dashboard.role).toBe("athlete");
});
