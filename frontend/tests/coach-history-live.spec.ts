import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";
import AxeBuilder from "@axe-core/playwright";
import { mkdir } from "node:fs/promises";

test("coach finds consenting athlete, requests link and both owners see lifecycle history", async ({ page, browser }) => {
  test.setTimeout(180000);
  const athleteContext = await browser.newContext();
  const athlete = await athleteContext.newPage();
  const name = `Вымышленный Поиск ${Date.now()}`;
  try {
    await athlete.goto("/register");
    await athlete.getByLabel("ФИО", { exact: true }).fill(name);
    await athlete.getByLabel("Электронная почта").fill(`coach-search-${Date.now()}@example.test`);
    await athlete.getByLabel("Дата рождения").fill("2000-01-01");
    await athlete.getByLabel("Пароль").fill("DemoOnly2026!");
    await athlete.getByRole("checkbox", { name: /Согласие на обработку/ }).check();
    await athlete.getByRole("button", { name: "Создать аккаунт" }).click();
    await expect(athlete).toHaveURL(/\/dashboard$/, { timeout: 20000 });
    await signIn(page, "demo.coach@example.test");
    await page.goto("/coach-links");
    await page.getByLabel("Имя спортсмена").fill(name);
    await page.getByRole("button", { name: "Найти в реестре" }).click();
    await page.getByLabel("Дисциплина для новой связи").selectOption({ label: "Программирование алгоритмическое" });
    await page.getByRole("button", { name: `Запросить связь: ${name}` }).click();
    await expect(page.getByText("Запрос сохранён.", { exact: false })).toBeVisible();
    await athlete.goto("/coach-links");
    // A newly registered athlete has exactly one incoming request.
    await athlete.getByRole("button", { name: "Подтвердить", exact: true }).click();
    await expect(athlete.getByText("Связь подтверждена", { exact: true })).toBeVisible();
    await page.reload();
    const management = page.locator("section").filter({ has: page.getByRole("heading", { name: /Управление связями/ }) });
    await management.getByLabel("Причина изменения статуса").fill("Вымышленный учебный перерыв");
    const linkCard = management.locator(".workflow-record").filter({ hasText: name });
    await linkCard.getByRole("button", { name: "Приостановить", exact: true }).click();
    await expect(management.getByText("Статус связи обновлён")).toBeVisible();
    await athlete.reload();
    const journal = athlete.locator("section").filter({ has: athlete.getByRole("heading", { name: /Журнал связей/ }) });
    await journal.locator("summary").click();
    await expect(journal.getByText("Причина: Вымышленный учебный перерыв")).toBeVisible();
    await expect(journal.getByText("Статус: Активна → Приостановлена")).toBeVisible();
    await mkdir("../docs/design/screenshots/mandatory", { recursive: true });
    for (const width of [1440, 768, 390]) for (const theme of ["light", "dark"]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.evaluate((value) => localStorage.setItem("fsp-theme", value), theme);
      await page.reload();
      const search = page.getByLabel("Имя спортсмена");
      await search.fill(name);
      await search.focus();
      await page.keyboard.press("Tab");
      await expect(page.getByRole("button", { name: "Найти в реестре", exact: true })).toBeFocused();
      await Promise.all([
        page.waitForResponse((response) => response.url().includes("/coach-athlete-directory/?")),
        page.keyboard.press("Enter"),
      ]);
      await expect(page.getByRole("button", { name: `Запросить связь: ${name}` })).toBeVisible();
      const coachJournal = page.locator("section").filter({ has: page.getByRole("heading", { name: /Журнал связей/ }) });
      const summary = coachJournal.locator("summary").first();
      await summary.focus();
      await page.keyboard.press("Enter");
      await expect(coachJournal.getByText("Причина: Вымышленный учебный перерыв")).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
      const scan = await new AxeBuilder({ page }).analyze();
      expect(scan.violations.filter((item) => ["serious", "critical"].includes(item.impact ?? ""))).toEqual([]);
      await page.screenshot({ path: `../docs/design/screenshots/mandatory/coach-links-${width}-${theme}.png`, fullPage: true });
    }
  } finally { await athleteContext.close(); }
});

test("federation correction ledger is readable from the qualification history", async ({ page }) => {
  await signIn(page, "demo.federation@example.test");
  await page.getByRole("button", { name: "Федерация", exact: true }).click();
  const records = await (await page.request.get("/api/v1/rank-history/")).json();
  expect(records.length).toBeGreaterThan(0);
  const record = records[0];
  const revised = `ДЕМО-ИСПР-${Date.now()}`;
  const reason = `Вымышленное исправление реквизитов ${revised}`;
  await page.goto("/qualifications");
  await page.getByLabel("Запись истории").selectOption(`rank:${record.id}`);
  await page.getByLabel("Исправленный номер приказа").fill(revised);
  await page.getByLabel("Причина исправления").fill(reason);
  await page.getByRole("button", { name: "Сохранить исправление", exact: true }).click();
  await expect(page.getByText("Исправление сохранено; предыдущие реквизиты остаются в журнале версий.")).toBeVisible();
  const section = page.locator("section").filter({ has: page.getByRole("heading", { name: /Реестр разрядов/ }) });
  const row = section.getByRole("row").filter({ hasText: revised });
  await row.locator("summary").click();
  await expect(row.getByText(`Причина: ${reason}`, { exact: true })).toBeVisible();
  await expect(row.getByText(`Приказ: ${record.order_number} → ${revised}`)).toBeVisible();
});
