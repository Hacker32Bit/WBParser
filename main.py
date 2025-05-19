import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv
from typing import Final
import os
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums.parse_mode import ParseMode
import asyncio
import logging
import re
from urllib.parse import urlparse

# Logging setup
logging.basicConfig(level=logging.INFO)

load_dotenv()
TOKEN: Final[str] = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()


async def parse(message: Message):
    await message.answer("Running parser... Please wait.")

    process = await asyncio.create_subprocess_exec(
        sys.executable, "scripts/parser.py", "",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        output = stdout.decode().strip()
        await message.answer(f"✅ Parser finished:\n<pre>{output or 'No output'}</pre>")
    else:
        error = stderr.decode().strip()
        await message.answer(f"❌ Error while parsing:\n<pre>{error or 'Unknown error'}</pre>")


def is_number(s: str) -> bool:
    return s.isdigit()


def is_valid_url(s: str) -> bool:
    try:
        result = urlparse(s)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


# FSM States
class ParseForm(StatesGroup):
    waiting_for_url = State()
    waiting_for_description_choice = State()
    waiting_for_model_selection = State()


# Start command
@dp.message(Command("parse"))
async def cmd_parse(message: Message, state: FSMContext):
    await message.answer("Please enter Wildberries URL or article ID:")
    await state.set_state(ParseForm.waiting_for_url)


# Step 1: Receive article ID or URL
@dp.message(ParseForm.waiting_for_url)
async def process_url(message: Message, state: FSMContext):
    input_answer = message.text.strip()

    if is_number(input_answer):
        await state.update_data(url_or_id=int(input_answer))
    elif is_valid_url(input_answer):
        await state.update_data(url_or_id=input_answer)
    else:
        await message.answer("❌ Please provide a valid numeric ID or a URL.")
        return  # Don't proceed if invalid

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Yes", callback_data="desc_yes")
    keyboard.button(text="No", callback_data="desc_no")
    keyboard.adjust(2)

    await message.answer("Do you want to scan the description?", reply_markup=keyboard.as_markup())
    await state.set_state(ParseForm.waiting_for_description_choice)


# Step 2: Receive description scan choice
@dp.callback_query(ParseForm.waiting_for_description_choice)
async def process_description_choice(callback: CallbackQuery, state: FSMContext):
    await state.update_data(scan_description=callback.data == "desc_yes")

    # Create combined keyboard
    keyboard = InlineKeyboardBuilder()

    # Add first row of 4 buttons
    for i in ["All", "spaCy", "YAKE", "KeyBERT"]:
        keyboard.button(text=str(i), callback_data=f"model_{i}")
    keyboard.adjust(4)

    # Add second row with one long button
    keyboard.button(text="ChatGPT (Experimental)", callback_data="model_ChatGPT")
    keyboard.adjust(4, 1)  # First adjust keeps previous row, second puts the long button

    # Send updated message and keyboard
    await callback.message.edit_text("Select NLP model:")
    await callback.message.edit_reply_markup(reply_markup=keyboard.as_markup())

    await state.set_state(ParseForm.waiting_for_model_selection)


# Step 3: Receive model selection
@dp.callback_query(ParseForm.waiting_for_model_selection)
async def process_model_selection(callback: CallbackQuery, state: FSMContext):
    model_number = callback.data.split("_")[1]
    await state.update_data(nlp_model=model_number)

    data = await state.get_data()
    await callback.message.edit_text(
        f"✅ Collected data:\n"
        f"🔗 URL/ID: {data['url_or_id']}\n"
        f"📄 Scan description: {True if data['scan_description'] else False}\n"
        f"🤖 NLP Model: {data['nlp_model']}"
    )

    # Finish the FSM
    await state.clear()

    await callback.message.answer("Running parser... Please wait.")

    user_id = callback.message.from_user.id
    output_dir = "output"
    output_path = os.path.join(output_dir, f"{user_id}.txt")
    os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w") as outfile:
        process = await asyncio.create_subprocess_exec(
            sys.executable, "scripts/parser.py",
            "--url", str(data['url_or_id']),
            "--desc" if data['scan_description'] else "--no-desc",
            "--model", data['nlp_model'],
            stdout=outfile,
            stderr=outfile,
        )

        await process.communicate()

    if process.returncode == 0:
        await callback.message.answer("✅ Parser finished. Sending the result file...")
    else:
        await callback.message.answer("❌ Parser encountered an error. Sending the log file...")

    result_file = FSInputFile(output_path, filename=f"result_{user_id}.txt")
    await callback.message.answer_document(result_file)

    # Optional: clean up after sending
    try:
        os.remove(output_path)
    except Exception as e:
        print(f"Warning: Could not delete file {output_path} - {e}")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
