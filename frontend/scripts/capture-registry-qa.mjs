import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const output = path.resolve(frontend, "..", "docs/design/screenshots");
const site = process.env.FSP_WEB_URL ?? "http://127.0.0.1:3000";
const browser = await chromium.launch({ channel: "chrome", headless: true });
await mkdir(output, { recursive: true });
try {
  const login = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await login.newPage();
  await page.goto(`${site}/login`);
  await page.getByLabel("Электронная почта").fill("demo.federation@example.test");
  await page.getByLabel("Пароль").fill("DemoOnly2026!");
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await page.waitForURL("**/dashboard");
  await page.getByRole("button", { name: "Федерация", exact: true }).click();
  await page.getByRole("button", { name: "Федерация", exact: true }).waitFor();
  await page.waitForFunction(() => document.querySelector('button[aria-pressed="true"]')?.textContent?.includes("Федерация"));
  const storage = await login.storageState();
  await login.close();
  for (const width of [1440, 768, 390]) for (const theme of ["light", "dark"]) for (const screen of ["registry", "analytics"]) {
    const context = await browser.newContext({ storageState: storage, viewport: { width, height: width === 390 ? 844 : 900 } });
    await context.addInitScript((value) => localStorage.setItem("fsp-theme", value), theme);
    const target = await context.newPage();
    await target.goto(`${site}${screen === "registry" ? "/registry" : "/analytics/participation"}`);
    await target.locator(".tw table").first().waitFor();
    await target.evaluate(() => document.fonts.ready);
    await target.waitForFunction((dark) => getComputedStyle(document.body).backgroundColor === (dark ? "rgb(28, 27, 69)" : "rgb(255, 255, 255)"), theme === "dark");
    if (width <= 900 && !(await target.locator(".mobtab").isVisible())) throw new Error("Mobile navigation is hidden");
    const overflow = await target.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    if (overflow) throw new Error(`Unexpected page overflow: ${screen} ${width} ${theme}`);
    const file = path.join(output, `phase33-${screen}-${width}-${theme}.png`);
    await target.screenshot({ path: file, fullPage: true });
    console.log(file);
    await context.close();
  }
} finally { await browser.close(); }
