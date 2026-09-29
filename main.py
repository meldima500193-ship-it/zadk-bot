import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web
from bs4 import BeautifulSoup
import aiohttp

TOKEN = os.getenv("BOT_TOKEN")
TARGET_URL = "https://zadk.zt.ua/"  # Адреса сайту коледжу (можна змінити на конкретну сторінку з розкладом)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Змінна для зберігання посилання на останнє знайдене фото замін
latest_photo_url = None

# Фонова задача, яка працює кожні 5 хвилин
async def check_schedule_loop():
    global latest_photo_url
    while True:
        try:
            print("Оновлення: перевірка сайту на нові фото замін...")
            async with aiohttp.ClientSession() as session:
                async with session.get(TARGET_URL) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Шукаємо зображення на сторінці 
                        # (за потреби селектор img можна буде уточнити під структуру сайту)
                        img_tag = soup.find('img') 
                        
                        if img_tag and img_tag.get('src'):
                            photo_url = img_tag['src']
                            # Якщо посилання відносне, робимо його абсолютним
                            if photo_url.startswith('/'):
                                photo_url = "https://zadk.zt.ua" + photo_url
                            
                            # Якщо з'явилося нове фото — оновлюємо
                            if photo_url != latest_photo_url:
                                latest_photo_url = photo_url
                                print(f"Знайдено нове фото замін: {latest_photo_url}")
        except Exception as e:
            print(f"Помилка під час парсингу сайту: {e}")
            
        # Чекаємо рівно 5 хвилин (300 секунд) перед наступною перевіркою
        await asyncio.sleep(300)

# Команда для користувачів, щоб отримати актуальні зміни
@dp.message(Command("changes", "schedule"))
async def cmd_changes(message: types.Message):
    if latest_photo_url:
        await message.answer_photo(photo=latest_photo_url, caption="Ось актуальні зміни в розкладі! 📋")
    else:
        await message.answer("Фото замін ще завантажується або не знайдено на головній сторінці. Сפрубуйте за хвилину.")

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привіт! Я бот розкладу ЖАДФК.\nНапиши /changes, щоб отримати найсвіжіші зміни занять.")

# Веб-сервер для утримання порту на Render
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

async def main():
    # Очищуємо старий вебхук
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Запускаємо веб-сервер та фоновий парсер
    asyncio.create_task(start_web_server())
    asyncio.create_task(check_schedule_loop())
    
    print("Бот запущено разом із фоновим оновленням розкладу...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
