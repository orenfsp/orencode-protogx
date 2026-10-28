import { expect, test } from "@playwright/test";
import { signIn } from "./helpers";

test.describe("optional case live workflows", () => {
  test.skip(process.env.FSP_OPTIONAL_LIVE !== "1", "Requires seed_optional and the fictional OIDC client; see docs/optional-demo.md");
  test.describe.configure({ mode: "serial" });

  test("D11 public navigation and responsive design", async ({ page }, info) => {
    await page.goto("/newcomer");
    await expect(page.getByRole("heading", { name: "Начать заниматься" })).toBeVisible();
    await expect(page.getByText("Демо: вымышленная школа ОренКод", { exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Регистрация", exact: true }).last()).toBeVisible();
    for (const width of [1440, 768, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      for (const theme of ["light", "dark"]) {
        await page.evaluate(value => { localStorage.setItem("fsp-theme", value); }, theme);
        await page.reload();
        await expect(page.getByRole("heading", { name: "Начать заниматься" })).toBeVisible();
        await expect(page.getByText("Демо: вымышленная школа ОренКод", { exact: true })).toBeVisible();
        await page.screenshot({ path: info.outputPath(`newcomer-${width}-${theme}.png`), fullPage: true });
      }
    }
  });

  test("D10 athlete certificate, D5 private evidence and D7 progression", async ({ page, browser }) => {
    await signIn(page, "demo.athlete@example.test");
    await page.goto("/certificates");
    const participation = page.getByLabel("Участие", { exact: true });
    await expect(participation.locator("option").nth(1)).toBeAttached();
    await participation.selectOption(await participation.locator("option").nth(1).getAttribute("value") as string);
    const issuedResponse = page.waitForResponse(r => r.url().endsWith("/api/v1/certificates/") && r.request().method() === "POST");
    await page.getByRole("button", { name: "Сформировать справку", exact: true }).click();
    const issued = await (await issuedResponse).json();
    await expect(page.getByRole("link", { name: "Скачать", exact: true }).first()).toBeVisible();
    const [download] = await Promise.all([page.waitForEvent("download"), page.getByRole("link", { name: "Скачать", exact: true }).first().click()]);
    expect(download.suggestedFilename()).toMatch(/certificate-.*\.pdf/);
    const publicContext = await browser.newContext();
    const verification = await publicContext.newPage();
    await verification.goto(new URL(issued.verify_url, page.url()).toString());
    await expect(verification.getByText("Действительна", { exact: true })).toBeVisible();
    await expect(verification.getByText("Демо Спортсмен", { exact: true })).toHaveCount(0);
    await publicContext.close();

    await page.goto("/reviews");
    const submit = page.locator("form").filter({ has: page.getByRole("button", { name: "Подать обращение", exact: true }) });
    await submit.getByLabel("Вид", { exact: true }).selectOption("appeal");
    const application = submit.getByLabel("Участник и событие", { exact: true });
    await expect(application.locator("option").nth(1)).toBeAttached();
    await application.selectOption(await application.locator("option").nth(1).getAttribute("value") as string);
    await submit.getByLabel("Обоснование", { exact: true }).fill("Демо: проверить тестовый результат, без реальных персональных данных");
    const caseResponse = page.waitForResponse(r => r.url().endsWith("/api/v1/reviews/") && r.request().method() === "POST");
    await submit.getByRole("button", { name: "Подать обращение", exact: true }).click();
    const review = await (await caseResponse).json();
    const evidence = page.locator("form").filter({ has: page.getByRole("button", { name: "Приложить доказательство", exact: true }) });
    await expect(evidence.getByLabel("Дело", { exact: true }).locator(`option[value='${review.id}']`)).toBeAttached();
    await evidence.getByLabel("Дело", { exact: true }).selectOption(String(review.id));
    await evidence.getByLabel("Описание", { exact: true }).fill("Вымышленный журнал платформы");
    await evidence.getByLabel("PNG, JPEG или текстовый лог до 5 МиБ", { exact: true }).setInputFiles({ name: "fictional-log.txt", mimeType: "text/plain", buffer: Buffer.from("fictional result evidence") });
    const uploaded = page.waitForResponse(r => /\/reviews\/\d+\/evidence\/$/.test(r.url()) && r.request().method() === "POST");
    await evidence.getByRole("button", { name: "Приложить доказательство", exact: true }).click();
    expect((await uploaded).status()).toBe(201);
    await expect(page.getByRole("link", { name: "Скачать доказательство" }).first()).toBeVisible();
    await page.goto("/progression");
    await expect(page.getByRole("heading", { name: "Личный путь спортсмена" })).toBeVisible();
    await expect(page.getByText("III спортивный разряд", { exact: true })).toBeVisible();
  });

  test("D3 D4 D6 D8 D2 federation workspaces use live data", async ({ page }) => {
    await signIn(page, "demo.federation@example.test");
    await page.getByRole("button", { name: "Федерация", exact: true }).click();
    for (const [route, title] of [["training", "Подготовка и журнал занятий"], ["assessment", "Нормативы и аттестация"], ["development", "Развитие вида спорта"], ["integrations", "Внешние интеграции"], ["awards", "Премии Губернатора"]]) {
      await page.goto(`/${route}`);
      await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
      await expect(page.getByRole("button", { name: /Сохранение/ })).toHaveCount(0);
      await expect(page.getByText("Загрузка…", { exact: true })).toHaveCount(0);
      await expect(page.locator("main [role=alert]")).toHaveCount(0);
    }
    const prepare = page.locator("form").filter({ has: page.getByRole("button", { name: "Проверить список и подготовить пакет", exact: true }) });
    const scheme = prepare.getByLabel("Версия справочника", { exact: true });
    await expect(scheme.locator("option").nth(1)).toBeAttached();
    await scheme.selectOption(await scheme.locator("option").nth(1).getAttribute("value") as string);
    const prepared = page.waitForResponse(r => r.url().endsWith("/awards/prepare/") && r.request().method() === "POST");
    await prepare.getByRole("button").click();
    expect((await prepared).status()).toBe(201);
    await expect(page.getByRole("link", { name: "Скачать", exact: true }).first()).toBeVisible();
  });

  test("D12 judge generates his own panel document", async ({ page }) => {
    await signIn(page, "demo.judge@example.test");
    await page.goto("/judging-documents");
    await page.getByLabel("Форма", { exact: true }).selectOption("panel");
    const event = page.getByLabel("Соревнование для справки", { exact: true });
    await expect(event.locator("option").nth(1)).toBeAttached();
    await event.selectOption(await event.locator("option").nth(1).getAttribute("value") as string);
    const generated = page.waitForResponse(r => r.url().endsWith("/judging-documents/") && r.request().method() === "POST");
    await page.getByRole("button", { name: "Сформировать документ", exact: true }).click();
    expect((await generated).status()).toBe(201);
    await expect(page.getByRole("link", { name: "Скачать", exact: true }).first()).toBeVisible();
  });

  test("D9 ministry reads without mutation rights", async ({ page }) => {
    await signIn(page, "demo.ministry@example.test");
    await page.goto("/ministry");
    await expect(page.getByText(/Доступ только для чтения/)).toBeVisible();
    await expect(page.locator("main [role=alert]")).toHaveCount(0);
    await expect(page.locator("main form")).toHaveCount(1); // Read-only year filter.
    expect((await page.request.post("/api/v1/ministry/", { data: {} })).status()).toBeGreaterThanOrEqual(400);
  });

  test("D1 real browser redirect login consent callback userinfo logout", async ({ page }, info) => {
    await page.goto("http://127.0.0.1:9012/");
    await page.getByRole("link", { name: "Войти через ФСП ID", exact: true }).click();
    await expect(page).toHaveURL(/127\.0\.0\.1:8000\/o\/login\//);
    await page.locator("input[name=username]").fill("demo.athlete@example.test");
    await page.locator("input[name=password]").fill("DemoOnly2026!");
    await page.getByRole("button", { name: "Войти", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Передача данных через ФСП ID" })).toBeVisible();
    await page.screenshot({ path: info.outputPath("oidc-consent.png"), fullPage: true });
    await page.getByRole("button", { name: "Разрешить передачу данных", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Вход выполнен через ФСП ID" })).toBeVisible();
    await expect(page.locator("pre")).toContainText("Демо Спортсмен");
    await page.screenshot({ path: info.outputPath("oidc-userinfo.png"), fullPage: true });
    await page.getByRole("button", { name: "Выйти из тестового клиента", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Вы вышли из тестового клиента" })).toBeVisible();
  });
});
