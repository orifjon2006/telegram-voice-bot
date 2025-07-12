import asyncio
import os
import json
import re
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup,
    CallbackQuery, InlineQuery, InlineQueryResultCachedVoice
)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import logging

# === CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "8135952933:AAG-zxzVoL8hW-BhVAfX-ZnX5qMNsHyITCU")  # .env faylidan o'qish tavsiya etiladi
ADMIN_PASSWORD = "1"  # Xavfsizlik uchun .env fayliga ko'chirish tavsiya etiladi
VOICE_DIR = "voices"
FILE_ID_PATH = "file_ids.json"
ADMINS_FILE = "admins.json"

# Logging sozlash
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === BOT OBYEKTI ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# === FSM HOLATLARI ===
class VoiceUpload(StatesGroup):
    waiting_for_name = State()

class AdminAuth(StatesGroup):
    waiting_for_password = State()

class VoiceDelete(StatesGroup):
    waiting_for_name = State()

# === YORDAMCHI FUNKSIYALAR ===
def load_admins() -> set:
    """Doimiy adminlarni fayldan yuklash"""
    try:
        if os.path.exists(ADMINS_FILE):
            with open(ADMINS_FILE, "r") as f:
                return set(json.load(f))
        return set()
    except Exception as e:
        logger.error(f"Adminlarni yuklashda xato: {e}")
        return set()

def save_admins(admins: set):
    """Adminlarni faylga saqlash"""
    try:
        with open(ADMINS_FILE, "w") as f:
            json.dump(list(admins), f)
    except Exception as e:
        logger.error(f"Adminlarni saqlashda xato: {e}")

def load_file_ids() -> dict:
    """Ovozli fayllar IDlarini yuklash"""
    try:
        if os.path.exists(FILE_ID_PATH):
            with open(FILE_ID_PATH, "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Fayl IDlarini yuklashda xato: {e}")
        return {}

def save_file_id(name: str, file_id: str):
    """Ovozli fayl IDni saqlash"""
    try:
        data = load_file_ids()
        data[name] = file_id
        with open(FILE_ID_PATH, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Fayl IDni saqlashda xato: {e}")

def sanitize_filename(name: str) -> str:
    """Fayl nomini xavfsiz qilish"""
    name = re.sub(r'[^\w\s-]', '', name).replace(" ", "_").lower()
    return name[:50]  # Fayl nomi uzunligini cheklash

def is_admin(user_id: int) -> bool:
    """Foydalanuvchi admin ekanligini tekshirish"""
    return user_id in load_admins()

# === START KOMANDASI ===
@dp.message(F.text == "/start")
async def start_handler(message: Message):
    buttons = [
        [KeyboardButton(text="🎙 Ovoz yuklash")],
        [KeyboardButton(text="📢 Barcha ovozlar")],
        [KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="🔍 ovoz_nomi")],
        [KeyboardButton(text="🗑 Ovoz o‘chirish")]
    ]
    kb = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("🎧 Xush kelibsiz! Botdan foydalanib ovozli xabarlar saqlang va ulashing.", reply_markup=kb)

# === ADMIN PAROLI ===
@dp.message(F.text == "/admin")
async def request_admin_password(message: Message, state: FSMContext):
    await message.answer("🔐 Admin parolni kiriting:")
    await state.set_state(AdminAuth.waiting_for_password)

@dp.message(AdminAuth.waiting_for_password, F.text)
async def check_admin_password(message: Message, state: FSMContext):
    if message.text == ADMIN_PASSWORD:
        admins = load_admins()
        admins.add(message.from_user.id)
        save_admins(admins)
        await message.answer("✅ Admin huquqlari berildi!")
    else:
        await message.answer("❌ Noto‘g‘ri parol.")
    await state.clear()

# === OVOZ NOMINI KIRITISH ===
@dp.message(F.text == "🎙 Ovoz yuklash")
async def ask_voice_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Bu funksiya faqat adminlar uchun.")
        return
    await message.answer("📌 Ovoz uchun nom kiriting:")
    await state.set_state(VoiceUpload.waiting_for_name)

# === NOM SAQLASH VA OVOZ YUKLASH ===
@dp.message(VoiceUpload.waiting_for_name, F.text)
async def save_named_voice(message: Message, state: FSMContext):
    await state.update_data(name=sanitize_filename(message.text))
    await message.answer("🎤 Endi ovozli xabar yuboring.")
    await state.set_state(None)

