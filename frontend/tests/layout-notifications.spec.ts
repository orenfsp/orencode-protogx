import { expect, test, type Page } from "@playwright/test";

async function mockCompetition(page: Page) {
  let status = "pending";
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace("/api/v1/", "");
    let body: unknown = [];
    let code = 200;
    if (path === "auth/me/") body = { id: 1, full_name: "Демо Федерация", roles: ["federation", "athlete"], active_role: "federation" };
    if (path === "auth/csrf/") body = { csrfToken: "test" };
    if (path === "competitions/1/") body = { id: 1, title: "Кубок области", discipline: 1, discipline_name: "Алгоритмическое программирование", template: 1, state: "published", starts_at: "2026-11-14T10:00:00Z", registration_deadline: "2026-11-10T10:00:00Z", age_group_details: [], stages: [], regulations: "Демонстрационные данные для проверки интерфейса.", level: "Региональный", competition_type: "Кубок", format: "online", location: "Оренбург" };
    if (path === "applications/") body = [
      { id: 1, athlete_name: "Демо Спортсмен", status },
      { id: 2, athlete_name: "Демонстрационный спортсмен с длинным именем для проверки переноса текста", status: "approved" },
      { id: 3, athlete_name: "Демо Спортсмен 3", status: "rejected" },
    ];
    if (path === "applications/1/decision/") {
      const payload = route.request().postDataJSON();
      if (payload.status === "rejected" && !payload.reason) { code = 400; body = ["Rejection reason is required"]; }
      else { status = payload.status; body = { status }; }
    }
    await route.fulfill({ status: code, json: body });
  });
}

for (const width of [1440, 768, 390]) {
  for (const dark of [false, true]) {
    test(`application cards and controls stay separate at ${width}px ${dark ? "dark" : "light"}`, async ({ page }, info) => {
      await page.setViewportSize({ width, height: 1000 });
      await page.addInitScript((theme) => localStorage.setItem("fsp-theme", theme), dark ? "dark" : "light");
      await mockCompetition(page);
      await page.goto("/competitions/1");
      const applications = page.locator("section").filter({ has: page.getByRole("heading", { name: "03 Заявки" }) });
      await expect(applications.locator(".workflow-record")).toHaveCount(3);
      await expect(page.locator("#th")).toBeChecked({ checked: dark });
      const defects = await applications.evaluate((section) => {
        const issues: string[] = [];
        for (const card of section.querySelectorAll(".workflow-record")) {
          const bounds = card.getBoundingClientRect();
          const stamp = card.querySelector(".bd")!.getBoundingClientRect();
          if (stamp.left < bounds.left || stamp.right > bounds.right || stamp.bottom > bounds.bottom) issues.push("stamp outside card");
          const name = card.querySelector("strong")!.getBoundingClientRect();
          if (name.bottom > stamp.top) issues.push("stamp overlaps name");
          const actions = card.querySelector(".workflow-actions");
          if (actions) {
            if (stamp.bottom > actions.getBoundingClientRect().top) issues.push("stamp overlaps actions");
            const controls = Array.from(actions.children).map((node) => node.getBoundingClientRect());
            for (let a = 0; a < controls.length; a++) for (let b = a + 1; b < controls.length; b++) {
              if (Math.min(controls[a].right, controls[b].right) > Math.max(controls[a].left, controls[b].left) && Math.min(controls[a].bottom, controls[b].bottom) > Math.max(controls[a].top, controls[b].top)) issues.push("controls overlap");
            }
          }
        }
        if (document.documentElement.scrollWidth > window.innerWidth) issues.push("page overflows");
        return issues;
      });
      expect(defects).toEqual([]);
      await applications.scrollIntoViewIfNeeded();
      await page.screenshot({ path: info.outputPath("application-cards.png"), fullPage: true });
    });
  }
}

test("errors are readable toasts, pause on interaction, disappear and can repeat; success can be closed", async ({ page }) => {
  await mockCompetition(page);
  await page.goto("/competitions/1");
  const reject = page.getByRole("button", { name: "Отклонить", exact: true });
  await reject.click();
  const alert = page.locator(".toast-viewport").getByRole("alert").filter({ hasText: "Укажите причину отказа." });
  await expect(alert).toBeVisible();
  await expect(alert).not.toContainText('["');
  await page.clock.install();
  await alert.hover();
  await page.clock.fastForward(7000);
  await expect(alert).toBeVisible();
  await page.mouse.move(0, 0);
  await page.clock.fastForward(6100);
  await expect(alert).toHaveCount(0);
  await reject.click();
  await expect(alert).toBeVisible();
  await alert.getByRole("button", { name: "Закрыть уведомление" }).click();
  await expect(alert).toHaveCount(0);
  await page.getByRole("button", { name: "Одобрить", exact: true }).click();
  const success = page.getByRole("status").filter({ hasText: "Заявка одобрена" });
  await expect(success).toBeVisible();
  await success.getByRole("button", { name: "Закрыть уведомление" }).click();
  await expect(success).toHaveCount(0);
});

test("nested field errors use the same toast on the login screen", async ({ page }) => {
  await page.route("**/api/v1/**", (route) => route.fulfill({ status: route.request().url().includes("auth/me/") ? 401 : route.request().url().includes("auth/login/") ? 400 : 200, json: route.request().url().includes("auth/login/") ? { email: ["Enter a valid email address."], non_field_errors: ["Проверьте данные входа."] } : { csrfToken: "test" } }));
  await page.goto("/login");
  await page.getByLabel("Электронная почта").fill("demo@example.test");
  await page.getByLabel("Пароль").fill("invalid-password");
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await expect(page.locator(".toast-viewport").getByRole("alert")).toContainText("Электронная почта: Введите корректный адрес электронной почты. Проверьте данные входа.");
  await expect(page.locator(".auth-form .toast")).toHaveCount(0);
});
