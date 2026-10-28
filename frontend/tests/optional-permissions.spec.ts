import { expect, test } from "@playwright/test";

test("optional workspace clears previously loaded private data after access is revoked", async ({ page }) => {
  await page.route("**/api/v1/auth/me/", route => route.fulfill({ json: { id: 501, email: "fictional@example.test", full_name: "Вымышленный спортсмен", roles: ["athlete"], active_role: "athlete" } }));
  await page.route("**/api/v1/auth/csrf/", route => route.fulfill({ json: { csrfToken: "fictional-browser-state-token" } }));
  let revoked = false;
  await page.route("**/api/v1/certificates/", route => {
    if (route.request().method() === "POST") revoked = true;
    return revoked ? route.fulfill({ status: 403, json: { detail: "Доступ отозван" } }) : route.fulfill({ json: { items: [{ id: 7, number: "ФСП-ДЕМО", competition: "Приватное вымышленное соревнование", status: "valid" }], options: { applications: [{ value: 1, label: "Вымышленное участие" }], certificates: [] } } });
  });
  await page.goto("/certificates");
  await expect(page.getByText("Приватное вымышленное соревнование", { exact: true })).toBeVisible();
  await page.getByLabel("Участие", { exact: true }).selectOption("1");
  await page.getByRole("button", { name: "Сформировать справку", exact: true }).click();
  await expect(page.getByText("Приватное вымышленное соревнование", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Сформировать справку", exact: true })).toHaveCount(0);
  await expect(page.getByRole("alert").filter({ hasText: "Доступ отозван" })).toBeVisible();
  await page.getByRole("button", { name: "Повторить", exact: true }).click();
  await expect(page.getByText("Приватное вымышленное соревнование", { exact: true })).toHaveCount(0);
});
