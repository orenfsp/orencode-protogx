import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

for (const width of [1440, 768, 390]) for (const theme of ["light", "dark"]) {
  test(`registry editing and focus at ${width}px in ${theme} theme`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript((value) => localStorage.setItem("fsp-theme", value), theme);
    const user = { id: 1, full_name: "Демо Федерация", email: "fiction@example.test", roles: ["federation"], active_role: "federation" };
    await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
    await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "fixture" } }));
    await page.route("**/api/v1/registry/options/", (route) => route.fulfill({ json: { organizations: [{ id: 1, name: "Демо организация" }], disciplines: [{ id: 1, name: "Алгоритмическое программирование" }], age_groups: [], municipalities: ["Оренбург"] } }));
    await page.route("**/api/v1/registry/eligible-users/**", (route) => route.fulfill({ json: { results: [{ id: 8, full_name: "Демо кандидат" }], next: null } }));
    await page.route("**/api/v1/registry/profiles/**", (route) => route.fulfill({ json: { ranks: [], categories: [], coach_links: [], assignments: [] } }));
    await page.route("**/api/v1/athletes/**/audit/", (route) => route.fulfill({ json: [] }));
    await page.route("**/api/v1/athletes/**/history/**", (route) => route.fulfill({ json: [{ id: 1, starts_on: "2024-01-01", ends_on: null }] }));
    await page.route("**/api/v1/athletes/**/correct/", (route) => route.fulfill({ status: 400, json: { detail: "Укажите причину исправления" } }));
    await page.route("**/api/v1/athletes/?**", (route) => route.fulfill({ json: { count: 1, next: null, previous: null, results: [{ id: 8, full_name: "Демо спортсмен", date_of_birth: "2000-01-01", organization: null, is_active: true }] } }));
    await page.goto("/registry");
    await page.getByRole("button", { name: "Демо спортсмен", exact: true }).click();
    await page.getByRole("button", { name: "Исправить", exact: true }).first().click();
    await expect(page.getByLabel("Причина исправления")).toBeVisible();
    await expect(page.getByLabel("Причина исправления")).toBeFocused();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy();
    if (width <= 900) await expect(page.getByRole("navigation", { name: "Основная навигация" })).toBeVisible();
    expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze()).violations).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath(`registry-form-${width}-${theme}.png`), fullPage: true });
    await page.keyboard.press("Tab");
    await expect(page.getByRole("button", { name: "Сохранить исправление" })).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("p[role=alert]")).toContainText("Укажите причину исправления");
    expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze()).violations).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath(`registry-validation-${width}-${theme}.png`), fullPage: true });
    await expect(page.getByLabel("Причина исправления")).toHaveAttribute("aria-describedby", "correction-error");
    await page.keyboard.press("Shift+Tab");
    await expect(page.getByLabel("Причина исправления")).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(page.getByLabel("Причина исправления")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Исправить", exact: true }).first()).toBeFocused();
  });
}

