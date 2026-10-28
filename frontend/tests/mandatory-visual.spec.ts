import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir } from "node:fs/promises";
import { signIn } from "./helpers";

for (const width of [1440, 768, 390]) for (const theme of ["light", "dark"]) {
  test(`mandatory cabinets ${width} ${theme}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 });
    await page.addInitScript((value) => localStorage.setItem("fsp-theme", value), theme);
    await signIn(page, "demo.athlete@example.test");
    const directory = "../docs/design/screenshots/mandatory";
    await mkdir(directory, { recursive: true });
    for (const route of ["dashboard", "profile", "history", "qualifications"]) {
      await page.goto(`/${route}`);
      await expect(page.locator("h1")).toBeVisible();
      if (route === "dashboard") await expect(page.getByRole("button", { name: "Обновить уведомления" })).toBeVisible();
      if (route === "profile") await expect(page.getByLabel("Дата прохождения курса")).toBeVisible();
      if (route === "history") await expect(page.getByRole("table")).toBeVisible();
      if (route === "qualifications") await expect(page.getByRole("heading", { name: /Подать заявку на разряд/ })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
      const scan = await new AxeBuilder({ page }).analyze();
      expect(scan.violations.filter((item) => ["serious", "critical"].includes(item.impact ?? ""))).toEqual([]);
      await page.screenshot({ path: `${directory}/${route}-${width}-${theme}.png`, fullPage: true });
    }
  });
}
