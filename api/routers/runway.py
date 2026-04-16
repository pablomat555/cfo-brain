"""
runway.py — API router для Runway Engine.

GET /runway — базовый сценарий
POST /runway/simulate — произвольный сценарий
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from loguru import logger

from core.database import get_db
from core.strategy_loader import load as load_strategy
from api.services.verdict_engine import ContextBuilder
from analytics.runway_engine import (
    BurnRateCalculator,
    RunwayEngine,
    ScenarioParams,
    RunwayResponse
)

router = APIRouter(prefix="/runway", tags=["runway"])


@router.get("", response_model=RunwayResponse)
def get_runway(db: Session = Depends(get_db)):
    """
    GET /runway — базовый сценарий (без изменений дохода/расходов).
    """
    # 1. Build context
    ctx = ContextBuilder.build(db)

    # Проверка: capital state пустой
    if ctx.liquid_total == 0:
        raise HTTPException(
            status_code=400,
            detail="Capital State не загружен. Используй /capital_add."
        )

    # 2. Load strategy
    strategy = load_strategy()

    # 3. Calculate burn stats
    try:
        burn_stats = BurnRateCalculator().calculate(db, months=3)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="Нет данных для расчёта. Загрузи CSV с указанием курса UAH."
        )

    # 4. Run simulation with default scenario
    scenario = ScenarioParams()
    result = RunwayEngine().simulate(ctx, burn_stats, strategy, scenario)

    logger.info(
        f"Runway GET: status={result.runway_status}, "
        f"delta={result.monthly_delta:.2f}, "
        f"capital={result.capital_snapshot:.2f}"
    )

    return result


@router.post("/simulate", response_model=RunwayResponse)
def simulate_runway(scenario: ScenarioParams, db: Session = Depends(get_db)):
    """
    POST /runway/simulate — симуляция с произвольными изменениями дохода/расходов.
    """
    # 1. Build context
    ctx = ContextBuilder.build(db)

    # Проверка: capital state пустой
    if ctx.liquid_total == 0:
        raise HTTPException(
            status_code=400,
            detail="Capital State не загружен. Используй /capital_add."
        )

    # 2. Load strategy
    strategy = load_strategy()

    # 3. Calculate burn stats с учётом months_history из сценария
    try:
        burn_stats = BurnRateCalculator().calculate(db, months=scenario.months_history)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail="Нет данных для расчёта. Загрузи CSV с указанием курса UAH."
        )

    # 4. Run simulation
    result = RunwayEngine().simulate(ctx, burn_stats, strategy, scenario)

    logger.info(
        f"Runway POST: status={result.runway_status}, "
        f"income_change={scenario.income_change:.2f}, "
        f"expense_change={scenario.expense_change:.2f}, "
        f"runway_months={result.runway_months}"
    )

    return result