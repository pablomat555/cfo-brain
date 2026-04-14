"""
verdict_engine.py — детерминированный Verdict Engine.

Трёхслойная архитектура:
1. ContextBuilder — читает capital state из БД (Single Source Rule D-30)
2. DecisionEngine — применяет одну из трёх политик (routine/strategic/exceptional)
3. VerdictResponse — стандартизированный ответ
"""

from datetime import date
from typing import Literal
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from loguru import logger

from core.models import (
    AccountBalance, PortfolioPosition, MonthlyMetrics
)
from core.strategy_loader import StrategyConfig


# ─────────────────────────────────────────────
# Response Models
# ─────────────────────────────────────────────

class VerdictMeta(BaseModel):
    """Метаданные вердикта."""
    liquid_before: float
    liquid_after: float
    last_updated: str
    policy_used: str
    expense_type: str


class VerdictResponse(BaseModel):
    """Ответ Verdict Engine."""
    decision: Literal["APPROVED", "APPROVED_WITH_IMPACT", "DENIED"]
    reason: str
    impact_level: Literal["NONE", "LOW", "MEDIUM", "HIGH"]
    capital_after: float       # liquid_total - amount
    liquidity_warning: bool    # capital_after < strategy.min_liquid_reserve
    meta: VerdictMeta


# ─────────────────────────────────────────────
# Context
# ─────────────────────────────────────────────

class CapitalContext(BaseModel):
    """Контекст капитала для принятия решения."""
    liquid_total: float
    semi_liquid_total: float
    investment_total: float
    total_net_worth: float
    last_updated: str          # ISO date
    burn_rate: float           # monthly expenses (abs)


class ContextBuilder:
    """
    Строит CapitalContext из БД.

    Single Source Rule (D-30): portfolio_positions приоритет над account_balances
    для одинакового account/date.
    """

    @classmethod
    def build(cls, db: Session) -> CapitalContext:
        """Построить контекст из БД."""
        # Находим последнюю дату snapshot
        max_date_balance = db.query(func.max(AccountBalance.as_of_date)).scalar()
        max_date_position = db.query(func.max(PortfolioPosition.as_of_date)).scalar()

        max_date = max(
            max_date_balance or date.min,
            max_date_position or date.min
        )

        if max_date == date.min:
            # Нет данных — возвращаем пустой контекст
            return CapitalContext(
                liquid_total=0.0,
                semi_liquid_total=0.0,
                investment_total=0.0,
                total_net_worth=0.0,
                last_updated="",
                burn_rate=0.0
            )

        # Получаем данные на последнюю дату
        balances = db.query(AccountBalance).filter(
            AccountBalance.as_of_date == max_date
        ).all()
        positions = db.query(PortfolioPosition).filter(
            PortfolioPosition.as_of_date == max_date
        ).all()

        # Single Source Rule: accounts с позициями исключаем из balances
        accounts_with_positions = {pos.account_name for pos in positions}

        liquid_total = 0.0
        semi_liquid_total = 0.0
        investment_total = 0.0

        # Суммируем позиции
        for pos in positions:
            value_usd = pos.market_value / pos.fx_rate if pos.fx_rate != 0 else 0.0
            bucket = pos.liquidity_bucket
            if bucket == "liquid":
                liquid_total += value_usd
            elif bucket == "semi_liquid":
                semi_liquid_total += value_usd
            elif bucket in ("investment", "illiquid"):
                investment_total += value_usd

        # Суммируем балансы (исключая accounts с позициями)
        for balance in balances:
            if balance.account_name in accounts_with_positions:
                continue
            value_usd = balance.balance / balance.fx_rate if balance.fx_rate != 0 else 0.0
            bucket = balance.bucket
            if bucket == "liquid":
                liquid_total += value_usd
            elif bucket == "semi_liquid":
                semi_liquid_total += value_usd
            elif bucket in ("investment", "illiquid"):
                investment_total += value_usd

        total_net_worth = liquid_total + semi_liquid_total + investment_total

        # Burn rate: последний monthly_metrics.total_expenses (abs)
        burn_rate = cls._get_burn_rate(db)

        last_updated = max_date.isoformat()

        logger.info(
            f"ContextBuilder: liquid={liquid_total:.2f}, semi_liquid={semi_liquid_total:.2f}, "
            f"investment={investment_total:.2f}, burn_rate={burn_rate:.2f}, date={last_updated}"
        )

        return CapitalContext(
            liquid_total=liquid_total,
            semi_liquid_total=semi_liquid_total,
            investment_total=investment_total,
            total_net_worth=total_net_worth,
            last_updated=last_updated,
            burn_rate=burn_rate
        )

    @staticmethod
    def _get_burn_rate(db: Session) -> float:
        """Получить последний burn_rate из monthly_metrics (abs)."""
        try:
            latest = db.query(MonthlyMetrics).order_by(
                MonthlyMetrics.month_key.desc()
            ).first()
            if latest:
                return abs(latest.total_spent)
        except Exception as e:
            logger.warning(f"ContextBuilder: failed to get burn_rate: {e}")
        return 0.0