# === OVOZ SAQLASH ===
@dp.message(F.voice)
async def save_voice_file(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Faqat adminlar ovoz yuklashi mumkin.")
        return

    user_data = await state.get_data()
    name = user_data.get("name")
    if not name:
        await message.answer("❗ Avval ovoz uchun nom kiriting ('🎙 Ovoz yuklash').")
        return

    try:
        os.makedirs(VOICE_DIR, exist_ok=True)
        path = f"{VOICE_DIR}/{name}.ogg"
        file = await bot.get_file(message.voice.file_id)
        await bot.download_file(file.file_path, destination=path)

        sent = await message.answer_voice(FSInputFile(path))
        save_file_id(name, sent.voice.file_id)
        await message.answer(f"✅ Ovoz saqlandi: {name}")
    except Exception as e:
        logger.error(f"Ovoz saqlashda xato: {e}")
        await message.answer("❌ Ovozni saqlashda xato yuz berdi.")
    finally:
        await state.clear()

# === BARCHA OVOZLAR ===
@dp.message(F.text == "📢 Barcha ovozlar")
async def list_all_voices(message: Message):
    try:
        os.makedirs(VOICE_DIR, exist_ok=True)
        files = os.listdir(VOICE_DIR)
        if not files:
            await message.answer("📭 Hech qanday ovoz mavjud emas.")
            return
        reply = "🎧 Mavjud ovozlar:\n\n" + "\n".join(f"• {f[:-4]}" for f in sorted(files))
        await message.answer(reply)
    except Exception as e:
        logger.error(f"Ovozlarni ro'yxatlashda xato: {e}")
        await message.answer("❌ Ovozlarni ko'rsatishda xato yuz berdi.")

# === QIDIRISH ===
@dp.message(F.text.startswith("🔍 "))
async def search_voice(message: Message):
    query = message.text[2:].strip().lower()
    try:
        for file in os.listdir(VOICE_DIR):
            if query in file.lower():
                path = os.path.join(VOICE_DIR, file)
                await message.answer_voice(FSInputFile(path), caption=f"🔊 Topildi: {file[:-4]}")
                return
        await message.answer("❌ Ovoz topilmadi.")
    except Exception as e:
        logger.error(f"Qidiruvda xato: {e}")
        await message.answer("❌ Qidiruvda xato yuz berdi.")

# === STATISTIKA ===
@dp.message(F.text == "📊 Statistika")
async def stats(message: Message):
    try:
        count = len(os.listdir(VOICE_DIR))
        await message.answer(f"📈 Jami {count} ta ovozli fayl mavjud.")
    except Exception as e:
        logger.error(f"Statistikada xato: {e}")
        await message.answer("❌ Statistikani ko'rsatishda xato yuz berdi.")

# === OVOZ O‘CHIRISH (YANGI) ===
@dp.message(F.text == "🗑 Ovoz o‘chirish")
async def ask_delete_voice_name(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Bu funksiya faqat adminlar uchun.")
        return
    await message.answer("🗑 O‘chirmoqchi bo‘lgan ovoz nomini kiriting:")
    await state.set_state(VoiceDelete.waiting_for_name)

@dp.message(VoiceDelete.waiting_for_name, F.text)
async def delete_voice_by_name(message: Message, state: FSMContext):
    name = sanitize_filename(message.text)
    path = os.path.join(VOICE_DIR, f"{name}.ogg")
    try:
        if os.path.exists(path):
            os.remove(path)
            file_ids = load_file_ids()
            file_ids.pop(name, None)
            with open(FILE_ID_PATH, "w") as f:
                json.dump(file_ids, f)
            await message.answer(f"🗑 Ovoz o‘chirildi: {name}")
        else:
            await message.answer(f"❌ '{name}' nomli ovoz topilmadi.")
    except Exception as e:
        logger.error(f"Ovoz o'chirishda xato: {e}")
        await message.answer("❌ Ovoz o‘chirishda xato yuz berdi.")
    finally:
        await state.clear()

# === INLINE QIDIRUV ===
@dp.inline_query()
async def inline_voice_search(query: InlineQuery):
    try:
        file_ids = load_file_ids()
        if not file_ids:
            await query.answer([], cache_time=1, switch_pm_text="Hech qanday ovoz topilmadi", switch_pm_parameter="empty")
            return

        results = []
        search_text = (query.query or "").strip().lower()
        bot_username = (await bot.get_me()).username.lower()
        is_username_query = search_text == bot_username or search_text == ""

        for name, file_id in sorted(file_ids.items()):  # Alfavit tartibida
            if is_username_query or search_text in name.lower():
                results.append(InlineQueryResultCachedVoice(
                    id=name,
                    title=name,
                    voice_file_id=file_id
                ))

        await query.answer(results[:50], cache_time=1)
    except Exception as e:
        logger.error(f"Inline qidiruvda xato: {e}")
        await query.answer([], cache_time=1, switch_pm_text="Xato yuz berdi", switch_pm_parameter="error")

# === RUN ===
async def main():
    try:
        os.makedirs(VOICE_DIR, exist_ok=True)
        logger.info("Bot ishga tushdi...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Botni ishga tushirishda xato: {e}")

if __name__ == "__main__":
    asyncio.run(main())