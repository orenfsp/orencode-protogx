import { expect, test } from "@playwright/test";

const user = { id: 7, email: "user@example.test", full_name: "Тестовый пользователь", roles: ["athlete", "coach", "judge"], active_role: "athlete" };
const events = [{ id: 12, title: "Открытый турнир", state: "published", starts_at: "2030-05-10T12:00:00Z", discipline_name: "Алгоритмы" }];
const application = { id: 3, competition: 12, athlete: 7, athlete_name: "Тестовый спортсмен", age_group: 1, submitted_by: 7, status: "rejected", decision_reason: "Не подходит возрастная группа" };
const assignment = { id: 4, competition: 12, judge: 7, judge_name: "Тестовый судья", role_label: "Главный судья" };

test("athlete, coach and judge see their own role's competitions", async ({ page }) => {
  let role = "athlete";
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: { ...user, active_role: role } }));
  await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "test" } }));
  await page.route("**/api/v1/auth/active-role/", async (route) => {
    role = route.request().postDataJSON().role;
    await route.fulfill({ json: { ...user, active_role: role } });
  });
  await page.route("**/api/v1/competitions/", (route) => route.fulfill({ json: events }));
  await page.route("**/api/v1/applications/", (route) => route.fulfill({ json: [application] }));
  await page.route("**/api/v1/judge-assignments/", (route) => route.fulfill({ json: [assignment] }));
  await page.goto("/my-competitions");
  let row = page.getByRole("row", { name: /Открытый турнир/ });
  await expect(row).toContainText("Отклонена");
  await expect(row).toContainText("Не подходит возрастная группа");
  await expect(row.getByRole("link")).toHaveAttribute("href", "/competitions/12");
  await expect(page.getByRole("columnheader", { name: "Спортсмен" })).toHaveCount(0);

  await page.getByRole("button", { name: "Тренер", exact: true }).click();
  await expect(page.getByRole("columnheader", { name: "Спортсмен" })).toBeVisible();
  await expect(row).toContainText("Тестовый спортсмен");

  await page.getByRole("button", { name: "Судья", exact: true }).click();
  row = page.getByRole("row", { name: /Открытый турнир/ });
  await expect(page.getByRole("heading", { name: /Назначения/ })).toBeVisible();
  await expect(row).toContainText("Главный судья");
  await expect(page.getByText("Не подходит возрастная группа")).toHaveCount(0);
});

test("loading and failure do not appear as an empty list, and retry loads data", async ({ page }) => {
  let release: () => void = () => {};
  const gate = new Promise<void>((resolve) => { release = resolve; });
  let fail = true;
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
  await page.route("**/api/v1/competitions/", (route) => route.fulfill({ json: events }));
  await page.route("**/api/v1/applications/", async (route) => {
    await gate;
    await route.fulfill(fail ? { status: 503, json: { detail: "Список недоступен" } } : { json: [application] });
  });
  await page.goto("/my-competitions");
  await expect(page.getByText("Загрузка соревнований…")).toBeVisible();
  await expect(page.getByText("Заявок пока нет.")).toHaveCount(0);
  release();
  await expect(page.getByRole("alert").filter({ hasText: "Список недоступен" })).toBeVisible();
  await expect(page.getByText("Заявок пока нет.")).toHaveCount(0);
  fail = false;
  await page.getByRole("button", { name: "Попробовать снова" }).click();
  await expect(page.getByRole("row", { name: /Открытый турнир/ })).toBeVisible();
});

test("dashboard links to the role-aware page", async ({ page }) => {
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
  await page.route("**/api/v1/auth/dashboard/", (route) => route.fulfill({ json: { role: "athlete", metrics: [], guardian_status: null } }));
  await page.goto("/dashboard");
  await expect(page.getByRole("link", { name: "Мои соревнования" })).toHaveAttribute("href", "/my-competitions");
});

test("late applications do not replace judge assignments after switching roles", async ({ page }) => {
  let role = "athlete";
  let release: () => void = () => {};
  const gate = new Promise<void>((resolve) => { release = resolve; });
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: { ...user, active_role: role } }));
  await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "test" } }));
  await page.route("**/api/v1/auth/active-role/", async (route) => {
    role = route.request().postDataJSON().role;
    await route.fulfill({ json: { ...user, active_role: role } });
  });
  await page.route("**/api/v1/competitions/", (route) => route.fulfill({ json: events }));
  await page.route("**/api/v1/applications/", async (route) => { await gate; await route.fulfill({ json: [application] }); });
  await page.route("**/api/v1/judge-assignments/", (route) => route.fulfill({ json: [assignment] }));
  const pendingRequest = page.waitForRequest("**/api/v1/applications/");
  await page.goto("/my-competitions");
  await pendingRequest;
  await expect(page.getByText("Загрузка соревнований…")).toBeVisible();
  await page.getByRole("button", { name: "Судья", exact: true }).click();
  await expect(page.getByText("Главный судья")).toBeVisible();
  const lateResponse = page.waitForResponse("**/api/v1/applications/");
  release();
  await lateResponse;
  await expect(page.getByText("Не подходит возрастная группа")).toHaveCount(0);
  await expect(page.getByText("Главный судья")).toBeVisible();
});

test("an inaccessible event is not linked or given fabricated details", async ({ page }) => {
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
  await page.route("**/api/v1/competitions/", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/v1/applications/", (route) => route.fulfill({ json: [application] }));
  await page.goto("/my-competitions");
  const row = page.getByRole("row", { name: /Соревнование недоступно/ });
  await expect(row).toBeVisible();
  await expect(row.getByRole("link")).toHaveCount(0);
});

test("applications are reachable on desktop, tablet and mobile in both themes", async ({ page }, testInfo) => {
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
  await page.route("**/api/v1/competitions/", (route) => route.fulfill({ json: events }));
  await page.route("**/api/v1/applications/", (route) => route.fulfill({ json: [application] }));
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await page.goto("/my-competitions");
    const row = page.getByRole("row", { name: /Открытый турнир/ });
    await expect(row).toBeVisible();
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    for (const dark of [false, true]) {
      if (await page.locator("#th").isChecked() !== dark) {
        if (width <= 900) await page.locator(".mobile-theme").click();
        else await page.locator("label[for=th].tgl").click();
      }
      await expect(page.locator("#th")).toHaveJSProperty("checked", dark);
      await row.getByRole("link").focus();
      await expect(row.getByRole("link")).toBeFocused();
      await page.screenshot({ path: testInfo.outputPath(`my-competitions-${width}-${dark ? "dark" : "light"}.png`) });
    }
    if (width === 390) {
      const region = page.getByRole("region", { name: "Заявки на соревнования" });
      await expect.poll(() => region.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(true);
      await region.focus();
      await page.keyboard.press("ArrowRight");
      await expect.poll(() => region.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0);
    }
  }
});
