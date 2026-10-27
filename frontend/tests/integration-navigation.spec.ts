import { expect, test } from "@playwright/test";

for (const width of [1440, 390]) {
  for (const role of ["federation", "athlete", "coach", "judge"] as const) {
    test(`${role} dashboard retains both applicable navigation links at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      const user = { id: 1, full_name: "Тест", email: "fiction@example.test", roles: [role], active_role: role };
      await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
      await page.route("**/api/v1/auth/dashboard/", (route) => route.fulfill({ json: { role, metrics: [], guardian_status: null } }));
      await page.goto("/dashboard");
      const qualifications = page.getByRole("link", { name: "Разряды и категории", exact: true });
      const competitions = page.getByRole("link", { name: "Мои соревнования", exact: true });
      await expect(qualifications).toHaveCount(1);
      await expect(qualifications).toBeVisible();
      await expect(qualifications).toHaveAttribute("href", "/qualifications");
      if (role === "federation") {
        await expect(competitions).toHaveCount(0);
      } else {
        await expect(competitions).toHaveCount(1);
        await expect(competitions).toBeVisible();
        await expect(competitions).toHaveAttribute("href", "/my-competitions");
      }
    });
  }
}

test("rapid role switches are serialized and the newest role wins", async ({ page }) => {
  let activeRole = "federation";
  let startFirst: (() => void) | undefined;
  let releaseFirst: (() => void) | undefined;
  let firstFinished: (() => void) | undefined;
  let secondStarted = false;
  const firstStarted = new Promise<void>((resolve) => { startFirst = resolve; });
  const firstReleased = new Promise<void>((resolve) => { releaseFirst = resolve; });
  const firstDone = new Promise<void>((resolve) => { firstFinished = resolve; });
  const user = (role: string) => ({ id: 1, full_name: "Тест", email: "fiction@example.test", roles: ["federation", "athlete", "judge"], active_role: role });
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user(activeRole) }));
  await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "test" } }));
  await page.route("**/api/v1/auth/dashboard/", (route) => route.fulfill({ json: { role: activeRole, metrics: [], guardian_status: null } }));
  await page.route("**/api/v1/auth/active-role/", async (route) => {
    const role = route.request().postDataJSON().role as string;
    activeRole = role;
    if (role === "athlete") {
      startFirst?.();
      await firstReleased;
      await route.fulfill({ json: user(role) });
      firstFinished?.();
    } else {
      secondStarted = true;
      await route.fulfill({ json: user(role) });
    }
  });
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Спортсмен", exact: true }).click();
  await firstStarted;
  await page.getByRole("button", { name: "Судья", exact: true }).click();
  expect(secondStarted).toBe(false);
  releaseFirst?.();
  await firstDone;
  await expect(page.getByRole("button", { name: "Судья", exact: true })).toHaveAttribute("aria-pressed", "true");
  expect(activeRole).toBe("judge");
});

test("logout invalidates a pending role response", async ({ page }) => {
  let signedOut = false;
  let release: (() => void) | undefined;
  let started: (() => void) | undefined;
  const pending = new Promise<void>((resolve) => { release = resolve; });
  const requested = new Promise<void>((resolve) => { started = resolve; });
  const user = { id: 1, full_name: "Тест", email: "fiction@example.test", roles: ["federation", "athlete"], active_role: "federation" };
  await page.route("**/api/v1/auth/me/", (route) => signedOut ? route.fulfill({ status: 403, json: { detail: "Signed out" } }) : route.fulfill({ json: user }));
  await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "test" } }));
  await page.route("**/api/v1/auth/dashboard/", (route) => route.fulfill({ json: { role: "federation", metrics: [], guardian_status: null } }));
  await page.route("**/api/v1/auth/active-role/", async (route) => {
    started?.();
    await pending;
    await route.fulfill({ json: { ...user, active_role: "athlete" } }).catch(() => {});
  });
  await page.route("**/api/v1/auth/logout/", (route) => { signedOut = true; return route.fulfill({ status: 204 }); });
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Спортсмен", exact: true }).click();
  await requested;
  await page.getByRole("button", { name: "Выйти", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("button", { name: "Спортсмен", exact: true })).toHaveCount(0);
  release?.();
  await expect(page.getByRole("button", { name: "Спортсмен", exact: true })).toHaveCount(0);
});

test("logout can cancel a role switch stalled while obtaining CSRF", async ({ page }) => {
  let signedOut = false;
  let csrfCount = 0;
  let rolePosted = false;
  let release: (() => void) | undefined;
  let started: (() => void) | undefined;
  const pending = new Promise<void>((resolve) => { release = resolve; });
  const requested = new Promise<void>((resolve) => { started = resolve; });
  const user = { id: 1, full_name: "Тест", email: "fiction@example.test", roles: ["federation", "athlete"], active_role: "federation" };
  await page.route("**/api/v1/auth/me/", (route) => signedOut ? route.fulfill({ status: 403, json: { detail: "Signed out" } }) : route.fulfill({ json: user }));
  await page.route("**/api/v1/auth/dashboard/", (route) => route.fulfill({ json: { role: "federation", metrics: [], guardian_status: null } }));
  await page.route("**/api/v1/auth/csrf/", async (route) => {
    csrfCount++;
    if (csrfCount === 1) { started?.(); await pending; }
    await route.fulfill({ json: { csrfToken: "test" } }).catch(() => {});
  });
  await page.route("**/api/v1/auth/active-role/", (route) => { rolePosted = true; return route.fulfill({ json: user }); });
  await page.route("**/api/v1/auth/logout/", (route) => { signedOut = true; return route.fulfill({ status: 204 }); });
  await page.goto("/dashboard");
  await page.getByRole("button", { name: "Спортсмен", exact: true }).click();
  await requested;
  await page.getByRole("button", { name: "Выйти", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  release?.();
  expect(rolePosted).toBe(false);
});
