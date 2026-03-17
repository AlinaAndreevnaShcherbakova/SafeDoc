# SafeDoc Frontend

Лаконичный UI для SafeDoc на `React + React Bootstrap + Axios`.

## Что есть

- Логин по `/auth/login`
- Список документов с поиском
- Загрузка, скачивание и удаление документов
- Создание публичной ссылки
- Заявки на доступ: мои и входящие
- Раздел пользователей для суперадмина

## Быстрый старт

1. Скопируй переменные окружения:

```bash
# Linux/macOS
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

2. Установи зависимости:

```bash
npm install
```

3. Запусти фронтенд:

```bash
npm run dev
```

Приложение будет доступно на `http://localhost:5173`.

## Переменные окружения

- `VITE_API_BASE_URL` - адрес FastAPI (по умолчанию `http://localhost:8000`).

## Запуск в Docker

Из корня проекта `SafeDoc`:

```bash
# Production-like запуск (frontend + api + базы)
docker compose up --build
```

```bash
# Debug запуск с hot-reload для backend и frontend
docker compose -f docker-compose.yml -f docker-compose.debug.yml up --build
```

Frontend будет доступен на `http://localhost:5173` (или на порту из `FRONTEND_PORT`).


