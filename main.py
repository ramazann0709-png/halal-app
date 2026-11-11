import asyncio
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

# 2. Базовый адрес вашего Mini App
BASE_URL = "https://finansmsbot.host/index.html"  # или hisab_finance.html


@dp.message(CommandStart())
async def send_mini_app(message: types.Message):
    # Генерируем инвойс-ссылку на оплату звездами
    invoice_link = await bot.create_invoice_link(
        title="Hisab Lite (1 месяц)",
        description="Умный алгоритм сбережений и продвинутая аналитика капитала.",
        payload="lite_sub_1_month",
        provider_token="",  # Строго пусто для Telegram Stars
        currency="XTR",
        prices=[LabeledPrice(label="Подписка на 1 месяц", amount=50)],
    )

    total_users = 1245
    total_lite = 312

    # Кодируем ссылку на инвойс, чтобы она корректно передалась через query-параметр
    encoded_invoice = quote(invoice_link, safe="")
    dynamic_url = f"{BASE_URL}?users={total_users}&lite={total_lite}&invoice={encoded_invoice}"

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


# Обязательный обработчик подтверждения платежа от Telegram
@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


async def main():
    print("Бот запущен и готов принимать платежи!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
