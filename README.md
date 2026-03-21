# SafeDoc Backend (MVP)

MVP backend для дипломного проекта: защищенное хранение документов с RBAC/ACL, версиями файлов, заявками на доступ, публичными ссылками, SMTP-уведомлениями и аудитом.

## Что реализовано

- FastAPI + SQLAlchemy (асинхронно) для реляционных данных.
- Поддержка MongoDB GridFS для хранения файлов (с fallback на локальную папку `storage/`).
- JWT-аутентификация и блокировка входа на 10 минут после 3 неудачных попыток.
- Роли: `superadmin`, `access_manager`, `owner`, `editor`, `reader`, `guest`.
- CRUD пользователей (только `superadmin`, защита от удаления последнего супер-админа).
- Операции с файлами: загрузка, скачивание, список, новая версия, история версий.
- Заявки на доступ и обработка заявок.
- Публичные ссылки с TTL.
- Аудит-лог в формате JSONL с ротацией 100 МБ и попыткой выгрузки закрытого лога в Mongo GridFS (`logs` bucket).

## Быстрый локальный старт (без Docker)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Swagger: `http://127.0.0.1:8000/docs`

## Docker Compose

### 1) Production run

Файлы: `docker-compose.yml`, `Dockerfile`, `.env.prod`.

```bash
docker compose --env-file .env.prod up -d --build
```

Остановить:

```bash
docker compose --env-file .env.prod down
```

### 2) Debug run (3rd-party stack)

Файлы: `docker-compose.yml` + `docker-compose.debug.yml`, `.env.debug`.

В debug поднимаются:
- `mailpit` (SMTP sandbox + web UI)
- открытые порты `postgres` и `mongo`
- hot reload для API
- опционально GUI по профилю `debug-tools`: `pgadmin`, `mongo-express`

```bash
docker compose -f docker-compose.yml -f docker-compose.debug.yml --env-file .env.debug up --build
```

Debug + GUI tools:

```bash
docker compose -f docker-compose.yml -f docker-compose.debug.yml --env-file .env.debug --profile debug-tools up --build
```

Остановить debug:

```bash
docker compose -f docker-compose.yml -f docker-compose.debug.yml --env-file .env.debug down
```

### Debug URLs

- API docs: `http://127.0.0.1:8000/docs`
- Mailpit UI: `http://127.0.0.1:8025`
- PgAdmin (profile `debug-tools`): `http://127.0.0.1:5050`
- Mongo Express (profile `debug-tools`): `http://127.0.0.1:8081`

## Минимальные API для демо

- `POST /auth/login`, `GET /auth/me`, `PATCH /auth/me`, `POST /auth/change-password`
- `POST /users`, `GET /users`, `PATCH /users/{user_id}`, `DELETE /users/{user_id}`
- `POST /documents` (multipart), `GET /documents`, `GET /documents/{id}/preview`, `GET /documents/{id}/download`
- `POST /documents/{id}/versions`, `GET /documents/{id}/versions`
- `PATCH /documents/{id}/rename`, `DELETE /documents/{id}`
- `POST /documents/{id}/restore/{version}`
- `POST /access/requests`, `GET /access/requests/my`, `GET /access/requests/inbox`
- `POST /access/requests/{id}/resolve`, `POST /access/grant`, `POST /access/revoke`
- `POST /links/{document_id}`, `GET /links/{document_id}`, `GET /links/public/{token}`, `POST /links/public/{token}/revoke`, `POST /links/{link_id}/revoke`
- `GET /audit/tail` (только superadmin)

## Переменные окружения

Смотри шаблоны: `.env.prod.example`, `.env.debug.example`.

Ключевые:
- `SECRET_KEY`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `MONGO_DB`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
- `DEFAULT_SUPERADMIN_LOGIN`, `DEFAULT_SUPERADMIN_PASSWORD`

## Тест

```bash
pytest -q
```

## Ограничения MVP

- Полная матрица полномочий реализована в базовом виде; детализацию по отделам можно расширить.
- Криптографические преобразования предполагаются внешним компонентом (в MVP не включены).
- Предпросмотр файлов реализован через inline-ответ API; отдельный viewer-сервис в MVP не используется.
