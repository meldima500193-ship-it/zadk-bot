import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web

# Вставте сюди ваш токен або отримайте його з налаштувань Render
TOKEN = os.getenv("BOT_TOKEN", "ВАШ_ТОКЕН_БОТА")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Приклад обробника команди /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привіт! Я ваш бот, і я успішно запущений на Render! 🚀")

# 1. Мінімальний веб-сервер для Render (щоб він бачив відкритий порт)
async def handle(request):
    return web.Response(text="Bot is running and alive!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# 2. Головна функція запуску
async def main():
    # Видаляємо старий вебхук, щоб усунути конфлікт
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаємо веб-сервер у фоновому режимі для Render
    asyncio.create_task(start_web_server())
    
    # Запускаємо опитування (polling) для бота
    print("Бот запущено через polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
