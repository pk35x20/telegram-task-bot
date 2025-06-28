import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from aiogram.utils.markdown import hbold
from aiogram import F
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from datetime import datetime, timedelta
import asyncio

# Загрузка токена
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# Хранилище задач
tasks = []

@dp.message(F.text.lower().contains("#задача"))
async def collect_task(message: Message):
    tasks.append((datetime.now(), message.from_user.first_name, message.text))

@dp.message(Command("собери"))
async def send_tasks(message: Message, command: CommandObject):
    try:
        days = int(command.args.strip()) if command.args else None
    except (ValueError, AttributeError):
        await message.answer("❗ Укажи число — например: /собери 2")
        return

    now = datetime.now()
    filtered = [
        f"{author}: {text}"
        for created_at, author, text in tasks
        if days is None or (now - created_at <= timedelta(days=days))
    ]

    if not filtered:
        await message.answer("📭 Нет задач за указанный период.")
    else:
        response = "📋 Список задач:\n" + "\n".join(filtered)
        await message.answer(response)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())