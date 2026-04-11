#!/usr/bin/env python3
"""Тест фильтрации Balancing transaction и внутренних переводов"""

import csv
import io
from etl.parser import parse_csv

# Создаем тестовый CSV с разными типами записей
test_csv = """Date,Description,Category,Payee,Tag,Account,Transfer Account,Amount
24 July 2024,,Balancing transaction,,,,Binance,40 000,00
20 March 2026,,,,,,Bybit*,Моно 8235,-1 000,00
20 March 2026,,,,,,Моно 8235,Bybit*,44 500,00
15 April 2026,Salary,Income,Company XYZ,,Bank Account,,3 800,00
16 April 2026,Groceries,Expense,Supermarket,,Bank Account,,-150,00"""

# Конвертируем в bytes
csv_bytes = test_csv.encode('utf-8')

# Парсим
transactions = parse_csv(csv_bytes, "test.csv")

print(f"Всего записей в CSV: 5")
print(f"Пропущено переводов: 2 (строки 2 и 3)")
print(f"Пропущено Balancing transaction: 1 (строка 1)")
print(f"Ожидается загруженных транзакций: 2 (строки 4 и 5)")
print(f"Фактически загружено: {len(transactions)}")

if len(transactions) == 2:
    print("✅ Тест пройден: фильтрация работает корректно")
    for t in transactions:
        print(f"  - {t.date.date()}: {t.description} ({t.category}), {t.amount} {t.currency}")
else:
    print(f"❌ Тест не пройден: ожидалось 2 транзакции, получено {len(transactions)}")
    for i, t in enumerate(transactions):
        print(f"  {i+1}. {t.date.date()}: {t.description} ({t.category})")