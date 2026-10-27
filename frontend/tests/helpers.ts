import { expect, type Page } from "@playwright/test";

export async function signIn(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Электронная почта").fill(email);
  await page.getByLabel("Пароль").fill("DemoOnly2026!");
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const [response] = await Promise.all([
      page.waitForResponse((value) => value.url().endsWith("/api/v1/auth/login/") && value.request().method() === "POST"),
      page.getByRole("button", { name: "Войти", exact: true }).click(),
    ]);
    if (response.status() !== 429) {
      expect(response.ok(), await response.text()).toBeTruthy();
      await expect(page).toHaveURL(/\/dashboard$/);
      return;
    }
    const retryAfter = Number(response.headers()["retry-after"] ?? 60);
    await page.waitForTimeout((Number.isFinite(retryAfter) ? retryAfter : 60) * 1000 + 1000);
  }
  throw new Error("Login remained rate limited after three retries");
}