# ─────────────────────────────────────────────
# Impact Calculation
# ─────────────────────────────────────────────

def calculate_impact(amount: float, liquid_total: float) -> Literal["NONE", "LOW", "MEDIUM", "HIGH"]:
    """
    Рассчитать impact level.

    ЗАЩИТА: если liquid_total == 0 → impact = "HIGH"
    иначе: ratio = amount / liquid_total
        < 5%   → LOW
        5–15%  → MEDIUM
        > 15%  → HIGH
    """
    if liquid_total == 0:
        return "HIGH"

    ratio = amount / liquid_total

    if ratio < 0.05:
        return "LOW"
    elif ratio <= 0.15:
        return "MEDIUM"
    else:
        return "HIGH"


def calculate_impact_pct(amount: float, liquid_total: float) -> float:
    """Рассчитать процент impact (amount / liquid_total * 100)."""
    if liquid_total == 0:
        return 100.0
    return (amount / liquid_total) * 100.0


# ─────────────────────────────────────────────
# Policies
# ─────────────────────────────────────────────

class RoutinePolicy:
    """
    RoutinePolicy: для routine расходов.

    if amount <= strategy.burn_rate_limit_usd:
        APPROVED, impact=NONE
    elif liquid_total >= amount:
        APPROVED_WITH_IMPACT
    else:
        DENIED
    """

    @classmethod
    def decide(
        cls,
        amount: float,
        ctx: CapitalContext,
        strategy: StrategyConfig
    ) -> VerdictResponse:
        liquid_after = ctx.liquid_total - amount

        if amount <= strategy.burn_rate_limit_usd:
            # В рамках burn rate — APPROVED без impact
            return VerdictResponse(
                decision="APPROVED",
                reason=f"Сумма ${amount:.0f} в рамках месячного лимита (${strategy.burn_rate_limit_usd:.0f})",
                impact_level="NONE",
                capital_after=liquid_after,
                liquidity_warning=liquid_after < strategy.min_liquid_reserve,
                meta=VerdictMeta(
                    liquid_before=ctx.liquid_total,
                    liquid_after=liquid_after,
                    last_updated=ctx.last_updated,
                    policy_used="RoutinePolicy",
                    expense_type="routine"
                )
            )
        elif ctx.liquid_total >= amount:
            # Превышает burn rate, но ликвидность есть
            impact = calculate_impact(amount, ctx.liquid_total)
            return VerdictResponse(
                decision="APPROVED_WITH_IMPACT",
                reason=f"Превышает месячный лимит (${strategy.burn_rate_limit_usd:.0f}), но ликвидность позволяет",
                impact_level=impact,
                capital_after=liquid_after,
                liquidity_warning=liquid_after < strategy.min_liquid_reserve,
                meta=VerdictMeta(
                    liquid_before=ctx.liquid_total,
                    liquid_after=liquid_after,
                    last_updated=ctx.last_updated,
                    policy_used="RoutinePolicy",
                    expense_type="routine"
                )
            )
        else:
            # Недостаточно ликвидности
            impact = calculate_impact(amount, ctx.liquid_total)
            return VerdictResponse(
                decision="DENIED",
                reason=f"Недостаточно ликвидности: ${ctx.liquid_total:.0f} < ${amount:.0f}",
                impact_level=impact,
                capital_after=liquid_after,
                liquidity_warning=True,
                meta=VerdictMeta(
                    liquid_before=ctx.liquid_total,
                    liquid_after=liquid_after,
                    last_updated=ctx.last_updated,
                    policy_used="RoutinePolicy",
                    expense_type="routine"
                )
            )


