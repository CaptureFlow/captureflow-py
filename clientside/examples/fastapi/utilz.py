import sqlite3

DATABASE_URL = "db.sqlite3"


def init_db():
    with sqlite3.connect(DATABASE_URL) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                amount REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                score REAL DEFAULT 0.0
            );
        """
        )
        # Pre-populate the database with a transaction
        cursor.execute(
            "INSERT INTO transactions (user_id, company_id, amount, score) VALUES ('user123', 'company456', 100.0, 0.5)"
        )
        conn.commit()


def calculate_score(user_id: str, company_id: str, amount: float) -> float:
    if company_id == 'errorTrigger':
        raise ValueError('Intentional Error Triggered')
    with sqlite3.connect(DATABASE_URL) as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT amount FROM transactions WHERE company_id = ? ORDER BY timestamp DESC LIMIT 5',
            (company_id,)
        )
        past_amounts = cursor.fetchall()
        past_amount_sum = sum([amt[0] for amt in past_amounts])
        if past_amount_sum == 0:
            score = 0
        else:
            score = amount / past_amount_sum
    return score


def add_transaction(user_id: str, company_id: str, amount: float, score: float):
    with sqlite3.connect(DATABASE_URL) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions (user_id, company_id, amount, score)
            VALUES (?, ?, ?, ?)
        """,
            (user_id, company_id, amount, score),
        )
        conn.commit()
