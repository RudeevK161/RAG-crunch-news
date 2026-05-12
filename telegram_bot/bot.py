import asyncio
import logging
import os
import httpx
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes


BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_BASE_URL = os.getenv("API_BASE_URL", "http://nginx:80/api/v1")
TIMEOUT = 60

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_tasks = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *RAG-бот готов!*\n\n"
        "Просто отправь вопрос.\n\n"
        "/status — статус\n"
        "/cancel — отменить",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 *Команды:*\n\n"
        "/start — запуск\n"
        "/status — статус\n"
        "/cancel — отмена\n\n"
        "Просто отправь вопрос текстом.",
        parse_mode="Markdown"
    )


async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    user_id = update.effective_user.id

    msg = await update.message.reply_text(
        f"🔍 *Ищу ответ...*\n\n_{question[:150]}_",
        parse_mode="Markdown"
    )

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{API_BASE_URL}/rag/ask",
                json={"question": question, "style": "concise"},
                timeout=10
            )

        r.raise_for_status()
        task_id = r.json()["task_id"]

        user_tasks[user_id] = task_id

        asyncio.create_task(wait_for_result(task_id, msg, question, user_id))

    except Exception as e:
        logger.error(e)
        await msg.edit_text("Ошибка подключения к серверу")


async def wait_for_result(task_id, message, question, user_id):
    try:
        async with httpx.AsyncClient() as client:
            for _ in range(TIMEOUT):
                r = await client.get(f"{API_BASE_URL}/status/{task_id}", timeout=5)

                if r.status_code != 200:
                    await asyncio.sleep(1)
                    continue

                data = r.json()

                if data["status"] == "completed":
                    result = data.get("result", {})
                    answer = result.get("answer", "Нет ответа")

                    await message.edit_text(
                        f"✅ *Ответ:*\n\n{answer}\n\n",
                        parse_mode="Markdown"
                    )

                    user_tasks.pop(user_id, None)
                    return

                elif data["status"] == "failed":
                    await message.edit_text("Ошибка при обработке")
                    user_tasks.pop(user_id, None)
                    return

                await asyncio.sleep(1)

        await message.edit_text("Таймаут ожидания")

    except Exception as e:
        logger.error(e)
        await message.edit_text("Ошибка при получении результата")


async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_tasks:
        await update.message.reply_text("Нет активных задач")
        return

    task_id = user_tasks[user_id]

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(f"{API_BASE_URL}/status/{task_id}")

        if r.status_code == 200:
            status = r.json()["status"]
            await update.message.reply_text(f"Статус: `{status}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("Ошибка получения статуса")

    except:
        await update.message.reply_text("Ошибка соединения")


async def cancel_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_tasks:
        await update.message.reply_text("Нет задач для отмены")
        return

    task_id = user_tasks[user_id]

    try:
        async with httpx.AsyncClient() as client:
            r = await client.delete(f"{API_BASE_URL}/status/{task_id}")

        if r.status_code == 200:
            await update.message.reply_text("Отменено")
            user_tasks.pop(user_id, None)
        else:
            await update.message.reply_text("Не удалось отменить")

    except:
        await update.message.reply_text("Ошибка при отмене")


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", check_status))
    app.add_handler(CommandHandler("cancel", cancel_task))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ask_question))

    logger.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()