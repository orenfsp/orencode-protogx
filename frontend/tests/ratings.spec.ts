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

test("ratings page expands a published-result breakdown", async ({ page }) => {
  await page.route("**/api/v1/rating-options/", (route) => route.fulfill({ json: {
    seasons: [{ id: 1, year: 2026, name: "Сезон 2026", is_active: true }],
    disciplines: [{ id: 1, code: "algorithmic", name: "Алгоритмическое программирование" }],
    age_groups: [],
  } }));
  await page.route("**/api/v1/ratings/**", (route) => route.fulfill({ json: {
    items: [{ id: 1, athlete: 7, athlete_name: "Демо Спортсмен", season: 2026, discipline: 1,
      discipline_code: "algorithmic", discipline_name: "Алгоритмическое программирование", base_score: "40.00",
      prize_count: 1, coefficient: "1.00", rating_score: "40.00", calculated_at: "2026-10-27T00:00:00Z", placement: 1,
      breakdown: [{ competition_id: 10, competition_title: "Региональный чемпионат", competition_level: "Regional", publication_id: 3,
        publication_version: 1, placement: 1, awarded_points: "40.00", age_group: "18+", source_snapshot: { place: 1 } }],
    }], page: 1, page_size: 25, total: 1, pages: 1,
  } }));
  await page.goto("/ratings");
  await expect(page.getByText("Демо Спортсмен")).toBeVisible();
  await page.getByRole("button", { name: "Демо Спортсмен" }).click();
  await expect(page.getByText("Региональный чемпионат")).toBeVisible();
  await expect(page.getByText("публикация v1")).toBeVisible();
});
