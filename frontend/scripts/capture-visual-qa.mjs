import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const frontendRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = path.resolve(frontendRoot, "..");
const output = path.join(repoRoot, "docs", "design", "screenshots");
const reference = pathToFileURL(path.join(repoRoot, "docs", "design", "fsp-reference.html")).href;
const site = process.env.FSP_WEB_URL ?? "http://127.0.0.1:3000";
const viewports = [
  { name: "1440", width: 1440, height: 900 },
  { name: "768", width: 768, height: 900 },
  { name: "390", width: 390, height: 844 },
];

await mkdir(output, { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
try {
  for (const viewport of viewports) {
    for (const theme of ["light", "dark"]) {
      for (const target of ["reference", "site"]) {
        const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, deviceScaleFactor: 1 });
        const page = await context.newPage();
        if (theme === "dark" && target === "site") {
          await context.addInitScript(() => {
            try { localStorage.setItem("fsp-theme", "dark"); } catch { /* about:blank has no storage */ }
          });
        }
        await page.goto(target === "reference" ? reference : site, { waitUntil: "domcontentloaded" });
        if (target === "site") await page.locator("#disciplines tbody tr").first().waitFor();
        await page.evaluate(() => document.fonts.ready);
        if (theme === "dark") {
          if (target === "reference") await page.locator("#th").evaluate((checkbox) => { checkbox.checked = true; });
          else await page.waitForFunction(() => document.querySelector("#th")?.checked);
          if (!(await page.locator("#th").isChecked())) throw new Error(`${target} dark theme did not activate`);
        }
        await page.waitForFunction(
          (expected) => getComputedStyle(document.body).backgroundColor === expected,
          theme === "dark" ? "rgb(28, 27, 69)" : "rgb(255, 255, 255)",
        );
        await page.evaluate(() => { document.documentElement.style.scrollBehavior = "auto"; window.scrollTo(0, 0); });
        const screenshotPath = path.join(output, `${target}-${viewport.name}-${theme}.png`);
        await page.screenshot({ path: screenshotPath });
        console.log(screenshotPath);
        await context.close();
      }
    }
  }

  const screens = [
    { name: "calendar", path: "/competitions" },
    { name: "login", path: "/login" },
    { name: "register", path: "/register" },
    { name: "privacy", path: "/privacy" },
    { name: "federation", email: "demo.federation@example.test" },
    { name: "athlete", email: "demo.athlete@example.test" },
    { name: "coach", email: "demo.coach@example.test" },
    { name: "judge", email: "demo.judge@example.test" },
  ];
  const roleSessions = new Map();
  for (const screen of screens.filter((item) => item.email)) {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(`${site}/login`, { waitUntil: "domcontentloaded" });
    await page.getByLabel("Электронная почта").fill(screen.email);
    await page.getByLabel("Пароль").fill("DemoOnly2026!");
    await page.getByRole("button", { name: "Войти", exact: true }).click();
    await page.waitForURL("**/dashboard");
    await page.locator(".dashboard-metrics").waitFor();
    roleSessions.set(screen.name, await context.storageState());
    await context.close();
  }
  for (const viewport of viewports) {
    for (const theme of ["light", "dark"]) {
      for (const screen of screens) {
        const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, deviceScaleFactor: 1, storageState: roleSessions.get(screen.name) });
        if (theme === "dark") await context.addInitScript(() => localStorage.setItem("fsp-theme", "dark"));
        const page = await context.newPage();
        if (screen.email) {
          await page.goto(`${site}/dashboard`, { waitUntil: "domcontentloaded" });
          await page.locator(".dashboard-metrics").waitFor();
        } else {
          await page.goto(`${site}${screen.path}`, { waitUntil: "domcontentloaded" });
          await page.locator("section.blk").first().waitFor();
        }
        await page.evaluate(() => document.fonts.ready);
        await page.waitForFunction(
          (expected) => getComputedStyle(document.body).backgroundColor === expected,
          theme === "dark" ? "rgb(28, 27, 69)" : "rgb(255, 255, 255)",
        );
        if (viewport.width <= 900 && !(await page.locator(".mobtab").isVisible())) throw new Error(`Mobile navigation hidden on ${screen.name}`);
        await page.evaluate(() => { document.documentElement.style.scrollBehavior = "auto"; window.scrollTo(0, 0); });
        const screenshotPath = path.join(output, `site-${screen.name}-${viewport.name}-${theme}.png`);
        await page.screenshot({ path: screenshotPath, fullPage: true });
        console.log(screenshotPath);
        await context.close();
      }
    }
  }
} finally {
  await browser.close();
}
