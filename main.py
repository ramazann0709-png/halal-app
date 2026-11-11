import os
import asyncio
from aiohttp import web
from urllib.parse import quote
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    PreCheckoutQuery,
    LabeledPrice
)

# 1. Вставьте ваш токен от BotFather
BOT_TOKEN = "ВАШ_ТОКЕН_ОТ_BOTFATHER"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

BASE_URL = "https://finansmsbot.host/index.html"

@dp.message(CommandStart())
async def send_mini_app(message: types.Message):
    invoice_link = await bot.create_invoice_link(
        title="Hisab Lite (1 месяц)",
        description="Умный алгоритм сбережений и аналитика капитала.",
        payload="lite_sub_1_month",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="Подписка на 1 месяц", amount=50)],
    )

    encoded_invoice = quote(invoice_link, safe="")
    dynamic_url = f"{BASE_URL}?users=1245&lite=312&invoice={encoded_invoice}"

    markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Открыть Hisab Finance", web_app=WebAppInfo(url=dynamic_url))]]
    )
    await message.answer("Управляйте своими финансами ☪️", reply_markup=markup)

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# Веб-сервер, который отвечает Render и подтверждает, что сервис активен
async def handle_ping(request):
    return web.Response(text="Hisab Finance Bot is Live!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    print("Бот запущен и готов принимать платежи!")
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
