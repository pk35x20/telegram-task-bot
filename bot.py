
import os
import asyncio
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

async def send_long_message(chat_id: int, text: str):
    max_length = 4096
    for i in range(0, len(text), max_length):
        await bot.send_message(chat_id, text[i:i + max_length], parse_mode=ParseMode.HTML)

def parse_task_status(text):
    if "👍" in text:
        return "👍"
    elif "🤝" in text:
        return "🤝"
    else:
        return "❓"

@dp.message(Command("собери"))
async def handle_soberi(message: Message):
    args = message.text.strip().split()
    days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    cutoff_date = datetime.now() - timedelta(days=days)

    collected = {"👍": [], "🤝": [], "❓": []}
    offset_id = 0
    limit = 100
    total_loaded = 0

    for _ in range(10):  # до 1000 сообщений
        messages = await bot.get_chat_history(message.chat.id, limit=limit, offset_id=offset_id)
        if not messages:
            break

        for msg in messages:
            if msg.date < cutoff_date:
                continue
            if msg.text and "#задача" in msg.text.lower():
                status = parse_task_status(msg.text)
                collected[status].append(msg.text)

        offset_id = messages[-1].message_id
        total_loaded += len(messages)

    if not any(collected.values()):
        await message.answer("Не найдено задач за указанный период.")
        return

    report = f"📦 Задачи за {days} дн. (просканировано {total_loaded} сообщений):\n"
    for status, tasks in collected.items():
        report += f"\n{status} {status_name(status)}:\n"
        for task in tasks:
            report += f"— {task}\n"

    await send_long_message(message.chat.id, report)

def status_name(emoji):
    return {
        "👍": "Выполнено",
        "🤝": "В работе",
        "❓": "Без статуса"
    }.get(emoji, "Неизвестно")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