class StrategicPolicy:
    """
    StrategicPolicy: для strategic расходов (инвестиции, крупные покупки).

    liquid_after = liquid_total - amount
    if liquid_after >= strategy.min_liquid_reserve:
        APPROVED
    elif liquid_after >= strategy.payoneer_target_usd:
        APPROVED_WITH_IMPACT
    else:
        DENIED
    """

    @classmethod
    def decide(
        cls,
        amount: float,
        ctx: CapitalContext,
        strategy: StrategyConfig
    ) -> VerdictResponse:
        liquid_after = ctx.liquid_total - amount

        if liquid_after >= strategy.min_liquid_reserve:
            # После расхода остаётся выше минимального резерва
            impact = calculate_impact(amount, ctx.liquid_total)
            return VerdictResponse(
                decision="APPROVED",
                reason=f"Ликвидность после расхода (${liquid_after:.0f}) выше минимального резерва (${strategy.min_liquid_reserve:.0f})",
                impact_level=impact,
                capital_after=liquid_after,
                liquidity_warning=False,
                meta=VerdictMeta(
                    liquid_before=ctx.liquid_total,
                    liquid_after=liquid_after,
                    last_updated=ctx.last_updated,
                    policy_used="StrategicPolicy",
                    expense_type="strategic"
                )
            )
        elif liquid_after >= strategy.payoneer_target_usd:
            # После расхода остаётся выше payoneer target, но ниже min_liquid_reserve
            impact = calculate_impact(amount, ctx.liquid_total)
            return VerdictResponse(
                decision="APPROVED_WITH_IMPACT",
                reason=f"Ликвидность после расхода (${liquid_after:.0f}) ниже резерва (${strategy.min_liquid_reserve:.0f}), но выше payoneer target (${strategy.payoneer_target_usd:.0f})",
                impact_level=impact,
                capital_after=liquid_after,
                liquidity_warning=True,
                meta=VerdictMeta(
                    liquid_before=ctx.liquid_total,
                    liquid_after=liquid_after,
                    last_updated=ctx.last_updated,
                    policy_used="StrategicPolicy",
                    expense_type="strategic"
                )
            )
        else:
            # Недостаточно ликвидности
            impact = calculate_impact(amount, ctx.liquid_total)
            return VerdictResponse(
                decision="DENIED",
                reason=f"Ликвидность после расхода (${liquid_after:.0f}) ниже payoneer target (${strategy.payoneer_target_usd:.0f})",
                impact_level=impact,
                capital_after=liquid_after,
                liquidity_warning=True,
                meta=VerdictMeta(
                    liquid_before=ctx.liquid_total,
                    liquid_after=liquid_after,
                    last_updated=ctx.last_updated,
                    policy_used="StrategicPolicy",
                    expense_type="strategic"
                )
            )


class ExceptionalPolicy:
    """
    ExceptionalPolicy: для exceptional расходов (незапланированные).

    burn_rate НЕ применяется.

    if liquid_total >= amount:
        APPROVED_WITH_IMPACT
        # impact/reason определяются через thresholds (не decision):
        # amount <= exceptional_auto_approved_usd → impact=LOW,    reason="auto-approved exceptional"
        # amount <= exceptional_with_impact_usd  → impact=MEDIUM,  reason="exceptional spend"
        # amount >  exceptional_with_impact_usd  → impact=HIGH,    reason="track separately"
    else:
        DENIED
    """

    @classmethod
    def decide(
        cls,
        amount: float,
        ctx: CapitalContext,
        strategy: StrategyConfig
    ) -> VerdictResponse:
        liquid_after = ctx.liquid_total - amount

        if ctx.liquid_total >= amount:
            # Ликвидность есть — APPROVED_WITH_IMPACT
            # impact/reason определяются через thresholds
            if amount <= strategy.exceptional_auto_approved_usd:
                impact = "LOW"
                reason = f"auto-approved exceptional (до ${strategy.exceptional_auto_approved_usd:.0f})"
            elif amount <= strategy.exceptional_with_impact_usd:
                impact = "MEDIUM"
                reason = f"exceptional spend (${strategy.exceptional_auto_approved_usd:.0f}–${strategy.exceptional_with_impact_usd:.0f})"
            else:
                impact = "HIGH"
                reason = "track separately (крупный exceptional расход)"

            return VerdictResponse(
                decision="APPROVED_WITH_IMPACT",
                reason=reason,
                impact_level=impact,
                capital_after=liquid_after,
                liquidity_warning=liquid_after < strategy.min_liquid_reserve,
                meta=VerdictMeta(
                    liquid_before=ctx.liquid_total,
                    liquid_after=liquid_after,
                    last_updated=ctx.last_updated,
                    policy_used="ExceptionalPolicy",
                    expense_type="exceptional"
                )
            )
        else:
            # Недостаточно ликвидности
            impact = calculate_impact(amount, ctx.liquid_total)
            return VerdictResponse(
                decision="DENIED",
                reason=f"Недостаточно ликвидности: ${ctx.liquid_total:.0f} < ${amount:.0f}",
                impact_level=impact,
                capital_after=liquid_after,
                liquidity_warning=True,
                meta=VerdictMeta(
                    liquid_before=ctx.liquid_total,
                    liquid_after=liquid_after,
                    last_updated=ctx.last_updated,
                    policy_used="ExceptionalPolicy",
                    expense_type="exceptional"
                )
            )


# ─────────────────────────────────────────────
# DecisionEngine (Facade)
# ─────────────────────────────────────────────

class DecisionEngine:
    """
    Фасад для принятия решения.

    Выбирает политику на основе expense_type и применяет её.
    """

    @classmethod
    def decide(
        cls,
        amount_usd: float,
        ctx: CapitalContext,
        strategy: StrategyConfig,
        expense_type: str = "routine"
    ) -> VerdictResponse:
        """
        Принять решение.

        Args:
            amount_usd: сумма в USD (уже нормализованная)
            ctx: контекст капитала
            strategy: конфигурация стратегии
            expense_type: тип расхода (routine | strategic | exceptional)
        """
        if expense_type == "strategic":
            return StrategicPolicy.decide(amount_usd, ctx, strategy)
        elif expense_type == "exceptional":
            return ExceptionalPolicy.decide(amount_usd, ctx, strategy)
        else:
            # default — routine
            return RoutinePolicy.decide(amount_usd, ctx, strategy)
