#!/usr/bin/env python3
"""Упрощённый тест логики фильтрации"""

# Имитируем логику из etl/parser.py для проверки фильтрации

def test_filtering_logic():
    print("Тестирование логики фильтрации:")
    print("=" * 50)
    
    # Тестовые данные
    test_rows = [
        {"Category": "Balancing transaction", "Transfer Account": "", "Account": "Binance", "Amount": "40 000,00"},
        {"Category": "", "Transfer Account": "Моно 8235", "Account": "Bybit*", "Amount": "-1 000,00"},
        {"Category": "", "Transfer Account": "Bybit*", "Account": "Моно 8235", "Amount": "44 500,00"},
        {"Category": "Income", "Transfer Account": "", "Account": "Bank Account", "Amount": "3 800,00"},
        {"Category": "Expense", "Transfer Account": "", "Account": "Bank Account", "Amount": "-150,00"},
    ]
    
    expected_skipped = 3  # 1 Balancing + 2 transfers
    expected_passed = 2   # 2 обычные транзакции
    
    skipped_balancing = 0
    skipped_transfers = 0
    passed = 0
    
    for i, row in enumerate(test_rows, 1):
        category = row.get("Category", "").strip() or None
        transfer_account = row.get("Transfer Account", "").strip()
        is_transfer = bool(transfer_account)
        
        # Правило 1: Пропускать переводы
        if is_transfer:
            print(f"Row {i}: transfer transaction (from {row['Account']} to {transfer_account}), skipping")
            skipped_transfers += 1
            continue
            
        # Правило 2: Пропускать Balancing transaction
        if category == "Balancing transaction":
            print(f"Row {i}: Balancing transaction, skipping")
            skipped_balancing += 1
            continue
            
        # Если дошли сюда - транзакция проходит
        print(f"Row {i}: passed - {category} ({row['Amount']})")
        passed += 1
    
    print("=" * 50)
    print(f"Итого:")
    print(f"  - Пропущено Balancing transaction: {skipped_balancing}")
    print(f"  - Пропущено переводов: {skipped_transfers}")
    print(f"  - Прошло транзакций: {passed}")
    
    if skipped_balancing == 1 and skipped_transfers == 2 and passed == 2:
        print("✅ Тест пройден: логика фильтрации работает корректно")
        return True
    else:
        print("❌ Тест не пройден")
        return False

if __name__ == "__main__":
    test_filtering_logic()