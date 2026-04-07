# Gmail AI Assistant

Полноценный локальный AI‑агент для Gmail: классификация писем, чистка мусора, отписка, уведомления и логирование. Работает по расписанию, есть API‑панель статуса, безопасный режим и DRY RUN.

## Возможности
- Анализ входящих писем
- Классификация: `important` / `useful` / `junk` / `manual_review`
- Авто‑чистка мусора (архив/удаление/спам)
- Авто‑отписка (List‑Unsubscribe)
- Маркировка важных писем
- Уведомления (Telegram/email/webhook)
- Расписание (APScheduler)
- Логи и история действий (SQLite)
- Безопасный режим

## Быстрый старт (локально)
1. Создайте проект в Google Cloud Console и включите Gmail API.
2. Создайте OAuth Client (Desktop App), скачайте `credentials.json` в корень проекта.
3. Скопируйте `.env.example` в `.env` и заполните значения.
4. При первом запуске сервис попросит создать пользователя API и добавить Gmail‑аккаунты (данные сохраняются в `configs/users.json` и `configs/accounts.json`).
4. Установите зависимости:

```bash
pip install -r requirements.txt
```

5. Запуск API:

```bash
uvicorn src.api:app --host 0.0.0.0 --port 8000
```

6. Запуск планировщика:

```bash
python -m src.main
```

При первом запуске откроется окно авторизации Gmail OAuth (локальный redirect). Будет создан `token.json`.

## Запуск через Docker
```bash
docker compose up --build
```
Сервис `api` — FastAPI, сервис `worker` — планировщик.

## Настройки (.env)
Ключевые параметры:
- `CLEANUP_MODE` = `archive|delete|spam`
- `DRY_RUN=true` — ничего не удаляет, только логирует
- `SAFE_MODE=true` — отписка только логируется
- `JUNK_CONFIDENCE_THRESHOLD` / `IMPORTANT_CONFIDENCE_THRESHOLD`
- `ALLOWED_SENDERS`, `BLOCKED_SENDERS`, `PROTECTED_DOMAINS` (CSV)
- `BASIC_AUTH_USER` / `BASIC_AUTH_PASS` — базовая авторизация для API
- `UNSUBSCRIBE_ALLOWLIST` — домены, на которые разрешена отписка
- `BLOCK_PRIVATE_IPS=true` — блокирует приватные и link‑local IP для unsubscribe URL

## Безопасность
Авто‑удаление применяется только к письмам с высокой уверенностью и без стоп‑слов. Важные категории никогда не удаляются автоматически.
API защищено Basic Auth (пользователи хранятся в `configs/users.json`), внешние URLs для отписки проверяются на безопасность, LLM получает редактированные данные.

## API
- `GET /health`
- `POST /run-scan`
- `GET /emails/recent`
- `GET /actions/logs`
- `GET /stats`
- `GET /rules`
- `POST /rules/update`
- `GET /manual-review`
- `POST /manual-review/{id}/keep`
- `POST /manual-review/{id}/junk`

## Тесты
```bash
pytest
```

## Примеры писем
См. `docs/sample_emails.md`.
