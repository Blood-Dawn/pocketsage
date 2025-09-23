from app.db import init_db, get_session
from app.models import Transaction, Habit, Liability
from datetime import datetime

def seed():
    init_db()
    with get_session() as s:
        s.add_all([
            Transaction(date=datetime.now(), amount=1200, category="Income", note="Paycheck", type="income"),
            Transaction(date=datetime.now(), amount=-45.5, category="Food", note="Groceries", type="expense"),
        ])
        s.add_all([Habit(name="No-spend day"), Habit(name="Pack lunch")])
        s.add_all([Liability(name="Credit Card", apr=24.99, balance=850.0, min_payment=35.0)])
        s.commit()
    print("Seeded demo data.")

if __name__ == "__main__":
    seed()
