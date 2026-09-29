import os
import asyncio
import logging
import zipfile
import io
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web
import aiohttp

TOKEN = os.getenv("BOT_TOKEN")
# Посилання на прямий експорт документа у форматі ZIP
DOC_EXPORT_URL = "https://docs.google.com/document/d/1zAjNgUKTNn0tuRuD-CswvxEC8Oe9RvYr/export?format=zip"

# ID адміністраторів
ADMIN_IDS = [6090181325, 1083979869]

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Змінні для зберігання зображення та підписників
latest_image_bytes = None
last_image_size = 0
subscribers = set()  # Множина ID користувачів, які увімкнули сповіщення

# Постійна клавіатура нижче чату (ReplyKeyboard)
main_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Переглянути заміну"), KeyboardButton(text="ℹ️ Про бота")],
        [KeyboardButton(text="🔔 Увімкнути сповіщення"), KeyboardButton(text="🔕 Вимкнути сповіщення")],
        [KeyboardButton(text="➕ Додати заміну")]
    ],
    resize_keyboard=True
)

# Функція розсилки нових замін підписникам
async def broadcast_new_schedule(img_bytes):
    if not subscribers:
        return
    print(f"Розсилка нового розкладу для {len(subscribers)} користувачів...")
    for user_id in list(subscribers):
        try:
            photo_file = BufferedInputFile(img_bytes, filename="schedule.jpg")
            await bot.send_photo(chat_id=user_id, photo=photo_file, caption="🔔 Увага! З'явився новий розклад замін:")
        except Exception as e:
            print(f"Не вдалося надіслати користувачу {user_id}: {e}")
            # Якщо користувач заблокував бота, видаляємо його з підписок
            subscribers.discard(user_id)

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
                                    # Робимо автоматичну розсилку всім, хто підписався
                                    await broadcast_new_schedule(img_bytes)
        except Exception as e:
            print(f"Помилка під час завантаження документа: {e}")
            
        await asyncio.sleep(300)

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        "👋 **Вітаю! Це офіційний бот замін розкладу ВСП ЖАДФК.**\n\n"
        "Бот працює 24/7 та автоматично оновлює інформацію з Google Документа.\n"
        "Користуйтеся кнопками нижньої панелі для керування:"
    )
    await message.answer(welcome_text, reply_markup=main_reply_keyboard, parse_mode="Markdown")

# Обробник кнопки та команди «Переглянути заміну»
@dp.message(F.text == "📋 Переглянути заміну")
@dp.message(Command("changes", "schedule"))
async def handle_show_changes(message: types.Message):
    if latest_image_bytes:
        try:
            photo_file = BufferedInputFile(latest_image_bytes, filename="schedule.jpg")
            await message.answer_photo(photo=photo_file, caption="📋 Актуальні зміни в розкладі:")
        except Exception as e:
            await message.answer(f"Помилка відправки фото: {e}")
    else:
        await message.answer("⏳ Фото замін у документі ще завантажується ботом. Спробуйте за хвилину.")

# Обробник кнопки «Про бота»
@dp.message(F.text == "ℹ️ Про бота")
async def handle_about_bot(message: types.Message):
    about_text = (
        "ℹ️ **Інформація про бота:**\n\n"
        "• **Призначення:** Надання актуального розкладу та замін занять для студентів і викладачів ВСП ЖАДФК.\n"
        "• **Оновлення:** Бот автоматично оновлює заміни кожні 5 хвилин у фоновому режимі.\n"
        "• **Розробка:** Проєкт був створений двома студентами групи ІСТ-1152.\n"
        "• **Статус:** Працює стабільно 24/7 на сервері Render 🚀"
    )
    await message.answer(about_text, reply_markup=main_reply_keyboard, parse_mode="Markdown")

# Обробник кнопки «Увімкнути сповіщення»
@dp.message(F.text == "🔔 Увімкнути сповіщення")
async def handle_enable_notifications(message: types.Message):
    subscribers.add(message.from_user.id)
    await message.answer("✅ Сповіщення успішно увімкнено! Ви отримуватимете нові заміни одразу після їх оновлення.")

# Обробник кнопки «🔕 Вимкнути сповіщення»
@dp.message(F.text == "🔕 Вимкнути сповіщення")
async def handle_disable_notifications(message: types.Message):
    subscribers.discard(message.from_user.id)
    await message.answer("🔕 Сповіщення вимкнено.")

# Обробник кнопки «➕ Додати заміну»
@dp.message(F.text == "➕ Додати заміну")
async def handle_add_change_prompt(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("📸 Надішліть фото нової замін сюди, і вона автоматично оновиться для всіх користувачів!")
    else:
        await message.answer("ℹ️ Основний розклад підтягується автоматично з Google Документа. Ця функція призначена для адміністраторів.")

# Перехоплення фото від адміністраторів (для ручного оновлення)
@dp.message(F.photo)
async def handle_admin_photo(message: types.Message):
    global latest_image_bytes, last_image_size
    if message.from_user.id in ADMIN_IDS:
        try:
            # Отримуємо найбільше фото з можливих
            photo = message.photo[-1]
            file_info = await bot.get_file(photo.file_id)
            file_path = file_info.file_path
            
            # Завантажуємо байти фото в пам'ять
            file_bytes_io = io.BytesIO()
            await bot.download_file(file_path, destination=file_bytes_io)
            latest_image_bytes = file_bytes_io.getvalue()
            last_image_size = len(latest_image_bytes)
            
            await message.answer("✅ Фото замін успішно оновлено вручну та розіслано підписникам!")
            await broadcast_new_schedule(latest_image_bytes)
        except Exception as e:
            await message.answer(f"❌ Помилка завантаження фото: {e}")
    else:
        await message.answer("⚠️ Тільки адміністратори можуть завантажувати заміни напряму.")

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
    
    print("Бот запущено із робочою нижньою панеллю та розсилкою...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