for (const width of [1440, 768, 390]) for (const theme of ["light", "dark"]) {
  test(`specialist and organization details at ${width}px in ${theme} theme`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript((value) => localStorage.setItem("fsp-theme", value), theme);
    const user = { id: 1, full_name: "Демо Федерация", email: "fiction@example.test", roles: ["federation"], active_role: "federation" };
    await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
    await page.route("**/api/v1/registry/options/", (route) => route.fulfill({ json: { organizations: [{ id: 1, name: "Демо организация" }], disciplines: [{ id: 1, name: "Программирование" }], age_groups: [], municipalities: ["Оренбург"] } }));
    await page.route("**/api/v1/registry/eligible-users/**", (route) => route.fulfill({ json: { results: [], next: null } }));
    await page.route("**/api/v1/registry/profiles/**/context/", (route) => {
      const judge = route.request().url().includes("/judge/");
      return route.fulfill({ json: {
        ranks: [],
        categories: judge ? [{ category: "Демо категория", assigned_on: "2024-01-01", valid_until: "2027-01-01", validity: "active", current: true }] : [],
        coach_links: judge ? [] : [{ coach: "Демо тренер", athlete: "Демо спортсмен", discipline: "Программирование", status: "confirmed" }],
        assignments: [],
      } });
    });
    await page.route("**/api/v1/registry/profiles/**/staff/", (route) => route.fulfill({ json: { organization: 1, disciplines: [1] } }));
    for (const [kind, name] of [["athletes", "Демо спортсмен"], ["coaches", "Демо тренер"], ["judges", "Демо судья"]] as const) {
      await page.route(`**/api/v1/${kind}/?**`, (route) => route.fulfill({ json: { count: 1, next: null, previous: null, results: [{ id: 8, full_name: name, date_of_birth: "2000-01-01", organization: "Демо организация", is_active: true }] } }));
    }
    await page.route("**/api/v1/organizations/?**", (route) => route.fulfill({ json: { count: 1, next: null, previous: null, results: [{ id: 1, code: "demo", name: "Демо организация", municipality: "Оренбург", organization_type: "Клуб", contact: "", is_active: true }] } }));
    await page.goto("/registry");
    for (const [kind, label, name] of [["coaches", "Тренеры", "Демо тренер"], ["judges", "Судьи", "Демо судья"], ["organizations", "Организации", "Демо организация"]] as const) {
      await page.getByRole("button", { name: label, exact: true }).click();
      await page.getByRole("button", { name, exact: true }).click();
      if (kind === "organizations") await expect(page.locator("section").filter({ hasText: "Организация · demo" }).getByLabel("Название", { exact: true })).toHaveValue(name);
      else {
        await expect(page.getByRole("heading", { name: "Профиль специалиста", exact: true })).toBeVisible();
        await expect(page.getByText(kind === "judges" ? "Демо категория" : "Подтверждена", { exact: false })).toBeVisible();
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBeTruthy();
      if (width <= 900) await expect(page.getByRole("navigation", { name: "Основная навигация" })).toBeVisible();
      expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze()).violations).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath(`registry-${kind}-${width}-${theme}.png`), fullPage: true });
    }
  });
}

for (const width of [1440, 768, 390]) for (const theme of ["light", "dark"]) {
  test(`registry loading, empty, error and denied states at ${width}px in ${theme} theme`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await page.addInitScript((value) => localStorage.setItem("fsp-theme", value), theme);
    const user = { id: 1, full_name: "Демо Федерация", email: "fiction@example.test", roles: ["federation"], active_role: "federation" };
    let release: () => void = () => {};
    let started: () => void = () => {};
    const wait = new Promise<void>((resolve) => { release = resolve; });
    const requestStarted = new Promise<void>((resolve) => { started = resolve; });
    await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
    await page.route("**/api/v1/registry/options/", (route) => route.fulfill({ json: { organizations: [], disciplines: [], age_groups: [], municipalities: [] } }));
    await page.route("**/api/v1/registry/eligible-users/**", (route) => route.fulfill({ json: { results: [], next: null } }));
    await page.route("**/api/v1/athletes/?**", async (route) => {
      const search = new URL(route.request().url()).searchParams.get("search");
      if (search === "error") return route.fulfill({ status: 500, json: { detail: "Демо ошибка" } });
      if (search === "denied") return route.fulfill({ status: 403, json: { detail: "denied" } });
      started(); await wait;
      return route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } }).catch(() => {});
    });
    await page.goto("/registry");
    await requestStarted;
    await expect(page.getByText("Загрузка…").first()).toBeVisible();
    expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze()).violations).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath(`registry-loading-${width}-${theme}.png`), fullPage: true });
    release();
    await expect(page.getByText("Записей не найдено.")).toBeVisible();
    expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze()).violations).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath(`registry-empty-${width}-${theme}.png`), fullPage: true });
    await page.getByLabel("Поиск", { exact: true }).fill("error");
    await expect(page.locator("p[role=alert]")).toContainText("Демо ошибка");
    expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze()).violations).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath(`registry-error-${width}-${theme}.png`), fullPage: true });
    await page.getByLabel("Поиск", { exact: true }).fill("denied");
    await expect(page.locator("p[role=alert]")).toContainText("Доступ");
    expect((await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze()).violations).toEqual([]);
    await page.screenshot({ path: testInfo.outputPath(`registry-denied-${width}-${theme}.png`), fullPage: true });
  });
}
