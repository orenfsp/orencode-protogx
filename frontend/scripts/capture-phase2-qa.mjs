import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const output = path.resolve(frontendRoot, "..", "docs", "design", "screenshots");
const site = process.env.FSP_WEB_URL ?? "http://127.0.0.1:3000";
const viewports = [{ name: "1440", width: 1440, height: 900 }, { name: "768", width: 768, height: 900 }, { name: "390", width: 390, height: 844 }];
await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
async function session(email) {
  const context = await browser.newContext();
  const page = await context.newPage();
  await page.goto(`${site}/login`);
  await page.getByLabel("Электронная почта").fill(email);
  await page.getByLabel("Пароль").fill("DemoOnly2026!");
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await page.waitForURL("**/dashboard");
  const storage = await context.storageState();
  await context.close();
  return storage;
}
try {
  const federation = await session("demo.federation@example.test");
  const athlete = await session("demo.athlete@example.test");
  const context = await browser.newContext({ storageState: federation });
  const page = await context.newPage();
  await page.goto(`${site}/competitions`);
  const items = await page.evaluate(async () => (await fetch("/api/v1/competitions/")).json());
  const latest = items.filter((item) => item.state === "published").sort((a, b) => b.id - a.id)[0];
  if (!latest) throw new Error("No published competition available for Phase 2 visual QA");
  await context.close();
  const screens = [
    { name: "calendar", storage: federation, url: "/competitions", ready: ".tw table" },
    { name: "competition-federation", storage: federation, url: `/competitions/${latest.id}`, ready: ".workflow-regulations", marker: "Версия 1" },
    { name: "competition-athlete", storage: athlete, url: `/competitions/${latest.id}`, ready: ".workflow-regulations", marker: "Ваша заявка: Одобрена" },
    { name: "history", storage: athlete, url: "/history", ready: ".tw table" },
  ];
  for (const viewport of viewports) for (const theme of ["light", "dark"]) for (const screen of screens) {
    const capture = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, deviceScaleFactor: 1, storageState: screen.storage });
    if (theme === "dark") await capture.addInitScript(() => localStorage.setItem("fsp-theme", "dark"));
    const target = await capture.newPage();
    await target.goto(`${site}${screen.url}`, { waitUntil: "domcontentloaded" });
    await target.locator(screen.ready).first().waitFor();
    if (screen.marker) await target.getByText(screen.marker, { exact: false }).first().waitFor();
    await target.evaluate(() => document.fonts.ready);
    await target.waitForFunction((expected) => getComputedStyle(document.body).backgroundColor === expected, theme === "dark" ? "rgb(28, 27, 69)" : "rgb(255, 255, 255)");
    if (viewport.width <= 900 && !(await target.locator(".mobtab").isVisible())) throw new Error(`Mobile navigation hidden on ${screen.name}`);
    const file = path.join(output, `phase2-${screen.name}-${viewport.name}-${theme}.png`);
    await target.screenshot({ path: file, fullPage: true });
    console.log(file);
    await capture.close();
  }
} finally { await browser.close(); }
