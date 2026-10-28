import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { signIn } from "./helpers";

test("live consent renewal, RUSADA profile, real XLSX, category and SMTP inbox", async ({ page, browser, request }, testInfo) => {
  test.setTimeout(240000);
  const context = await browser.newContext();
  const judge = await context.newPage();
  page.setDefaultTimeout(15000);
  judge.setDefaultTimeout(15000);
  try {
    await signIn(judge, "demo.judge@example.test");
    await judge.goto("/qualifications");
    const categories = await (await judge.request.get("/api/v1/judge-category-history/")).json();
    if (categories.some((item: { category: string }) => item.category === "third")) await judge.getByLabel("Тип заявки").selectOption("confirm");
    await judge.getByRole("combobox", { name: /^Категория/ }).selectOption("third");
    await judge.getByRole("button", { name: "Отправить в федерацию" }).click();
    await expect(judge.getByRole("status")).toContainText("Заявка отправлена");
    const applications = await (await judge.request.get("/api/v1/judge-category-applications/")).json();
    const applicationId = applications.find((item: { status: string }) => item.status === "pending").id;
    await signIn(page, "demo.federation@example.test");
    await page.getByRole("button", { name: "Федерация", exact: true }).click();
    await page.goto("/qualifications");
    const record = page.locator(".workflow-record").filter({ hasText: "Демо Судья" });
    await record.getByLabel("Номер приказа").fill("ДЕМО-КАТЕГОРИЯ");
    const until = new Date(); until.setFullYear(until.getFullYear() + 1);
    await record.getByLabel("Действует до").fill(until.toISOString().slice(0, 10));
    await record.getByRole("button", { name: "Присвоить" }).click();
    await expect(page.getByRole("status")).toContainText("запись добавлена в историю");
    await judge.goto("/qualifications");
    await expect(judge.getByText("ДЕМО-КАТЕГОРИЯ").first()).toBeVisible();
    const notifications = await (await judge.request.get("/api/v1/notifications/")).json();
    const notice = notifications.find((item: { kind: string }) => item.kind === "judge_category_application.approved");
    expect(notice).toBeTruthy();
    const denial = await page.request.get(`/api/v1/notifications/`);
    expect(denial.ok()).toBeTruthy();
    const csrf = await (await page.request.get("/api/v1/auth/csrf/")).json();
    expect((await page.request.post(`/api/v1/notifications/${notice.id}/read/`, { headers: { "X-CSRFToken": csrf.csrfToken } })).status()).toBe(404);
    await expect.poll(async () => {
      const items = await (await judge.request.get("/api/v1/notifications/")).json();
      return items.find((item: { id: number }) => item.id === notice.id)?.status;
    }, { timeout: 90000, intervals: [1000, 3000, 5000] }).toBe("sent");
    const mailpit = process.env.FSP_MAILPIT_URL ?? "http://127.0.0.1:18025";
    const messages = await (await request.get(`${mailpit}/api/v1/search`, { params: { query: "to:demo.judge@example.test" } })).json();
    expect(messages.total).toBeGreaterThan(0);
    await testInfo.attach("smtp-delivery", { body: JSON.stringify({ applicationId, notificationId: notice.id, capturedMessages: messages.total }), contentType: "application/json" });
    await judge.goto("/dashboard");
    const section = judge.locator("section").filter({ has: judge.getByRole("heading", { name: /Уведомления/ }) });
    const read = section.getByRole("button", { name: /Отметить прочитанным/ }).first();
    await read.focus(); await expect(read).toBeFocused(); await read.press("Enter");
    await expect(section.getByText("Прочитано").first()).toBeVisible();
  } catch (error) {
    console.log("Judge page:", await judge.locator("body").innerText().catch(() => "unavailable"));
    await judge.screenshot({ path: testInfo.outputPath("judge-failure.png"), fullPage: true }).catch(() => {});
    throw error;
  } finally { await context.close(); }

  // The seeded federation account also has athlete role, with no password/session duplication.
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Спортсмен", exact: true }).click();
  await page.getByRole("button", { name: "Отозвать согласие" }).click();
  await expect(page.getByText("Согласие не действует", { exact: true })).toBeVisible();
  await page.getByRole("checkbox", { name: "Подтверждаю согласие на обработку персональных данных" }).check();
  await page.getByRole("button", { name: "Возобновить согласие" }).click();
  await expect(page.getByText("Согласие действует", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Мой профиль и РУСАДА" }).click();
  await page.getByLabel("Дата прохождения курса").fill("2026-01-10");
  await page.getByLabel("Ссылка на сертификат").fill("https://example.test/fictional-rusada");
  await page.getByRole("button", { name: "Сохранить отметку РУСАДА" }).click();
  await expect(page.getByRole("status")).toHaveText("Отметка РУСАДА сохранена");
  await page.reload();
  await expect(page.getByLabel("Ссылка на сертификат")).toHaveValue("https://example.test/fictional-rusada");
  await page.goto("/history");
  const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("link", { name: "Скачать отчёт выступлений · XLSX" }).click()]);
  const target = testInfo.outputPath("athlete-participation.xlsx");
  await download.saveAs(target);
  expect((await readFile(target)).subarray(0, 2).toString()).toBe("PK");
});
