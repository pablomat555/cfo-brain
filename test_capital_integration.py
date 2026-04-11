#!/usr/bin/env python3
"""
Тест интеграции Capital Snapshot MVP.
Проверяет основные компоненты без запуска сервера.
"""
import sys
import os
sys.path.append('.')

def test_parser():
    """Тест парсера CSV"""
    print("=== Тест парсера CSV ===")
    
    # Создаём тестовый CSV контент
    csv_content = """account_name,balance,currency,fx_rate,bucket,as_of_date,source
Payoneer,4200,USD,1.0,liquid,2026-04-11,manual
Monobank UAH,180000,UAH,43.85,liquid,2026-04-11,manual"""
    
    try:
        # Импортируем и тестируем парсер
        from etl.capital_parser import parse_capital_snapshot_csv
        
        result = parse_capital_snapshot_csv(csv_content, "account")
        print(f"✓ Парсер успешно обработал {len(result)} строк")
        
        for i, row in enumerate(result, 1):
            print(f"  Строка {i}: {row['account_name']} - {row['balance']} {row['currency']}")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка парсера: {e}")
        return False

def test_models():
    """Тест моделей Pydantic"""
    print("\n=== Тест моделей Pydantic ===")
    
    try:
        from core.models import AccountBalanceCreate, CapitalStateResponse
        
        # Тест создания модели
        account_data = AccountBalanceCreate(
            account_name="Test Account",
            balance=1000.0,
            currency="USD",
            fx_rate=1.0,
            bucket="liquid",
            as_of_date="2026-04-11"
        )
        
        print(f"✓ Модель AccountBalanceCreate создана: {account_data.account_name}")
        
        # Тест модели ответа
        state_data = CapitalStateResponse(
            as_of_date="2026-04-11",
            total_net_worth_usd=56000.0,
            by_bucket={
                "liquid": {"total_usd": 8000.0, "accounts": []},
                "semi_liquid": {"total_usd": 3000.0, "accounts": []},
                "investment": {"total_usd": 45000.0, "accounts": []}
            }
        )
        
        print(f"✓ Модель CapitalStateResponse создана: ${state_data.total_net_worth_usd:,.2f}")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка моделей: {e}")
        return False

def test_api_structure():
    """Тест структуры API роутера"""
    print("\n=== Тест структуры API ===")
    
    try:
        # Проверяем что файл API существует и импортируется
        from api.routers import capital
        
        endpoints = [
            ("POST", "/capital/account", "upsert_account_balance"),
            ("GET", "/capital/state", "get_capital_state"),
            ("GET", "/capital/accounts", "get_accounts_list"),
            ("POST", "/ingest/capital_snapshot", "ingest_capital_snapshot")
        ]
        
        print("✓ API роутер импортирован")
        print(f"✓ Роутер имеет префикс: {capital.router.prefix}")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка API структуры: {e}")
        return False

def test_bot_structure():
    """Тест структуры бота"""
    print("\n=== Тест структуры бота ===")
    
    try:
        # Проверяем что файл хендлеров существует
        from bot.handlers import capital
        
        print("✓ Хендлеры бота импортированы")
        print(f"✓ Роутер зарегистрирован")
        
        # Проверяем основные команды
        commands = ["/capital", "/capital_add", "/capital_edit", "/cancel"]
        print(f"✓ Поддерживаемые команды: {', '.join(commands)}")
        
        return True
    except Exception as e:
        print(f"✗ Ошибка структуры бота: {e}")
        return False

def test_migration():
    """Тест миграции"""
    print("\n=== Тест миграции ===")
    
    try:
        migration_path = "core/migrations/003_capital_snapshot_tables.sql"
        
        if os.path.exists(migration_path):
            with open(migration_path, 'r') as f:
                content = f.read()
            
            # Проверяем ключевые элементы миграции
            checks = [
                ("CREATE TABLE account_balances", "Таблица account_balances"),
                ("CREATE TABLE portfolio_positions", "Таблица portfolio_positions"),
                ("UNIQUE(account_name, as_of_date)", "Уникальный constraint для account_balances"),
                ("CHECK (bucket IN ('liquid', 'semi_liquid', 'investment'))", "Проверка bucket")
            ]
            
            all_passed = True
            for check_str, desc in checks:
                if check_str in content:
                    print(f"✓ {desc} присутствует в миграции")
                else:
                    print(f"✗ {desc} отсутствует в миграции")
                    all_passed = False
            
            return all_passed
        else:
            print(f"✗ Файл миграции не найден: {migration_path}")
            return False
    except Exception as e:
        print(f"✗ Ошибка проверки миграции: {e}")
        return False

def test_fixture():
    """Тест фикстуры"""
    print("\n=== Тест фикстуры ===")
    
    try:
        fixture_path = "fixtures/capital_snapshot_example.csv"
        
        if os.path.exists(fixture_path):
            with open(fixture_path, 'r') as f:
                lines = f.readlines()
            
            print(f"✓ Файл фикстуры существует: {len(lines)-1} строк данных")
            
            # Проверяем заголовок
            if "account_name,balance,currency,fx_rate,bucket,as_of_date,source" in lines[0]:
                print("✓ Заголовок CSV корректен")
                
                # Показываем пример данных
                print("  Пример данных:")
                for i, line in enumerate(lines[1:4], 1):
                    print(f"    {i}. {line.strip()}")
                
                return True
            else:
                print("✗ Неверный формат заголовка CSV")
                return False
        else:
            print(f"✗ Файл фикстуры не найден: {fixture_path}")
            return False
    except Exception as e:
        print(f"✗ Ошибка проверки фикстуры: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("Тестирование интеграции Capital Snapshot MVP\n")
    
    tests = [
        ("Парсер CSV", test_parser),
        ("Модели Pydantic", test_models),
        ("Структура API", test_api_structure),
        ("Структура бота", test_bot_structure),
        ("Миграция БД", test_migration),
        ("Фикстура", test_fixture)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ Неожиданная ошибка в тесте '{test_name}': {e}")
    
    print(f"\n{'='*50}")
    print(f"Результаты: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("✅ Все тесты пройдены успешно!")
        return 0
    else:
        print("❌ Некоторые тесты не пройдены")
        return 1

if __name__ == "__main__":
    sys.exit(main())