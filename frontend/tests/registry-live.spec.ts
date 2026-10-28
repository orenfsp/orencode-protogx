import { execFileSync } from "node:child_process";
import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test("live registry history and two-year XLSX agree", async ({ page }, testInfo) => {
  await signIn(page, "demo.federation@example.test");
  await page.getByRole("button", { name: "Федерация", exact: true }).click();
  await page.goto("/registry");
  await page.getByLabel("Поиск").fill("Демо Спортсмен");
  await page.getByRole("button", { name: "Демо Спортсмен", exact: true }).click();
  await expect(page.getByText("Демо центр Вектор").last()).toBeVisible();
  await expect(page.getByText("Демо клуб Орбита").last()).toBeVisible();
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
});
