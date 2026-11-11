import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    WebAppInfo, 
    PreCheckoutQuery, 
    LabeledPrice
)

# 1. СЮДА ВСТАВЬ НОВЫЙ ТОКЕН ОТ BOTFATHER
BOT_TOKEN = "ВАШ_НОВЫЙ_ТОКЕН_ОТ_BOTFATHER"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 2. СЮДА УКАЖИ ТОЧНЫЙ ПУТЬ ДО ТВОЕГО HTML ФАЙЛА НА ХОСТИНГЕ
BASE_URL = "https://finansmsbot.host/index.html" # Уточни название файла (index.html или hisab_finance.html)

# ==========================================
# 1. КОМАНДА /START (ОТКРЫТИЕ МИНИ АПП)
# ==========================================
@dp.message(CommandStart())
async def send_mini_app(message: types.Message):
    # Здесь в будущем ты прикрутишь базу данных, пока ставим цифры для теста
    total_users = 1245
    total_lite = 312

    # Склеиваем ссылку с параметрами
    dynamic_url = f"{BASE_URL}?users={total_users}&lite={total_lite}"

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

# ==========================================
# 2. ЛОВИМ НАЖАТИЕ КНОПКИ ОПЛАТЫ ИЗ МИНИ АПП
# ==========================================
@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    if message.web_app_data.data == "buy_lite":
        # Отправляем счет в Звездах прямо в чат
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="Hisab Lite (1 месяц)",
            description="Умный алгоритм сбережений и продвинутая аналитика капитала.",
            payload="lite_sub_1_month",
            provider_token="",  # Строго пусто для Telegram Stars
            currency="XTR",     # Валюта - Звезды
            prices=[LabeledPrice(label="Подписка на 1 месяц", amount=50)], # 50 звезд
        )

# ==========================================
# 3. ПОДТВЕРЖДЕНИЕ ПЛАТЕЖА (Требование Telegram)
# ==========================================
@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# ==========================================
# 4. ДЕЙСТВИЕ ПОСЛЕ УСПЕШНОЙ ОПЛАТЫ
# ==========================================
@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    # Генерируем ссылку со специальным флагом ?paid=1, чтобы Mini App понял, что оплата прошла
    dynamic_url = f"{BASE_URL}?paid=1"
    
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Вернуться в Hisab", web_app=WebAppInfo(url=dynamic_url))
    ]])
    
    await message.answer(
        "🎉 Спасибо за оплату! 50 ⭐️ списано. Ваша подписка Hisab Lite успешно оформлена на 30 дней.",
        reply_markup=markup
    )

# ==========================================
# ЗАПУСК БОТА
# ==========================================
async def main():
    print("Бот запущен и готов принимать платежи!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
