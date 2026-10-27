import { expect, test } from "@playwright/test";

const athlete = { id: 1, email: "athlete@example.test", full_name: "Тестовый спортсмен", roles: ["athlete", "coach"], active_role: "athlete" };
const competition = (id: number, title: string, state: string, startsAt: string) => ({ id, title, state, starts_at: startsAt, discipline_name: "Алгоритмы" });

test("homepage shows the nearest future published competition", async ({ page }) => {
  const future = (days: number) => new Date(Date.now() + days * 86400000).toISOString();
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ status: 403, json: {} }));
  await page.route("**/api/v1/disciplines/", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/v1/competitions/", (route) => route.fulfill({ json: [
    competition(1, "Черновик", "draft", future(1)), competition(2, "Завершено", "closed", future(1)),
    competition(3, "Прошедшее", "published", future(-1)), competition(4, "Позже", "published", future(5)),
    competition(5, "Ближайшее", "published", future(2)),
  ] }));
  await page.goto("/");
  const card = page.getByRole("complementary", { name: "Ближайшее соревнование" });
  await expect(card.getByRole("link", { name: "Ближайшее" })).toHaveAttribute("href", "/competitions/5");
  await expect(card).not.toContainText("Черновик");
  await expect(page.getByText("Дисциплин пока нет.")).toBeVisible();
});

test("homepage distinguishes an empty calendar from an unavailable one", async ({ page }) => {
  let fail = false;
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ status: 403, json: {} }));
  await page.route("**/api/v1/disciplines/", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/v1/competitions/", (route) => route.fulfill(fail ? { status: 503, json: {} } : { json: [] }));
  await page.goto("/");
  await expect(page.getByText("Предстоящих соревнований пока нет")).toBeVisible();
  fail = true;
  await page.reload();
  await expect(page.getByRole("alert").filter({ hasText: "Календарь временно недоступен." })).toBeVisible();
  await expect(page.getByText("Предстоящих соревнований пока нет")).toHaveCount(0);
});

test("upcoming competition card remains usable at desktop, tablet and mobile widths in both themes", async ({ page }, testInfo) => {
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ status: 403, json: {} }));
  await page.route("**/api/v1/disciplines/", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/v1/competitions/", (route) => route.fulfill({ json: [competition(5, "Региональное соревнование по алгоритмическому программированию", "published", new Date(Date.now() + 86400000).toISOString())] }));
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/");
    const card = page.getByRole("complementary", { name: "Ближайшее соревнование" });
    const link = card.getByRole("link");
    await expect(link).toBeVisible();
    for (const dark of [false, true]) {
      if (await page.locator("#th").isChecked() !== dark) {
        if (width <= 900) await page.locator(".mobile-theme").click();
        else await page.locator("label[for=th].tgl").click();
      }
      await expect(page.locator("#th")).toHaveJSProperty("checked", dark);
      await expect.poll(() => card.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true);
      await page.screenshot({ path: testInfo.outputPath(`home-${width}-${dark ? "dark" : "light"}.png`) });
    }
  }
});

test("calendar distinguishes loading, failure, empty search and closed events", async ({ page }) => {
  let release: () => void = () => {};
  const gate = new Promise<void>((resolve) => { release = resolve; });
  let fail = false;
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ status: 403, json: {} }));
  await page.route("**/api/v1/competitions/", async (route) => {
    await gate;
    await route.fulfill(fail ? { status: 503, json: { detail: "Календарь недоступен" } } : { json: [competition(1, "Турнир", "closed", "2030-01-01T12:00:00Z")] });
  });
  for (const path of ["disciplines", "age-groups", "templates", "calendar-entries"]) {
    await page.route(`**/api/v1/${path}/`, (route) => route.fulfill({ json: [] }));
  }
  await page.goto("/competitions");
  await expect(page.getByText("Загрузка календаря…")).toBeVisible();
  await expect(page.getByText("Соревнований пока нет.")).toHaveCount(0);
  release();
  await expect(page.getByRole("row", { name: /Турнир/ })).toContainText("Завершено");
  await page.getByLabel("Поиск по названию и дисциплине").fill("нет совпадений");
  await expect(page.getByText("По вашему запросу соревнования не найдены.")).toBeVisible();
  fail = true;
  await page.reload();
  await expect(page.getByRole("alert").filter({ hasText: "Календарь недоступен" })).toBeVisible();
  await expect(page.getByText("Соревнований пока нет.")).toHaveCount(0);
});

test("history hides stale results after a role change and reports request failures", async ({ page }) => {
  let release: () => void = () => {};
  const gate = new Promise<void>((resolve) => { release = resolve; });
  let role = "athlete";
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: { ...athlete, active_role: role } }));
  await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "test" } }));
  await page.route("**/api/v1/auth/active-role/", async (route) => {
    role = route.request().postDataJSON().role;
    await route.fulfill({ json: { ...athlete, active_role: role } });
  });
  let switched = false;
  await page.route("**/api/v1/history/", async (route) => {
    if (!switched) {
      await gate;
      await route.fulfill({ json: [{ competition_id: 1, competition_title: "Старый результат", version: 1, row: { status: "classified", place: 1, score: "100" } }] });
    } else {
      await route.fulfill({ status: 503, json: { detail: "История недоступна" } });
    }
  });
  await page.goto("/history");
  await expect(page.getByText("Загрузка истории…")).toBeVisible();
  await page.getByRole("button", { name: "Тренер", exact: true }).click();
  await expect(page.getByText("Откройте роль спортсмена.")).toBeVisible();
  switched = true;
  release();
  await page.getByRole("button", { name: "Спортсмен", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "История недоступна" })).toBeVisible();
  await expect(page.getByText("Старый результат")).toHaveCount(0);
  await expect(page.getByText("Опубликованных результатов пока нет.")).toHaveCount(0);
});
