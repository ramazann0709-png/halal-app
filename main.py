import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# 1. Вставьте сюда ваш токен от BotFather
BOT_TOKEN = "8969041135:AAFrflT01mB8INpgr4w6b4-zbLEafiYyFRQ"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def send_mini_app(message: types.Message):
    # Здесь в будущем вы будете брать цифры из вашей базы данных
    total_users = 1245
    total_lite = 312

    # 2. Вставьте сюда ссылку, где лежит ваш HTML-файл
    base_url = "https://finansmsbot.host"

    # Склеиваем ссылку с цифрами для панели разработчика
    dynamic_url = f"{base_url}?users={total_users}&lite={total_lite}"

    markup = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть Hisab Finance",
                    web_app=WebAppInfo(url=dynamic_url)
                )
            ]
        ]
    )

    await message.answer("Управляйте своими финансами ☪️", reply_markup=markup)

async def main():
    print("Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
