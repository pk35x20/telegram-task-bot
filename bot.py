
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Хранилище задач по чатам
tasks_by_chat = {}

def task_buttons(message_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍 Выполнено", callback_data=f"done:{message_id}"),
            InlineKeyboardButton(text="🤝 В работе", callback_data=f"in_progress:{message_id}")
        ]
    ])

@dp.message(F.text.lower().contains("#задача"))
async def collect_task(message: Message):
    chat_id = message.chat.id
    text = message.text
    to_user = None
    for word in text.split():
        if word.startswith("@"):
            to_user = word
            break

    reply_text = "Задача зарегистрирована.\nСтатус: 📥 Ожидает\n(установите статус кнопкой ниже)"
    reply_msg = await message.reply(reply_text, reply_markup=task_buttons(message.message_id))

    if chat_id not in tasks_by_chat:
        tasks_by_chat[chat_id] = {}

    tasks_by_chat[chat_id][message.message_id] = {
        "text": text,
        "author": message.from_user.mention_html(),
        "to": to_user,
        "timestamp": datetime.now(),
        "status": "📥",
        "reply_msg_id": reply_msg.message_id,
        "chat_id": chat_id
    }

@dp.callback_query(F.data.startswith("done:") | F.data.startswith("in_progress:"))
async def handle_status_change(callback: CallbackQuery):
    data = callback.data
    status_key, message_id_str = data.split(":")
    message_id = int(message_id_str)
    chat_id = callback.message.chat.id

    chat_tasks = tasks_by_chat.get(chat_id, {})
    if message_id in chat_tasks:
        emoji = "👍" if status_key == "done" else "🤝"
        chat_tasks[message_id]["status"] = emoji
        user = callback.from_user.mention_html()
        reply_id = chat_tasks[message_id]["reply_msg_id"]

        new_text = f"Задача зарегистрирована.\nСтатус: {emoji} (обновил {user})"
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=reply_id,
                text=new_text,
                reply_markup=task_buttons(message_id)
            )
        except Exception as e:
            logging.warning(f"Ошибка при редактировании: {e}")

        await callback.answer(f"Статус: {'Выполнено' if emoji == '👍' else 'В работе'}")
    else:
        await callback.answer("Задача не найдена.", show_alert=True)

@dp.message(F.text.lower().startswith("собери"))
async def collect_report(message: Message):
    chat_id = message.chat.id
    parts = message.text.split()
    days = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
    cutoff = datetime.now() - timedelta(days=days)

    done, in_progress, no_reaction = [], [], []

    chat_tasks = tasks_by_chat.get(chat_id, {})
    for task in chat_tasks.values():
        if task["timestamp"] < cutoff:
            continue

        line = f"— {task['to'] or '❓'}: {task['text']}"
        if task["status"] == "👍":
            done.append(line)
        elif task["status"] == "🤝":
            in_progress.append(line)
        else:
            no_reaction.append(line)

    report = f"<b>📦 Задачи за {days} дн.:</b>\n"
    if done:
        report += "\n<b>👍 Выполнено:</b>\n" + "\n".join(done)
    if in_progress:
        report += "\n<b>🤝 В работе:</b>\n" + "\n".join(in_progress)
    if no_reaction:
        report += "\n<b>📥 Без реакции:</b>\n" + "\n".join(no_reaction)

    await message.answer(report)

@dp.message(F.text.lower().startswith("kpi"))
async def kpi_report(message: Message):
    await send_monthly_kpi_report(message.chat.id)

async def send_monthly_kpi_report(chat_id: int):
    cutoff = datetime.now() - timedelta(days=30)
    chat_tasks = tasks_by_chat.get(chat_id, {})
    user_stats = {}

    for task in chat_tasks.values():
        if task["timestamp"] < cutoff or not task["to"]:
            continue

        user = task["to"]
        if user not in user_stats:
            user_stats[user] = {"total": 0, "done": 0, "unhandled": 0}

        user_stats[user]["total"] += 1
        if task["status"] == "👍":
            user_stats[user]["done"] += 1
        else:
            user_stats[user]["unhandled"] += 1

    if not user_stats:
        await bot.send_message(chat_id, "Нет задач за последние 30 дней.")
        return

    lines = ["<b>📊 KPI за 30 дней:</b>"]
    for user, stats in user_stats.items():
        lines.append(
            f"\n{user}:\nВсего: {stats['total']}\n👍 Выполнено: {stats['done']}\n❗ Не выполнено: {stats['unhandled']}"
        )

    await bot.send_message(chat_id, "\n".join(lines))

async def monthly_kpi_task():
    sent_months = {}
    while True:
        now = datetime.now()
        if now.day == 1:
            for chat_id in tasks_by_chat:
                if sent_months.get(chat_id) != now.month:
                    await send_monthly_kpi_report(chat_id)
                    sent_months[chat_id] = now.month
        await asyncio.sleep(3600)

async def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.create_task(monthly_kpi_task())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
