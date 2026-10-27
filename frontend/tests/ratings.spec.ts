import { expect, test } from "@playwright/test";

test("ratings page loads API options and shows empty state for an uncalculated season", async ({ page }) => {
  const options = page.waitForResponse((response) => response.url().includes("/api/v1/rating-options/") && response.request().method() === "GET");
  await page.goto("/ratings");
  expect((await options).ok()).toBeTruthy();
  await expect(page.getByRole("heading", { name: "Рейтинг спортсменов" })).toBeVisible();
  await expect(page.getByLabel("Сезон")).toHaveValue("2026");
  await expect(page.getByLabel("Дисциплина")).toHaveValue("algorithmic");
  await expect(page.getByText("Для выбранных фильтров опубликованных результатов нет.")).toBeVisible();
  await page.getByLabel("Возрастная группа").selectOption({ label: "Демо: 18+" });
  await expect(page.getByLabel("Возрастная группа")).toHaveValue("2");
});
