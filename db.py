import aiosqlite
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import aiohttp

DB_NAME = "finances.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.executescript('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT,
                category TEXT,
                amount REAL,
                date TIMESTAMP DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                goal_name TEXT,
                target_amount REAL,
                current_amount REAL DEFAULT 0.0
            );
            CREATE TABLE IF NOT EXISTS debts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                creditor_name TEXT,
                amount REAL,
                paid_amount REAL DEFAULT 0.0,
                due_date TEXT
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value REAL
            );
            INSERT OR IGNORE INTO settings (key, value) VALUES ('nisaab', 650000);
        ''')
        await db.commit()

async def update_nisaab_from_cbr():
    today = datetime.now()
    d2 = today.strftime("%d/%m/%Y")
    d1 = (today - timedelta(days=7)).strftime("%d/%m/%Y")
    url = f"https://www.cbr.ru/scripts/xml_metall.asp?date_req1={d1}&date_req2={d2}"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    root = ET.fromstring(text)
                    gold_records = [r for r in root.findall("Record") if r.get("Code") == "1"]
                    if gold_records:
                        last_record = gold_records[-1]
                        buy_price = float(last_record.find("Buy").text.replace(",", "."))
                        nisaab_value = round(buy_price * 84.8, 2)
                        
                        async with aiosqlite.connect(DB_NAME) as db:
                            await db.execute("UPDATE settings SET value = ? WHERE key = 'nisaab'", (nisaab_value,))
                            await db.commit()
                        print(f">>> Курс золота ЦБ: {buy_price} ₽/г. Нисаб: {nisaab_value:,.2f} ₽")
                        return nisaab_value
    except Exception as e:
        print(f">>> Ошибка при загрузке курса ЦБ: {e}")
    return await get_nisaab()

async def get_nisaab() -> float:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT value FROM settings WHERE key = 'nisaab'") as cursor:
            res = await cursor.fetchone()
            return res[0] if res else 650000.0

async def add_transaction(user_id: int, trans_type: str, category: str, amount: float):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO transactions (user_id, type, category, amount, date) VALUES (?, ?, ?, ?, datetime('now', 'localtime'))",
            (user_id, trans_type, category, amount)
        )
        await db.commit()

async def get_balance(user_id: int) -> float:
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT COALESCE(SUM(amount), 0.0) FROM transactions WHERE user_id = ? AND type = 'income'", 
            (user_id,)
        ) as cursor:
            income = (await cursor.fetchone())[0]

        async with db.execute(
            "SELECT COALESCE(SUM(amount), 0.0) FROM transactions WHERE user_id = ? AND type = 'expense'", 
            (user_id,)
        ) as cursor:
            expense = (await cursor.fetchone())[0]

        return round(income - expense, 2)

async def get_expenses_by_category(user_id: int, period: str = "month"):
    date_filter = ""
    if period == "day":
        date_filter = " AND date(date) = date('now', 'localtime')"
    elif period == "week":
        date_filter = " AND date(date) >= date('now', 'localtime', '-7 days')"
    elif period == "month":
        date_filter = " AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now', 'localtime')"

    query = f"""
        SELECT category, SUM(amount) as total 
        FROM transactions 
        WHERE user_id = ? AND type = 'expense' {date_filter}
        GROUP BY category 
        ORDER BY total DESC
    """
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [{"category": row["category"], "total": row["total"]} for row in rows]

async def get_transactions_history(user_id: int, period: str = "month", limit: int = 40):
    date_filter = ""
    if period == "day":
        date_filter = " AND date(date) = date('now', 'localtime')"
    elif period == "week":
        date_filter = " AND date(date) >= date('now', 'localtime', '-7 days')"
    elif period == "month":
        date_filter = " AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now', 'localtime')"

    query = f"""
        SELECT id, type, category, amount, strftime('%d.%m %H:%M', date) as formatted_date 
        FROM transactions 
        WHERE user_id = ? {date_filter}
        ORDER BY id DESC LIMIT ?
    """
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(query, (user_id, limit)) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "type": row["type"],
                    "category": row["category"],
                    "amount": row["amount"],
                    "date": row["formatted_date"]
                }
                for row in rows
            ]

async def delete_transaction(user_id: int, transaction_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM transactions WHERE id = ? AND user_id = ?",
            (transaction_id, user_id)
        )
        await db.commit()

async def reset_all_data(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM transactions WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM goals WHERE user_id = ?", (user_id,))
        await db.execute("DELETE FROM debts WHERE user_id = ?", (user_id,))
        await db.commit()

# --- Цели ---
async def create_goal(user_id: int, goal_name: str, target_amount: float):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO goals (user_id, goal_name, target_amount) VALUES (?, ?, ?)",
            (user_id, goal_name, target_amount)
        )
        await db.commit()

async def get_goals(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, goal_name, target_amount, current_amount FROM goals WHERE user_id = ?", 
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "id": row["id"],
                    "name": row["goal_name"],
                    "target": row["target_amount"],
                    "current": row["current_amount"]
                }
                for row in rows
            ]

async def add_money_to_goal(user_id: int, goal_id: int, goal_name: str, amount: float):
    async with aiosqlite.connect(DB_NAME) as db:
        # Списываем со свободного баланса
        await db.execute(
            "INSERT INTO transactions (user_id, type, category, amount, date) VALUES (?, ?, ?, ?, datetime('now', 'localtime'))",
            (user_id, "expense", f"Копилка: {goal_name}", amount)
        )
        # Начисляем в цель
        await db.execute(
            "UPDATE goals SET current_amount = current_amount + ? WHERE id = ? AND user_id = ?",
            (amount, goal_id, user_id)
        )
        await db.commit()

async def get_goal_progress(goal_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT target_amount, current_amount FROM goals WHERE id = ?", 
            (goal_id,)
        ) as cursor:
            return await cursor.fetchone()

async def finish_goal(goal_id: int, user_id: int = None):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        await db.commit()

# --- Долги ---
async def create_debt(user_id: int, creditor_name: str, amount: float, due_date: str):
    async with aiosqlite.connect(DB_NAME) as db:
        # Фиксируем долг в реестре долгов
        await db.execute(
            "INSERT INTO debts (user_id, creditor_name, amount, due_date) VALUES (?, ?, ?, ?)",
            (user_id, creditor_name, amount, due_date)
        )
        # Добавляем полученную сумму в свободный баланс как доход
        await db.execute(
            "INSERT INTO transactions (user_id, type, category, amount, date) VALUES (?, ?, ?, ?, datetime('now', 'localtime'))",
            (user_id, "income", f"Взято в долг: {creditor_name}", amount)
        )
        await db.commit()

async def get_debts(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, creditor_name, amount, paid_amount, due_date FROM debts WHERE user_id = ? AND paid_amount < amount",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            debts = []
            today = datetime.now().date()
            for r in rows:
                try:
                    d_date = datetime.strptime(r["due_date"], "%Y-%m-%d").date()
                    days_left = (d_date - today).days
                except Exception:
                    days_left = 0
                
                debts.append({
                    "id": r["id"],
                    "creditor_name": r["creditor_name"],
                    "amount": r["amount"],
                    "paid_amount": r["paid_amount"],
                    "due_date": r["due_date"],
                    "days_left": days_left
                })
            return debts

async def pay_debt(user_id: int, debt_id: int, creditor_name: str, amount: float):
    async with aiosqlite.connect(DB_NAME) as db:
        # Списываем возвращенные деньги с баланса
        await db.execute(
            "INSERT INTO transactions (user_id, type, category, amount, date) VALUES (?, ?, ?, ?, datetime('now', 'localtime'))",
            (user_id, "expense", f"Возврат долга: {creditor_name}", amount)
        )
        # Обновляем статус долга
        await db.execute(
            "UPDATE debts SET paid_amount = paid_amount + ? WHERE id = ? AND user_id = ?",
            (amount, debt_id, user_id)
        )
        await db.commit()

async def get_users_count():
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            async with db.execute("SELECT COUNT(DISTINCT user_id) FROM transactions") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception:
            return 0
