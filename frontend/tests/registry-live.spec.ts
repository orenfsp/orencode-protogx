import { execFileSync } from "node:child_process";
import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test("live registry history and two-year XLSX agree", async ({ page }, testInfo) => {
  await signIn(page, "demo.federation@example.test");
  await page.getByRole("button", { name: "Федерация", exact: true }).click();
  await page.goto("/registry");
  await page.getByLabel("Поиск").fill("Демо Спортсмен");
  await page.getByRole("button", { name: "Демо Спортсмен", exact: true }).click();
  await expect(page.locator("li").filter({ hasText: "Демо центр Вектор" })).toBeVisible();
  await expect(page.locator("li").filter({ hasText: "Демо клуб Орбита" })).toBeVisible();
  const participation = page.locator("li").filter({ hasText: "участие" }).first();
  await participation.getByRole("button", { name: "Исправить" }).click();
  await page.getByLabel("Исправленное начало").fill("2024-01-02");
  await page.getByLabel("Причина исправления").fill("Уточнение вымышленной даты");
  await page.getByRole("button", { name: "Сохранить исправление" }).click();
  await expect(page.locator("li").filter({ hasText: "2024-01-02 — по настоящее время · участие" })).toBeVisible();
  const organizations = await page.request.get("/api/v1/organizations/?search=Орбита");
  expect(organizations.ok()).toBeTruthy();
  const organizationId = (await organizations.json()).results[0].id;
  await page.getByLabel("Новая организация").selectOption(String(organizationId));
  await page.getByLabel("Дата перевода").fill("2025-06-01");
  await page.getByRole("button", { name: "Сохранить перевод" }).click();
  await expect(page.getByText("2025-06-01 — по настоящее время · Демо клуб Орбита")).toBeVisible();
  await page.goto("/analytics/participation");
  const firstYear = page.getByRole("row").filter({ hasText: "2024" }).first();
  const secondYear = page.getByRole("row").filter({ hasText: "2025" }).first();
  await expect(firstYear.locator("td").nth(1)).toHaveText("2");
  await expect(secondYear.locator("td").nth(1)).toHaveText("3");
  const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: "Скачать XLSX" }).click()]);
  const file = testInfo.outputPath("participation.xlsx");
  await download.saveAs(file);
  const python = process.env.FSP_PYTHON || "python";
  execFileSync(python, ["-c", "import sys; from openpyxl import load_workbook; w=load_workbook(sys.argv[1],data_only=True); assert w['Итоги']['B4'].value==2 and w['Итоги']['B5'].value==3; assert 'Дисциплины' in w.sheetnames", file]);
  await page.goto("/registry");
  for (const label of ["Тренеры", "Судьи", "Организации"]) {
    await page.getByRole("button", { name: label, exact: true }).click();
    await expect(page.getByRole("heading", { name: label })).toBeVisible();
  }
  await page.getByRole("button", { name: "Спортсмен", exact: true }).click();
  await expect(page.getByText("Для просмотра реестров выберите роль федерации.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Спортсмен", exact: true })).toHaveAttribute("aria-pressed", "true");
  expect((await page.request.get("/api/v1/organizations/")).status()).toBe(403);
  await page.getByRole("button", { name: "Выйти", exact: true }).click();
  await page.goto("/analytics/participation");
  await expect(page.getByText("Для просмотра аналитики выберите роль федерации.")).toBeVisible();
});
