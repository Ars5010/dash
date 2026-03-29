# Frontend (React + Tailwind)

## Экраны (MVP)
- **Хронология** (`/timeline`)\n
  - выбор даты\n
  - поиск + выбор пользователей\n
  - лента дня по каждому пользователю\n
  - **правая KPI‑панель** (активное/неактивное/продуктивное/непродуктивное, % + минуты, KPI%, индикатор цветом, штраф)\n
  - снизу блок **«Показатели за период»** (месяц/год): рабочие/выходные/праздники + хорошие/средние/плохие/отсутствия с цветами\n
- **Сводка** (`/summary`)\n
  - гистограмма по дням (active/away/afk/productive)\n
  - «серые» дни (Праздник/Выходной) подтягиваются из календаря «Отсутствие»\n
- **Отсутствие** (`/absence`)\n
  - календарь + создание события по выделенному диапазону\n
  - **выбор дат + времени** (`datetime-local`)\n
  - типы и цвета:\n
    - Отпуск/Больничный/Отгул — **синий**\n
    - Праздник/Выходной — **серый**\n
    - Прогул — **красный**\n
  - связка: эти типы влияют на периодные показатели и маркировку дней в хронологии/сводке\n
- **Админка** (`/admin`)\n
  - пользователи\n
  - правила продуктивности\n
  - устройства/enrollment\n
  - Telegram‑подписки (чаты)\n

## Главные компоненты/модули
- `src/components/Shell.jsx` — общий layout + навигация\n
- `src/lib/api.js` — axios клиент, подставляет JWT из `localStorage` (`portal_jwt`)\n
- `src/pages/TimelinePage.jsx` — UX хронологии + правая KPI‑панель\n
- `src/pages/AbsencePage.jsx` — календарь отсутствий с datetime\n

## UX хронологии (как устроено)
- Лента дня — горизонтальная шкала 00:00–23:59 (MVP: UTC, позже переключим на таймзону пользователя)\n
- Сегменты:\n
  - Active (зелёный)\n
  - Away/AFK (красный)\n
  - Productive (оранжевый)\n
- Правая панель:\n
  - KPI% и индикатор (green/yellow/red/blue) + подсветка всего блока\n
  - минуты и проценты по 4 метрикам\n
  - опоздал/ранний уход (штраф в %)\n
  - штраф за день (‑1000/‑3000)\n

## Связки «Отсутствие ↔ Хронология/Сводка»
- В хронологии периодные показатели и “серые” дни зависят от событий отсутствия.\n
- В сводке дни Праздник/Выходной показываются отдельным цветом.\n

## Запуск
```bash
cd portal/frontend
npm run dev
```

# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
