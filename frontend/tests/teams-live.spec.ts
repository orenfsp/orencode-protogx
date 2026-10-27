import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { signIn } from "./helpers";

test("live published ratings to manually selected team and documents", async ({ page }, testInfo) => {
  const teamName = `E2E ${Date.now()}`;
  await signIn(page, "demo.federation@example.test");
  await page.getByRole("button", { name: "Федерация", exact: true }).click();
  await page.goto("/ratings");
  await page.getByLabel("Сезон").selectOption("2026");
  await page.getByLabel("Дисциплина").selectOption("algorithmic");
  await page.getByRole("button", { name: "Демо Спортсмен", exact: true }).click();
  await expect(page.getByText("публикация v1").first()).toBeVisible();
  await page.goto("/teams");
  await page.getByLabel("Сезон").selectOption({ label: "Сезон 2026" });
  await page.getByLabel("Дисциплина").selectOption("algorithmic");
  await page.getByLabel("Возрастная группа").selectOption({ label: "Взрослые" });
  await page.getByLabel("Название новой команды").fill(teamName);
  await page.getByRole("button", { name: "Создать команду" }).click();
  await expect(page.getByRole("heading", { name: teamName })).toBeVisible();
  await page.getByRole("row").filter({ hasText: "demo.athlete2@example.test" }).getByRole("button", { name: "Добавить" }).click();
  const candidate = page.getByRole("row").filter({ hasText: "demo.athlete@example.test" });
  await candidate.getByRole("button", { name: "Добавить" }).click();
  const item = page.locator("ol.at li").filter({ hasText: "Демо Спортсмен" }).filter({ hasNotText: "Два" }).filter({ hasNotText: "Три" });
  await expect(item).toBeVisible();
  await item.getByRole("button", { name: "↑" }).click();
  await expect(page.locator("ol.at li").first()).toContainText("Демо Спортсмен");
  await page.reload();
  await page.getByLabel("Сезон").selectOption({ label: "Сезон 2026" });
  await page.getByLabel("Дисциплина").selectOption("algorithmic");
  await page.getByLabel("Возрастная группа").selectOption({ label: "Взрослые" });
  await page.getByRole("button", { name: teamName }).click();
  await expect(page.locator("ol.at li").first()).toContainText("Демо Спортсмен");
  await page.getByRole("button", { name: "Утвердить состав" }).click();
  await expect(page.getByRole("button", { name: "Утвердить состав" })).toHaveCount(0);
  for (const [label, signature] of [["Скачать состав PDF", "%PDF"], ["Состав DOCX", "PK"], ["Проект порядка PDF", "%PDF"], ["Порядок DOCX", "PK"]]) {
    const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: label }).click()]);
    const path = testInfo.outputPath(download.suggestedFilename());
    await download.saveAs(path);
    expect((await readFile(path)).subarray(0, signature.length).toString()).toBe(signature);
  }
});
