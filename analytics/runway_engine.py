"""
runway_engine.py — Burn Rate Calculator + Runway Simulation Engine.

Использует:
- ContextBuilder из api/services/verdict_engine.py — liquid_total, last_updated
- StrategyConfig из core/strategy_loader.py — burn_rate_limit_usd, emergency_fund_months
- MonthlyMetrics из core.models — только rate_type="manual"
"""

from typing import Literal
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from loguru import logger

from core.models import MonthlyMetrics
from api.services.verdict_engine import ContextBuilder, CapitalContext
from core.strategy_loader import StrategyConfig, load as load_strategy


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class BurnRateStats(BaseModel):
    avg_burn: float
    avg_income: float
    avg_savings_rate: float
    burn_trend: Literal["stable", "growing", "declining"]
    months_used: int
    rate_type_filter: str  # всегда "manual"


class ScenarioParams(BaseModel):
    income_change: float = 0.0    # -0.3 = -30% к доходу
    expense_change: float = 0.0   # +0.2 = +20% к расходам
    months_history: int = 3       # за сколько месяцев считать avg


class RunwayResponse(BaseModel):
    runway_status: Literal["self_sustaining", "depleting"]
    runway_months: int | None                # None если self_sustaining
    runway_months_liquid_zero: int | None    # None если self_sustaining
    monthly_delta: float                     # adjusted_income - adjusted_burn
    burn_rate_avg: float
    income_avg: float
    savings_rate_avg: float
    burn_trend: str
    emergency_floor: float                   # burn_rate_limit * emergency_fund_months
    scenario: ScenarioParams
    capital_snapshot: float                  # текущий liquid_total
    as_of: str                               # дата последнего capital snapshot
    warning: str | None                      # если runway_months < 6 → предупреждение


# ─────────────────────────────────────────────
# BurnRateCalculator
# ─────────────────────────────────────────────

class BurnRateCalculator:
    """
    Рассчитывает средние burn rate, income, savings rate за последние N месяцев,
    только для записей с rate_type="manual".
    """

    def calculate(self, db: Session, months: int = 3) -> BurnRateStats:
        """
        Читает monthly_metrics, фильтрует по rate_type="manual",
        сортирует по month_key DESC, берёт первые N записей.
        """
        # Запрос с фильтром
        query = db.query(MonthlyMetrics).filter(
            MonthlyMetrics.rate_type == "manual"
        ).order_by(desc(MonthlyMetrics.month_key))

        records = query.limit(months).all()

        if not records:
            raise ValueError("No manual-rate months available")

        # Разделяем для тренда (первая половина vs вторая половина)
        half = len(records) // 2
        first_half = records[half:]  # более старые
        second_half = records[:half]  # более новые

        avg_burn = sum(r.total_spent for r in records) / len(records)
        avg_income = sum(r.total_income for r in records) / len(records)
        avg_savings_rate = sum(r.savings_rate for r in records) / len(records)

        # Тренд burn rate
        if half >= 1:
            burn_first = sum(r.total_spent for r in first_half) / len(first_half)
            burn_second = sum(r.total_spent for r in second_half) / len(second_half)
            if burn_first == 0:
                trend = "stable"
            else:
                change_pct = (burn_second - burn_first) / abs(burn_first)
                if change_pct > 0.1:
                    trend = "growing"
                elif change_pct < -0.1:
                    trend = "declining"
                else:
                    trend = "stable"
        else:
            trend = "stable"

        return BurnRateStats(
            avg_burn=abs(avg_burn),  # burn rate всегда положительный
            avg_income=avg_income,
            avg_savings_rate=avg_savings_rate,
            burn_trend=trend,
            months_used=len(records),
            rate_type_filter="manual"
        )


# ─────────────────────────────────────────────
# RunwayEngine
# ─────────────────────────────────────────────

class RunwayEngine:
    """
    Симулирует runway (сколько месяцев протянет liquid капитал)
    на основе текущего капитала и скорректированного cash flow.
    """

    def simulate(
        self,
        ctx: CapitalContext,
        burn_stats: BurnRateStats,
        strategy: StrategyConfig,
        scenario: ScenarioParams
    ) -> RunwayResponse:
        """
        Выполняет симуляцию runway.
        """
        # Корректируем burn и income по сценарию
        adjusted_burn = burn_stats.avg_burn * (1 + scenario.expense_change)
        adjusted_income = burn_stats.avg_income * (1 + scenario.income_change)
        monthly_delta = adjusted_income - adjusted_burn
        emergency_floor = strategy.burn_rate_limit_usd * strategy.emergency_fund_months

        # Правило: если monthly_delta >= 0 → self_sustaining
        if monthly_delta >= 0:
            return RunwayResponse(
                runway_status="self_sustaining",
                runway_months=None,
                runway_months_liquid_zero=None,
                monthly_delta=monthly_delta,
                burn_rate_avg=burn_stats.avg_burn,
                income_avg=burn_stats.avg_income,
                savings_rate_avg=burn_stats.avg_savings_rate,
                burn_trend=burn_stats.burn_trend,
                emergency_floor=emergency_floor,
                scenario=scenario,
                capital_snapshot=ctx.liquid_total,
                as_of=ctx.last_updated,
                warning=None
            )

        # Симуляция помесячно (макс 120 месяцев = 10 лет)
        balance = ctx.liquid_total
        months_to_floor = None
        months_to_zero = None
        for i in range(1, 121):
            balance += monthly_delta
            if months_to_floor is None and balance <= emergency_floor:
                months_to_floor = i
            if months_to_zero is None and balance <= 0:
                months_to_zero = i
                break

        warning = None
        if months_to_floor is not None and months_to_floor < 6:
            warning = f"⚠️ Runway критически мал: {months_to_floor} мес до emergency floor"

        return RunwayResponse(
            runway_status="depleting",
            runway_months=months_to_floor,
            runway_months_liquid_zero=months_to_zero,
            monthly_delta=monthly_delta,
            burn_rate_avg=burn_stats.avg_burn,
            income_avg=burn_stats.avg_income,
            savings_rate_avg=burn_stats.avg_savings_rate,
            burn_trend=burn_stats.burn_trend,
            emergency_floor=emergency_floor,
            scenario=scenario,
            capital_snapshot=ctx.liquid_total,
            as_of=ctx.last_updated,
            warning=warning
        )