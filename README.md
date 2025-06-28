
# Telegram Task Bot

Бот для сбора задач из чата Telegram по хештегу `#задача`.

## 🚀 Как запустить

1. Распакуй архив и перейди в папку проекта:

```bash
cd telegram-task-bot
```

2. Установи зависимости:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Убедись, что в файле `.env` прописан токен

4. Запусти бота:

```bash
python bot.py
```

## 📌 Команды

- Пиши сообщения в чат с `#задача`
- Введи `/собери` или `/собери N`, чтобы получить задачи за последние N суток
