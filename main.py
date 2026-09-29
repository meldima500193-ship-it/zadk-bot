import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import requests
from bs4 import BeautifulSoup

# --- КОНФІГУРАЦІЯ ---
TOKEN = "8771268059:AAH1bGKcTVJitkGBviccu8-RsE79gbbPipk"
ADMIN_IDS = [6090181325, 1083979869]
ZAMINA_URL = 'https://zadk.zt.ua/studentam/zmini-v-rozkladi-zanyat'

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

subscribers = set()
last_photo = None
last_text = "Замін поки немає."

class AdminState(StatesGroup):
    waiting_for_zamina = State()

def get_keyboard(user_id: int):
    is_admin = user_id in ADMIN_IDS
    buttons = [
        [KeyboardButton(text="📋 Переглянути заміни"), KeyboardButton(text="ℹ️ Про бота")],
        [KeyboardButton(text="🔔 Увімкнути сповіщення"), KeyboardButton(text="🔕 Вимкнути сповіщення")]
    ]
    if is_admin:
        buttons.append([KeyboardButton(text="➕ Додати заміну")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# --- АВТОМАТИЧНИЙ ПАРСИНГ САЙТУ ---
async def check_website():
    global last_photo, last_text
    while True:
        try:
            response = requests.get(ZAMINA_URL, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            img_element = soup.find('img')
            found_photo_url = img_element.get('src') if img_element else None

            if found_photo_url and found_photo_url.startswith('/'):
                found_photo_url = 'https://zadk.zt.ua' + found_photo_url

            if found_photo_url and found_photo_url != last_photo:
                last_photo = found_photo_url
                last_text = "📋 Оновлені заміни з сайту ВСП ЖАДФК НТУ!"

                for user_id in subscribers:
                    try:
                        await bot.send_photo(user_id, last_photo, caption=last_text)
                    except Exception:
                        pass
        except Exception as e:
            print(f"Помилка парсингу: {e}")

        await asyncio.sleep(300)

# --- КОМАНДИ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Ви на офіційному tg ВСП ЖАДФК НТУ ✅", reply_markup=get_keyboard(message.from_user.id))

@dp.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Дію скасовано. 🚫", reply_markup=get_keyboard(message.from_user.id))

# --- КНОПКИ МЕНЮ ---
@dp.message(F.text == "📋 Переглянути заміни")
async def view_zamina(message: types.Message):
    if last_photo:
        await message.answer_photo(last_photo, caption=last_text)
    else:
        await message.answer(last_text)

@dp.message(F.text == "🔔 Увімкнути сповіщення")
async def enable_notif(message: types.Message):
    subscribers.add(message.from_user.id)
    await message.answer("Сповіщення увімкнено! 🔔")

@dp.message(F.text == "🔕 Вимкнути сповіщення")
async def disable_notif(message: types.Message):
    subscribers.discard(message.from_user.id)
    await message.answer("Сповіщення вимкнено! 🔕")

@dp.message(F.text == "ℹ️ Про бота")
async def about_bot(message: types.Message):
    text = (
        "✨ *ВСП ЖАДФК НТУ* ✨\n"
        "────────────────────────\n"
        "ℹ️ *Інформація про бота*\n\n"
        "Цей бот створений для швидкого перегляду замін у розкладі занять нашого коледжу.\n\n"
        "👨‍💻 *Розробники:*\n• `Мельнічук Д.`\n• `Ярмола І.`\n\n"
        "🎓 *Керівник проєкту:*\n• *Іщук О.С.*\n"
        "────────────────────────"
    )
    await message.answer(text, parse_mode="Markdown")

# --- АДМІНСЬКА ЗОНА ---
@dp.message(F.text == "➕ Додати заміну")
async def add_zamina_btn(message: types.Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        await state.set_state(AdminState.waiting_for_zamina)
        cancel_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Скасувати")]], resize_keyboard=True)
        await message.answer("Надішліть фото або текст заміни. Для скасування натисніть нижче:", reply_markup=cancel_kb)

@dp.message(F.text == "❌ Скасувати")
async def cancel_admin(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Дію скасовано. ✅", reply_markup=get_keyboard(message.from_user.id))

@dp.message(AdminState.waiting_for_zamina)
async def process_admin_zamina(message: types.Message, state: FSMContext):
    global last_photo, last_text

    last_text = message.caption or message.text or "Нова заміна!"
    last_photo = message.photo[-1].file_id if message.photo else None

    await message.answer("Збережено! Розсилаю... ✅", reply_markup=get_keyboard(message.from_user.id))

    for user_id in subscribers:
        try:
            if last_photo:
                await bot.send_photo(user_id, last_photo, caption=last_text)
            else:
                await bot.send_message(user_id, "🔔 " + last_text)
        except Exception:
            pass

    await state.clear()

# --- ЗАПУСК БОТА ---
async def main():
    asyncio.create_task(check_website())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
