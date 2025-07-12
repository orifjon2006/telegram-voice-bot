from aiogram import Router, F
from aiogram.types import Message
from config import ADMIN_ID
import os
import time

admin_router = Router()

@admin_router.message(F.from_user.id == ADMIN_ID, F.text == "🎙 Ovoz yuklash")
async def prompt_for_voice(message: Message):
    await message.answer("Iltimos, yubormoqchi bo‘lgan ovozli xabaringizni tashlang.")

@admin_router.message(F.from_user.id == ADMIN_ID, F.voice)
async def save_voice(message: Message):
    os.makedirs("voices", exist_ok=True)
    filename = f"voices/voice_{int(time.time())}.ogg"

    file = await message.bot.get_file(message.voice.file_id)
    await message.bot.download_file(file.file_path, destination=filename)

    await message.answer("✅ Ovoz muvaffaqiyatli saqlandi!")