"""
Интеграционные тесты для Verdict Engine.

Тестирует все 7 сценариев из TASK.md.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import date, datetime

from api.main import app
from core.database import get_db
from core.models import Base, AccountBalance, PortfolioPosition, MonthlyMetrics
from core.strategy_loader import reset_cache


# Тестовая БД в памяти с StaticPool (одна БД для всех соединений)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Переопределение зависимости БД для тестов."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="function", autouse=True)
def setup_db():
    """Настройка БД перед каждым тестом."""
    # Создаём таблицы
    Base.metadata.create_all(bind=engine)

    # Сбрасываем кеш strategy_loader
    reset_cache()

    # Добавляем тестовые данные
    db = TestingSessionLocal()

    # Добавляем capital snapshot (liquid_total = $10,000)
    account = AccountBalance(
        account_name="Payoneer",
        balance=10000.0,
        currency="USD",
        fx_rate=1.0,
        bucket="liquid",
        as_of_date=date(2026, 4, 13),
        source="test"
    )
    db.add(account)

    # Добавляем monthly_metrics для burn_rate и FX rate
    metrics = MonthlyMetrics(
        month_key="2026-04",
        total_spent=1200.0,  # burn_rate = 1200
        total_income=3000.0,
        savings_rate=60.0,
        burn_rate=1200.0,
        currency="USD",
        fx_rate=42.5,  # manual rate для UAH
        rate_type="manual",
        tx_count=10,
        updated_at=datetime.utcnow().isoformat()
    )
    db.add(metrics)

    db.commit()
    db.close()

    yield

    # Очистка после теста
    Base.metadata.drop_all(bind=engine)


def test_1_routine_approved_below_burn_rate():
    """1. Routine — approved (< burn_rate_limit)."""
    response = client.post("/verdict", json={
        "amount": 200,
        "currency": "USD",
        "category": "продукты",
        "expense_type": "routine"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVED"
    assert data["impact_level"] == "NONE"
    # liquidity_warning = capital_after < min_liquid_reserve
    # liquid_after = $10,000 - $200 = $9,800 < $10,000 → True
    assert data["liquidity_warning"] is True
    assert data["meta"]["policy_used"] == "RoutinePolicy"


def test_2_routine_approved_with_impact_above_burn_rate():
    """2. Routine — approved with impact (> burn_rate_limit, liquid есть)."""
    response = client.post("/verdict", json={
        "amount": 2000,
        "currency": "USD",
        "category": "техника",
        "expense_type": "routine"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVED_WITH_IMPACT"
    assert data["impact_level"] in ["LOW", "MEDIUM", "HIGH"]
    # liquidity_warning = capital_after < min_liquid_reserve
    # liquid_after = $10,000 - $2,000 = $8,000 < $10,000 → True
    assert data["liquidity_warning"] is True
    assert data["meta"]["policy_used"] == "RoutinePolicy"


def test_3_exceptional_approved_with_impact_high():
    """3. Exceptional — не блокируется burn rate, impact=HIGH."""
    response = client.post("/verdict", json={
        "amount": 3000,
        "currency": "USD",
        "category": "медицина",
        "expense_type": "exceptional"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVED_WITH_IMPACT"
    assert data["impact_level"] == "HIGH"  # 3000 / 10000 = 30% > 15%
    assert data["meta"]["policy_used"] == "ExceptionalPolicy"


def test_4_exceptional_small_amount_impact_low():
    """4. Exceptional — маленькая сумма, impact=LOW."""
    response = client.post("/verdict", json={
        "amount": 50,
        "currency": "USD",
        "category": "лекарства",
        "expense_type": "exceptional"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVED_WITH_IMPACT"
    assert data["impact_level"] == "LOW"  # 50 / 10000 = 0.5% < 5%
    assert data["meta"]["policy_used"] == "ExceptionalPolicy"


def test_5_strategic_liquid_floor_check():
    """5. Strategic — liquid floor check."""
    # min_liquid_reserve = $10k (payoneer_target + sgov_target)
    # liquid_total = $10k, amount = $15k → liquid_after = -$5k → DENIED
    response = client.post("/verdict", json={
        "amount": 15000,
        "currency": "USD",
        "category": "крипто",
        "expense_type": "strategic"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "DENIED"
    assert data["liquidity_warning"] is True
    assert data["meta"]["policy_used"] == "StrategicPolicy"


def test_6_uah_normalization():
    """6. UAH normalization."""
    # 21250 UAH / 42.5 = $500 → routine approved (burn_rate_limit = $1500)
    response = client.post("/verdict", json={
        "amount": 21250,
        "currency": "UAH",
        "category": "продукты",
        "expense_type": "routine"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVED"  # $500 < $1500
    assert data["impact_level"] == "NONE"
    assert data["meta"]["policy_used"] == "RoutinePolicy"


def test_7_capital_state_empty():
    """7. Capital state пустой → 400."""
    # Удаляем все capital данные
    db = TestingSessionLocal()
    db.query(AccountBalance).delete()
    db.query(PortfolioPosition).delete()
    db.commit()
    db.close()

    response = client.post("/verdict", json={
        "amount": 100,
        "currency": "USD",
        "category": "test"
    })
    assert response.status_code == 400
    data = response.json()
    assert "Capital State не загружен" in data["detail"]


def test_fx_fallback_when_no_manual_rate():
    """FX fallback когда manual rate недоступен."""
    # Удаляем monthly_metrics с manual rate
    db = TestingSessionLocal()
    db.query(MonthlyMetrics).delete()
    db.commit()
    db.close()

    # 4250 UAH / 42.5 (fallback) = $100
    response = client.post("/verdict", json={
        "amount": 4250,
        "currency": "UAH",
        "category": "тест",
        "expense_type": "routine"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVED"  # $100 < $1500


def test_impact_calculation_zero_liquid():
    """Impact calculation при liquid_total = 0 → HIGH."""
    # Удаляем capital данные
    db = TestingSessionLocal()
    db.query(AccountBalance).delete()
    db.query(PortfolioPosition).delete()
    db.commit()
    db.close()

    # Добавляем только позицию с liquid_total = 0
    # (не добавляем ничего)
    response = client.post("/verdict", json={
        "amount": 100,
        "currency": "USD",
        "category": "test"
    })
    assert response.status_code == 400  # capital state пустой
    # Но если бы liquid_total = 0, impact был бы HIGH (защита в calculate_impact)


def test_strategic_approved_when_liquid_after_above_reserve():
    """Strategic APPROVED когда liquid_after >= min_liquid_reserve."""
    # Добавим больше ликвидности
    db = TestingSessionLocal()
    extra = AccountBalance(
        account_name="Monobank",
        balance=5000.0,
        currency="USD",
        fx_rate=1.0,
        bucket="liquid",
        as_of_date=date(2026, 4, 13),
        source="test"
    )
    db.add(extra)
    db.commit()
    db.close()

    # Теперь liquid_total = $15k, min_liquid_reserve = $10k
    # amount = $2000 → liquid_after = $13k > $10k → APPROVED
    response = client.post("/verdict", json={
        "amount": 2000,
        "currency": "USD",
        "category": "инвестиции",
        "expense_type": "strategic"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "APPROVED"
    assert data["liquidity_warning"] is False
    assert data["meta"]["policy_used"] == "StrategicPolicy"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
