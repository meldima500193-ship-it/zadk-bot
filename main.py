import os
import asyncio
import logging
import zipfile
import io
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web
import aiohttp

TOKEN = os.getenv("BOT_TOKEN")
# Посилання на прямий експорт документа у форматі ZIP
DOC_EXPORT_URL = "https://docs.google.com/document/d/1zAjNgUKTNn0tuRuD-CswvxEC8Oe9RvYr/export?format=zip"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Головне меню з інлайн-кнопками
code_keyboard = InlineKeyboardBuilder()
code_keyboard.button(text="📋 Переглянути заміну", callback_data="show_changes")
code_keyboard.button(text="ℹ️️ Про бота", callback_data="about_bot")
code_keyboard.adjust(1)  # Кнопки у стовпчик

# Змінні для зберігання останніх байтів зображення та його розміру
latest_image_bytes = None
last_image_size = 0

# Фонова задача для перевірки документа кожні 5 хвилин
async def check_schedule_loop():
    global latest_image_bytes, last_image_size
    while True:
        try:
            print("Завантаження архіву Google Документа...")
            async with aiohttp.ClientSession() as session:
                async with session.get(DOC_EXPORT_URL) as response:
                    if response.status == 200:
                        zip_data = await response.read()
                        
                        # Розпаковуємо ZIP-архів у пам'яті
                        with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                            image_files = [f for f in z.namelist() if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
                            
                            if image_files:
                                largest_img = max(image_files, key=lambda f: z.getinfo(f).file_size)
                                img_bytes = z.read(largest_img)
                                img_size = len(img_bytes)
                                
                                if img_size != last_image_size:
                                    latest_image_bytes = img_bytes
                                    last_image_size = img_size
                                    print(f"Знайдено нове фото замін! Розмір: {img_size} байт")
        except Exception as e:
            print(f"Помилка під час завантаження документа: {e}")
            
        await asyncio.sleep(300)

# Команда /start та головна панель
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        "👋 **Вітаю! Це офіційний бот замін розкладу ВСП ЖАДФК.**\n\n"
        "Бот працює 24/7 та автоматично оновлює інформацію з Google Документа.\n"
        "Оберіть потрібну дію за допомогою кнопок нижче:"
    )
    await message.answer(welcome_text, reply_markup=code_keyboard.as_markup(), parse_mode="Markdown")

# Обробник кнопки «Переглянути заміну»
@dp.callback_query(F.data == "show_changes")
async def process_show_changes(callback: types.CallbackQuery):
    await callback.answer()
    if latest_image_bytes:
        try:
            photo_file = BufferedInputFile(latest_image_bytes, filename="schedule.jpg")
            await callback.message.answer_photo(photo=photo_file, caption="📋 Актуальні зміни в розкладі:")
        except Exception as e:
            await callback.message.answer(f"Помилка відправки фото: {e}")
    else:
        await callback.message.answer("⏳ Фото замін у документі ще завантажується ботом. Спробуйте за хвилину.")

# Обробник кнопки «Про бота» з оновленою інформацією
@dp.callback_query(F.data == "about_bot")
async def process_about_bot(callback: types.CallbackQuery):
    await callback.answer()
    about_text = (
        "ℹ️ **Інформація про бота:**\n\n"
        "• **Призначення:** Надання актуального розкладу та замін занять для студентів і викладачів ВСП ЖАДФК.\n"
        "• **Оновлення:** Бот автоматично оновлює заміни кожні 5 хвилин у фоновому режимі.\n"
        "• **Розробка:** Проєкт був створений двома студентами групи ІСТ-1152.\n"
        "• **Статус:** Працює стабільно 24/7 на сервері Render 🚀"
    )
    await callback.message.answer(about_text, reply_markup=code_keyboard.as_markup(), parse_mode="Markdown")

# Текстова команда /changes
@dp.message(Command("changes", "schedule"))
async def cmd_changes(message: types.Message):
    if latest_image_bytes:
        try:
            photo_file = BufferedInputFile(latest_image_bytes, filename="schedule.jpg")
            await message.answer_photo(photo=photo_file, caption="📋 Актуальні зміни в розкладі:")
        except Exception as e:
            await message.answer(f"Помилка відправки фото: {e}")
    else:
        await message.answer("⏳ Фото замін у документі ще завантажується ботом. Спробуйте за хвилину.")

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
    
    print("Бот запущено із панеллю керування та фоновим оновленням...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
