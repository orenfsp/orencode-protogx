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
        await page.goto(target === "reference" ? reference : site, { waitUntil: "networkidle" });
        if (target === "site") await page.locator("#disciplines tbody tr").first().waitFor();
        if (theme === "dark") {
          if (target === "reference") await page.locator("#th").evaluate((checkbox) => { checkbox.checked = true; });
          else await page.waitForFunction(() => document.querySelector("#th")?.checked);
          if (!(await page.locator("#th").isChecked())) throw new Error(`${target} dark theme did not activate`);
        }
        await page.evaluate(() => { document.documentElement.style.scrollBehavior = "auto"; window.scrollTo(0, 0); });
        const screenshotPath = path.join(output, `${target}-${viewport.name}-${theme}.png`);
        await page.screenshot({ path: screenshotPath });
        console.log(screenshotPath);
        await context.close();
      }
    }
  }
} finally {
  await browser.close();
}
