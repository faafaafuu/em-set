# Gmail AI Assistant (CLI)

Минималистичный CLI‑агент для Gmail: авторизация при запуске, команды через диалог, без API и лишних конфиг‑файлов.

## Что умеет
- Классификация: `important` / `useful` / `junk` / `manual_review`
- Авто‑чистка мусора (архив/удаление/спам)
- Авто‑отписка (List‑Unsubscribe)
- Маркировка важных писем
- Логи и история (SQLite)
- Несколько Gmail‑аккаунтов

## Быстрый старт
1. Создайте проект в Google Cloud Console и включите Gmail API.
2. Создайте OAuth Client (Desktop App), скачайте `credentials.json`.
3. Установите зависимости:

```bash
pip install -r requirements.txt
```

4. Запуск:

```bash
python -m src.main
```

При первом запуске приложение попросит создать пользователя и добавить Gmail‑аккаунт(ы). Данные сохраняются в `data/email_assistant.db`.

## Команды CLI
```
help
accounts
add-account
scan [account|all]
manual list
manual keep <account> <email_id>
manual junk <account> <email_id>
stats
exit
```

## Безопасность
- DRY RUN включен по умолчанию в `src/config.py`
- Авто‑удаление только для junk с высокой уверенностью
- LLM получает редактированные данные
- Unsubscribe URL проходит проверку безопасности

## Тесты
```bash
python -m pytest
```
