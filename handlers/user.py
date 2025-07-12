from aiogram import Router
from aiogram.types import Message, FSInputFile
import os

user_router = Router()

@user_router.message(lambda msg: msg.text == "📢 Barcha ovozlar")
async def list_all_voices(message: Message):
    os.makedirs("voices", exist_ok=True)
    voices = sorted(os.listdir("voices"))

    if not voices:
        await message.answer("📭 Hozircha hech qanday ovozli xabar yuklanmagan.")
        return

    for file_name in voices:
        file_path = os.path.join("voices", file_name)
        voice = FSInputFile(file_path)
        await message.answer_voice(voice)