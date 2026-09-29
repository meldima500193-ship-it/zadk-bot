import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiohttp import web
from bs4 import BeautifulSoup
import aiohttp

TOKEN = os.getenv("BOT_TOKEN")
# Використовуємо режим /preview, який доступний для перегляду всім без логіну
DOC_URL = "https://docs.google.com/document/d/1zAjNgUKTNn0tuRuD-CswvxEC8Oe9RvYr/preview"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Змінна для зберігання посилання на останнє знайдене фото
latest_photo_url = None

# Фонова задача для перевірки документа кожні 5 хвилин
async def check_schedule_loop():
    global latest_photo_url
    while True:
        try:
            print("Перевірка Google Документа (preview) на нові фото замін...")
            async with aiohttp.ClientSession() as session:
                async with session.get(DOC_URL) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Шукаємо всі зображення у прев'ю документі
                        images = soup.find_all('img')
                        photo_url = None
                        
                        for img in images:
                            src = img.get('src', '')
                            # Картинки в Google Docs зазвичай містять googleusercontent
                            if 'googleusercontent' in src or 'docs.google.com' in src:
                                photo_url = src
                                break
                        
                        if not photo_url and images:
                            photo_url = images[0].get('src', '')
                        
                        if photo_url:
                            if photo_url.startswith('/'):
                                photo_url = "https://docs.google.com" + photo_url
                            
                            # Якщо з'явилося нове фото — оновлюємо
                            if photo_url != latest_photo_url:
                                latest_photo_url = photo_url
                                print(f"Знайдено нове фото замін із Google Документа: {latest_photo_url}")
        except Exception as e:
            print(f"Помилка під час зчитування Google Документа: {e}")
            
        # Чекаємо 5 хвилин (300 секунд)
        await asyncio.sleep(300)

# Команда для користувачів
@dp.message(Command("changes", "schedule"))
async def cmd_changes(message: types.Message):
    if latest_photo_url:
        try:
            await message.answer_photo(photo=latest_photo_url, caption="📋 Актуальні зміни в розкладі з Google Документа:")
        except Exception:
            await message.answer(f"Ось посилання на документ зі змінами: {DOC_URL.replace('/preview', '/edit')}")
    else:
        await message.answer("Фото замін у документі ще завантажується ботом. Спробуйте за хвилину.")

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привіт! Я бот розкладу ЖАДФК.\nНапиши /changes, щоб отримати найсвіжіші зміни з Google Документа.")

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
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(start_web_server())
    asyncio.create_task(check_schedule_loop())
    
    print("Бот запущено із переглядом Google Документа через /preview...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
