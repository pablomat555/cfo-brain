"""
verdict.py — API router для Verdict Engine.

POST /verdict — запрос вердикта по расходу.
"""

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from loguru import logger

from core.database import get_db
from core.models import MonthlyMetrics
from core.strategy_loader import load as load_strategy
from api.services.verdict_engine import (
    ContextBuilder, DecisionEngine, VerdictResponse, VerdictMeta
)

router = APIRouter(prefix="/verdict", tags=["verdict"])

# Fallback FX rate если manual rate недоступен
_FX_FALLBACK_RATE = 42.5


class VerdictRequest(BaseModel):
    """Запрос вердикта."""
    amount: float
    currency: str = "USD"
    category: str
    description: str = ""
    expense_type: str = "routine"   # routine | strategic | exceptional
    account: str | None = None


@router.post("", response_model=VerdictResponse)
def verdict(request: VerdictRequest, db: Session = Depends(get_db)):
    """
    POST /verdict — получить вердикт по расходу.

    Последовательность:
    1. FX normalization (UAH → USD)
    2. ContextBuilder.build(db)
    3. strategy_loader.load()
    4. DecisionEngine.decide()
    5. return VerdictResponse
    """
    # 1. FX normalization
    amount_usd = _normalize_currency(request.amount, request.currency, db)

    # 2. Build context
    ctx = ContextBuilder.build(db)

    # Проверка: capital state пустой
    if ctx.liquid_total == 0:
        raise HTTPException(
            status_code=400,
            detail="Capital State не загружен. Используй /capital_add."
        )

    # 3. Load strategy
    strategy = load_strategy()

    # 4. Decide
    result = DecisionEngine.decide(
        amount_usd=amount_usd,
        ctx=ctx,
        strategy=strategy,
        expense_type=request.expense_type
    )

    logger.info(
        f"Verdict: {result.decision} | amount=${amount_usd:.2f} | "
        f"category={request.category} | expense_type={request.expense_type} | "
        f"impact={result.impact_level}"
    )

    return result


def _normalize_currency(amount: float, currency: str, db: Session) -> float:
    """
    Нормализовать сумму в USD.

    Если currency == "UAH":
        берём последний monthly_metrics где rate_type == "manual"
        fx_rate = rate_row.fx_rate если есть, иначе fallback 42.5
        logger.warning если использован fallback
        amount_usd = amount / fx_rate
    Иначе:
        amount_usd = amount
    """
    if currency.upper() == "UAH":
        try:
            rate_row = db.query(MonthlyMetrics).filter(
                MonthlyMetrics.rate_type == "manual"
            ).order_by(
                MonthlyMetrics.month_key.desc()
            ).first()

            if rate_row and rate_row.fx_rate > 0:
                fx_rate = rate_row.fx_rate
                logger.debug(f"FX normalization: using manual rate {fx_rate}")
            else:
                fx_rate = _FX_FALLBACK_RATE
                logger.warning(
                    f"FX normalization: no manual rate found, using fallback {fx_rate}"
                )

            amount_usd = amount / fx_rate
            logger.info(f"FX normalization: {amount} UAH → {amount_usd:.2f} USD (rate={fx_rate})")
            return amount_usd

        except Exception as e:
            logger.error(f"FX normalization error: {e}, using fallback")
            amount_usd = amount / _FX_FALLBACK_RATE
            return amount_usd
    else:
        return amount
