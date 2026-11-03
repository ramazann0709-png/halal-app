import asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from aiogram.filters import CommandStart, Command
from db import (
    init_db,
    get_users_count,
    update_nisaab_from_cbr,
    get_balance,
    add_transaction,
    create_goal,
    add_money_to_goal,
    get_goal_progress,
    finish_goal,
    get_transactions_history,
    create_debt,
    delete_transaction,
    reset_all_data,
    get_goals,
    get_debts,
    get_nisaab,
    get_expenses_by_category,
    pay_debt
)

BOT_TOKEN = "8969041135:AAFrflT01mB8INpgr4w6b4-zbLEafiYyFRQ"
WEB_APP_URL = "https://finansmsbot.host"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

ADMIN_ID = 8774039431

@dp.message(Command("stats"))
async def stats_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    total = await get_users_count()
    await message.answer(f"📊 Статистика бота:\n\n👥 Всего пользователей: {total}")

def json_response(data):
    return web.json_response(data, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, ngrok-skip-browser-warning"
    })

async def handle_options(request):
    return web.Response(status=204, headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, ngrok-skip-browser-warning"
    })

async def api_get_data(request):
    user_id = int(request.query.get("user_id", 0))
    period = request.query.get("period", "month")
    
    balance = await get_balance(user_id)
    goals = await get_goals(user_id)
    debts = await get_debts(user_id)
    nisaab = await get_nisaab()
    categories = await get_expenses_by_category(user_id, period=period)
    history = await get_transactions_history(user_id, period=period)
    zakat = balance * 0.025 if balance >= nisaab else 0

    return json_response({
        "balance": balance,
        "goals": goals,
        "debts": debts,
        "nisaab": nisaab,
        "zakat": zakat,
        "categories": categories,
        "history": history
    })

async def api_add_transaction(request):
    data = await request.json()
    await add_transaction(data["user_id"], data["type"], data["category"], float(data["amount"]))
    return json_response({"status": "success"})

async def api_delete_transaction(request):
    data = await request.json()
    await delete_transaction(data["user_id"], int(data["transaction_id"]))
    return json_response({"status": "success"})

async def api_reset_data(request):
    data = await request.json()
    if data.get("confirmation") == "СБРОСИТЬ":
        await reset_all_data(data["user_id"])
        return json_response({"status": "success"})
    return json_response({"status": "error", "message": "Неверное кодовое слово"})

async def api_create_goal(request):
    data = await request.json()
    await create_goal(data["user_id"], data["name"], float(data["target"]))
    return json_response({"status": "success"})

async def api_fund_goal(request):
    data = await request.json()
    user_id = data["user_id"]
    goal_id = int(data["goal_id"])
    amount = float(data["amount"])
    
    await add_money_to_goal(user_id, goal_id, data["goal_name"], amount)
    progress = await get_goal_progress(goal_id)
    if progress and progress["current_amount"] >= progress["target_amount"]:
        await finish_goal(goal_id)
    return json_response({"status": "success"})

async def api_add_debt(request):
    data = await request.json()
    await create_debt(data["user_id"], data["creditor_name"], float(data["amount"]), data["due_date"])
    return json_response({"status": "success"})

async def api_pay_debt(request):
    data = await request.json()
    await pay_debt(data["user_id"], int(data["debt_id"]), data["creditor_name"], float(data["amount"]))
    return json_response({"status": "success"})

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    print(f">>> [OK] Получена команда /start от пользователя ID: {message.from_user.id}")
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Открыть кошелек", web_app=WebAppInfo(url=WEB_APP_URL))]],
        resize_keyboard=True
    )
    await message.answer("Халяль-кошелек готов к работе! Нажмите кнопку ниже:", reply_markup=markup)

async def main():
    await init_db()
    asyncio.create_task(update_nisaab_from_cbr())
    
    app = web.Application()
    app.router.add_route("OPTIONS", "/{tail:.*}", handle_options)
    app.router.add_get("/api/data", api_get_data)
    app.router.add_post("/api/transaction", api_add_transaction)
    app.router.add_post("/api/delete_transaction", api_delete_transaction)
    app.router.add_post("/api/reset_data", api_reset_data)
    app.router.add_post("/api/goal", api_create_goal)
    app.router.add_post("/api/fund", api_fund_goal)
    app.router.add_post("/api/debt", api_add_debt)
    app.router.add_post("/api/pay_debt", api_pay_debt)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print(">>> Сервер API запущен на порту 8080")
    print(">>> Бот слушает сообщения...")

    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n>>> Бот остановлен.")
