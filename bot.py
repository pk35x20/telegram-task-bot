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

def task_buttons(msg_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("👍 Выполнено", callback_data=f"done:{msg_id}"),
            InlineKeyboardButton("🤝 В работе", callback_data=f"in_progress:{msg_id}")
        ]
    ])

@dp.message(F.text.lower().contains("#задача"))
async def collect_task(message: Message):
    chat_id = message.chat.id
    text = message.text.strip()
    words = text.split()

    # 1) Пробуем найти entity-mention
    to_user = None
    if message.entities:
        for ent in message.entities:
            if ent.type == "mention":
                to_user = text[ent.offset:ent.offset + ent.length]
                break

    # 2) Фоллбэк: слово после #задача
    if not to_user and len(words) >= 2 and words[0].lower() == "#задача":
        to_user = words[1].strip(",.():;!?")

    reply = "Задача зарегистрирована.\nСтатус: 📥 Ожидает\n(нажмите кнопку ниже)"
    reply_msg = await message.reply(reply, reply_markup=task_buttons(message.message_id))

    tasks_by_chat.setdefault(chat_id, {})[message.message_id] = {
        "text": text,
        "author": message.from_user.mention_html(),
        "to": to_user,
        "timestamp": datetime.now(),
        "status": "📥",
        "reply_msg_id": reply_msg.message_id,
    }

@dp.callback_query(F.data.startswith("done:") | F.data.startswith("in_progress:"))
async def handle_status_change(cb: CallbackQuery):
    action, msg_id_str = cb.data.split(":")
    msg_id = int(msg_id_str)
    chat_id = cb.message.chat.id
    chat_tasks = tasks_by_chat.get(chat_id, {})

    if msg_id in chat_tasks:
        emoji = "👍" if action == "done" else "🤝"
        chat_tasks[msg_id]["status"] = emoji
        user = cb.from_user.mention_html()
        reply_id = chat_tasks[msg_id]["reply_msg_id"]

        new_text = f"Задача зарегистрирована.\nСтатус: {emoji} (обновил {user})"
        try:
            await bot.edit_message_text(
                new_text, chat_id, reply_id, reply_markup=task_buttons(msg_id)
            )
        except Exception as e:
            logging.warning(f"Не удалось обновить: {e}")

        await cb.answer(f"Статус: {'Выполнено' if action=='done' else 'В работе'}")
    else:
        await cb.answer("Задача не найдена", show_alert=True)

@dp.message(F.text.lower().startswith("собери"))
async def collect_report(message: Message):
    chat_id = message.chat.id
    parts = message.text.split()
    days = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
    cutoff = datetime.now() - timedelta(days=days)

    done, prog, pend = [], [], []
    for task in tasks_by_chat.get(chat_id, {}).values():
        if task["timestamp"] < cutoff:
            continue
        line = f"— {task['to'] or '❓'}: {task['text']}"
        if task["status"] == "👍":
            done.append(line)
        elif task["status"] == "🤝":
            prog.append(line)
        else:
            pend.append(line)

    report = f"<b>📦 Задачи за {days} дн.:</b>\n"
    if done:
        report += "\n<b>👍 Выполнено:</b>\n" + "\n".join(done)
    if prog:
        report += "\n<b>🤝 В работе:</b>\n" + "\n".join(prog)
    if pend:
        report += "\n<b>📥 Без реакции:</b>\n" + "\n".join(pend)

    await message.answer(report, parse_mode=ParseMode.HTML)

@dp.message(F.text.lower().startswith("kpi"))
async def kpi_report(message: Message):
    await send_monthly_kpi_report(message.chat.id)

async def send_monthly_kpi_report(chat_id: int):
    cutoff = datetime.now() - timedelta(days=30)
    stats = {}
    for task in tasks_by_chat.get(chat_id, {}).values():
        if task["timestamp"] < cutoff or not task["to"]:
            continue
        user = task["to"]
        stats.setdefault(user, {"total": 0, "done": 0, "unhandled": 0})
        stats[user]["total"] += 1
        if task["status"] == "👍":
            stats[user]["done"] += 1
        else:
            stats[user]["unhandled"] += 1

    if not stats:
        await bot.send_message(chat_id, "Нет задач с адресацией за последние 30 дней.")
        return

    lines = ["<b>📊 KPI за 30 дней:</b>"]
    for user, s in stats.items():
        lines.append(
            f"\n{user}:\nВсего задач: {s['total']}\n👍 Выполнено: {s['done']}\n❗ Не выполнено: {s['unhandled']}"
        )
    await bot.send_message(chat_id, "\n".join(lines), parse_mode=ParseMode.HTML)

async def monthly_kpi_task():
    sent = {}
    while True:
        now = datetime.now()
        if now.day == 1:
            for cid in tasks_by_chat:
                if sent.get(cid) != now.month:
                    await send_monthly_kpi_report(cid)
                    sent[cid] = now.month
        await asyncio.sleep(3600)

async def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.create_task(monthly_kpi_task())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())