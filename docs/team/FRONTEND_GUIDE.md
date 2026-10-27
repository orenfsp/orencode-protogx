# Разработка frontend

`frontend/` — Next.js 16.4.3 App Router, React 19.2, TypeScript. Сначала прочтите `frontend/AGENTS.md`: в нём требуется сверять API Next.js с установленной документацией `node_modules/next/dist/docs/` перед изменением кода. Визуальный контракт — [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md).

## Маршруты и состав

| Route | Файл | Реальное поведение |
| --- | --- | --- |
| `/` | `src/app/page.tsx` | открытый каталог дисциплин и вход |
| `/login`, `/register`, `/privacy` | соответствующие `page.tsx` | session login, регистрация с согласием, информация о demo-обработке |
| `/dashboard` | `src/app/dashboard/page.tsx` | четыре варианта одной сводки по `auth/dashboard/` и активной роли |
| `/competitions` | `src/app/competitions/page.tsx` | публичный календарь; federation создаёт соревнование и версию шаблона |
| `/competitions/[id]` | `src/app/competitions/[id]/page.tsx` | детализация, роли, заявки, moderation, судьи, результаты, preview/publication/export |
| `/coach-links` | `src/app/coach-links/page.tsx` | запрос и подтверждение связи по дисциплине |
| `/history` | `src/app/history/page.tsx` | собственная история спортсмена |
| `/my-competitions` | `src/app/my-competitions/page.tsx` | заявки спортсмена/тренера или назначения судьи из существующих API; доступ из кабинета |

`src/app/layout.tsx` загружает шрифты, `globals.css` и `app.css`, оборачивает все страницы в `src/components/AppShell.tsx`. Отдельных role-specific layout-файлов нет. `AppShell` строит нумерованную боковую навигацию, мобильную нижнюю панель, выбор активной роли, logout и переключение темы; `useCurrentUser()` читает контекст оболочки. Защитой данных служит API, а не этот контекст. После изменения роли `dashboard/page.tsx` заново запрашивает метрики.

`src/components/CompetitionEditor.tsx` — форма draft/edit и этапов; `TemplateEditor.tsx` — конфигурация версии шаблона; `ResultEditor.tsx` — статус, балл/место и метрики шаблона. `src/lib/api.ts` содержит **все общие DTO**, функцию `api<T>()` и CSRF-обмен. В приложении нет отдельного каталога hooks или глобального data-fetching фреймворка: страницы/формы используют `useState`, `useEffect` и локальные `load`/`refresh` функции. Не придумывайте несуществующий shared hook при выдаче задания.

## Запросы, ошибки и формы

`api<T>("competitions/")` обращается к `/api/v1/competitions/` через same-origin rewrite. Перед POST/PATCH функция получает `/api/v1/auth/csrf/`, отправляет `X-CSRFToken`, включает cookies и кидает `Error` из `detail` либо JSON ошибки. Для бинарного download страница `[id]/page.tsx` отдельно использует `fetch` с `credentials: "include"`; не заставляйте JSON helper разбирать PDF. Поля форм имеют native HTML-ограничения, но источник истины — Django сериализаторы и сервисы. Ошибки показываются через `.note.wn`/`role="alert"`; состояния загрузки и отсутствия данных оформлены на конкретных страницах, общего `loading.tsx` нет.

Тема: checkbox `#th` управляет CSS `:root:has(#th:checked)`; `AppShell` сохраняет значение `fsp-theme` в `localStorage`. На ширине ≤900 px sidebar скрывается, показываются `mobile-tools` и `.mobtab`; таблицы Phase 2 горизонтально прокручиваются. В `app.css` лежат дополнительные функциональные стили форм и workflow; точные базовые токены в `globals.css`, извлечённые из неизменяемого HTML.

## Куда добавлять код

- Страница по выданному маршруту: `src/app/<route>/page.tsx`. Сначала проверьте существующие route и `AppShell`.
- Локальный UI-компонент: рядом со страницей или в `src/components/` только если повторно используется и его интерфейс утверждён. Пример существующего выноса — `ResultEditor`.
- Сетевой вызов: через `api<T>()` из `src/lib/api.ts`; изменение общего DTO разрешает только руководитель после API-ревью. Если нужен бинарный ответ, следуйте текущему download-коду.
- Стили: пользуйтесь существующими `.blk`, `.btn`, `.bd`, `.tw`, `.note`, `.workflow-form`; изменение `globals.css`, `app.css`, `AppShell` требует согласования.
- Проверка сценария: `frontend/tests/phase1.spec.ts` или `phase2.spec.ts` по владельцу; скриншоты — `frontend/scripts/capture-*.mjs` и [visual-qa.md](../design/visual-qa.md).

Перед изменением дизайна откройте [reference HTML](../design/fsp-reference.html), затем сравните страницу при 1440/768/390 px в обеих темах. Не копируйте статические данные HTML как рабочие данные продукта.
