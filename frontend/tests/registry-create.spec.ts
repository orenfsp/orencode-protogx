import { expect, test } from "@playwright/test";

for (const [role, button] of [["athlete", "Спортсмены"], ["coach", "Тренеры"], ["judge", "Судьи"]] as const) {
  test(`federation creates the ${role} profile for an existing user`, async ({ page }) => {
    const user = { id: 1, full_name: "Тест федерации", email: "fiction@example.test", roles: ["federation"], active_role: "federation" };
    let submitted: unknown;
    await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
    await page.route("**/api/v1/auth/csrf/", (route) => route.fulfill({ json: { csrfToken: "fixture" } }));
    await page.route("**/api/v1/registry/options/", (route) => route.fulfill({ json: { organizations: [{ id: 7, name: "Демо организация" }], disciplines: [], age_groups: [], municipalities: [] } }));
    await page.route("**/api/v1/registry/eligible-users/**", (route) => {
      const requestedRole = new URL(route.request().url()).searchParams.get("role");
      return route.fulfill({ json: { results: requestedRole === role ? [{ id: 42, full_name: "Демо кандидат" }] : [], next: null } });
    });
    await page.route(`**/api/v1/registry/profiles/${role}/`, (route) => {
      submitted = route.request().postDataJSON();
      return route.fulfill({ status: 201, json: { id: 42 } });
    });
    for (const list of ["athletes", "coaches", "judges"]) {
      await page.route(`**/api/v1/${list}/?**`, (route) => route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } }));
    }
    await page.goto("/registry");
    if (role !== "athlete") await page.getByRole("button", { name: button, exact: true }).click();
    await expect(page.getByRole("option", { name: "Демо кандидат" })).toHaveCount(1);
    await page.getByLabel("Существующий пользователь").selectOption("42");
    await page.getByLabel("Организация профиля").selectOption("7");
    await page.getByRole("button", { name: "Создать профиль", exact: true }).click();
    await expect.poll(() => submitted).toEqual({ user: 42, organization: 7 });
    await expect(page.getByLabel("Существующий пользователь")).toHaveValue("");
  });
}

test("organization filters send named selections to the API", async ({ page }) => {
  const user = { id: 1, full_name: "Федерация", email: "fiction@example.test", roles: ["federation"], active_role: "federation" };
  let lastQuery = "";
  await page.route("**/api/v1/auth/me/", (route) => route.fulfill({ json: user }));
  await page.route("**/api/v1/registry/options/", (route) => route.fulfill({ json: { organizations: [], disciplines: [], age_groups: [], municipalities: ["Оренбург"] } }));
  await page.route("**/api/v1/registry/eligible-users/**", (route) => route.fulfill({ json: { results: [], next: null } }));
  await page.route("**/api/v1/athletes/**", (route) => route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } }));
  await page.route("**/api/v1/organizations/**", (route) => {
    lastQuery = new URL(route.request().url()).search;
    return route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } });
  });
  await page.goto("/registry");
  await page.getByRole("button", { name: "Организации", exact: true }).click();
  await page.getByLabel("Статус организации").selectOption("false");
  await page.getByLabel("Муниципалитет в фильтре").selectOption("Оренбург");
  await page.getByLabel("Тип организации").fill("Клуб");
  await expect.poll(() => {
    const query = new URLSearchParams(lastQuery);
    return [query.get("active"), query.get("municipality"), query.get("organization_type")];
  }).toEqual(["false", "Оренбург", "Клуб"]);
});
