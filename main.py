import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message

load_dotenv()
TOKEN: Final[str] = os.getenv("TOKEN")


bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()


@dp.message(Command("parse"))
async def parse_command(message: Message):
    await message.answer("Starting parser... Please wait.")

    # Run the external Python script asynchronously
    process = await asyncio.create_subprocess_exec(
        "python3", "scripts/parser.py",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        await message.answer("✅ Parsing completed successfully.")
    else:
        error_msg = stderr.decode().strip()
        await message.answer(f"❌ Error while parsing:\n<pre>{error_msg}</pre>")


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)
    import asyncio

    asyncio.run(dp.start_polling(bot))
