"""
strategy_loader.py — парсинг STRATEGY.md и извлечение конфигурационных параметров.

Читает STRATEGY.md один раз при старте, кеширует результат.
Каждое извлечение обёрнуто в try/except с fallback на default + logger.warning.
"""

import os
import re
from pathlib import Path
from typing import Any
from pydantic import BaseModel
from loguru import logger

# Путь к STRATEGY.md относительно корня проекта
_STRATEGY_PATH = Path(__file__).parent.parent / "STRATEGY.md"

# Глобальный кеш
_cached_config: "StrategyConfig | None" = None


class StrategyConfig(BaseModel):
    """Конфигурация стратегии, извлечённая из STRATEGY.md."""
    burn_rate_limit_usd: float = 1500.0
    payoneer_target_usd: float = 5000.0
    sgov_target_usd: float = 5000.0
    min_liquid_reserve: float = 10000.0       # payoneer + sgov, для StrategicPolicy
    monthly_investment_usd: float = 500.0
    emergency_fund_months: int = 3
    exceptional_auto_approved_usd: float = 100.0   # только для impact/reason
    exceptional_with_impact_usd: float = 500.0     # только для impact/reason


def _extract_float(pattern: str, text: str, default: float, field_name: str) -> float:
    """Извлечь float из текста по regex паттерну с fallback на default."""
    try:
        match = re.search(pattern, text)
        if match:
            value = float(match.group(1).replace(",", ""))
            logger.debug(f"strategy_loader: {field_name} = {value} (parsed)")
            return value
        else:
            logger.warning(f"strategy_loader: {field_name} not found in STRATEGY.md, using default {default}")
            return default
    except Exception as e:
        logger.warning(f"strategy_loader: failed to parse {field_name}: {e}, using default {default}")
        return default


def _extract_int(pattern: str, text: str, default: int, field_name: str) -> int:
    """Извлечь int из текста по regex паттерну с fallback на default."""
    try:
        match = re.search(pattern, text)
        if match:
            value = int(match.group(1))
            logger.debug(f"strategy_loader: {field_name} = {value} (parsed)")
            return value
        else:
            logger.warning(f"strategy_loader: {field_name} not found in STRATEGY.md, using default {default}")
            return default
    except Exception as e:
        logger.warning(f"strategy_loader: failed to parse {field_name}: {e}, using default {default}")
        return default


def _parse_strategy(text: str) -> StrategyConfig:
    """Парсинг STRATEGY.md и извлечение всех параметров."""
    config = StrategyConfig()

    # burn_rate_limit_usd: "$1,500" или "$1500" в секции OPERATIONAL LIMITS
    config.burn_rate_limit_usd = _extract_float(
        r"(?:Burn Rate|Месячный Лимит).*?\\$([\\d,]+)",
        text,
        default=config.burn_rate_limit_usd,
        field_name="burn_rate_limit_usd"
    )

    # payoneer_target_usd: "$5,000" в секции Эшелон 2
    config.payoneer_target_usd = _extract_float(
        r"Payoneer.*?Целевой баланс.*?\\$([\\d,]+)",
        text,
        default=config.payoneer_target_usd,
        field_name="payoneer_target_usd"
    )

    # sgov_target_usd: "$5,000" в секции Эшелон 3
    config.sgov_target_usd = _extract_float(
        r"SGOV.*?Целевой баланс.*?\\$([\\d,]+)",
        text,
        default=config.sgov_target_usd,
        field_name="sgov_target_usd"
    )

    # min_liquid_reserve = payoneer_target + sgov_target (по умолчанию $10k)
    config.min_liquid_reserve = config.payoneer_target_usd + config.sgov_target_usd
    logger.debug(f"strategy_loader: min_liquid_reserve = {config.min_liquid_reserve} (payoneer + sgov)")

    # monthly_investment_usd: "$500" в секции INVESTMENT PORTFOLIO
    config.monthly_investment_usd = _extract_float(
        r"Месячный взнос.*?\\$([\\d,]+)",
        text,
        default=config.monthly_investment_usd,
        field_name="monthly_investment_usd"
    )

    # emergency_fund_months: не парсится из файла, остаётся default = 3
    # (в STRATEGY.md нет явного указания на emergency fund months)

    # exceptional_auto_approved_usd: "До $100" в Exception Policy
    config.exceptional_auto_approved_usd = _extract_float(
        r"До\s+\\$([\\d,]+)\s*—\s*автоматически",
        text,
        default=config.exceptional_auto_approved_usd,
        field_name="exceptional_auto_approved_usd"
    )

    # exceptional_with_impact_usd: "$100-$500" в Exception Policy
    config.exceptional_with_impact_usd = _extract_float(
        r"\\$[\\d,]+-\\$([\\d,]+)\s*—\s*approved with impact",
        text,
        default=config.exceptional_with_impact_usd,
        field_name="exceptional_with_impact_usd"
    )

    # Парсинг CFO Rules блока (machine-readable)
    # Формат: key: value
    cfo_rules_section_match = re.search(r"## CFO Rules\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    if cfo_rules_section_match:
        cfo_text = cfo_rules_section_match.group(1)
        # Извлечение каждого параметра
        patterns = {
            "burn_rate_limit_usd": r"burn_rate_limit_usd:\s*([\d.]+)",
            "payoneer_target_usd": r"payoneer_target_usd:\s*([\d.]+)",
            "sgov_target_usd": r"sgov_target_usd:\s*([\d.]+)",
            "monthly_investment_usd": r"monthly_investment_usd:\s*([\d.]+)",
            "emergency_fund_months": r"emergency_fund_months:\s*([\d.]+)",
            "exceptional_auto_approved_usd": r"exceptional_auto_approved_usd:\s*([\d.]+)",
            "exceptional_with_impact_usd": r"exceptional_with_impact_usd:\s*([\d.]+)",
        }
        for field, pattern in patterns.items():
            match = re.search(pattern, cfo_text)
            if match:
                try:
                    value = float(match.group(1)) if field != "emergency_fund_months" else int(match.group(1))
                    setattr(config, field, value)
                    logger.debug(f"strategy_loader: {field} = {value} (from CFO Rules)")
                except Exception as e:
                    logger.warning(f"strategy_loader: failed to parse {field} from CFO Rules: {e}")
        # Пересчитываем min_liquid_reserve после возможного обновления payoneer_target_usd и sgov_target_usd
        config.min_liquid_reserve = config.payoneer_target_usd + config.sgov_target_usd
        logger.debug(f"strategy_loader: min_liquid_reserve updated = {config.min_liquid_reserve}")

    # Итоговая проверка: если ни одно значение не было распарсено (все остались default),
    # значит CFO Rules блок отсутствует или формат изменился
    parsed_count = sum(1 for v in [
        config.burn_rate_limit_usd, config.payoneer_target_usd, config.sgov_target_usd,
        config.monthly_investment_usd, config.emergency_fund_months,
        config.exceptional_auto_approved_usd, config.exceptional_with_impact_usd
    ] if v is not None)

    if parsed_count == 0:
        logger.warning("StrategyConfig: CFO Rules block not found in STRATEGY.md — using defaults. Update STRATEGY.md.")

    return config


def load(force: bool = False) -> StrategyConfig:
    """
    Загрузить StrategyConfig из STRATEGY.md.
    Кеширует результат при первом вызове.
    force=True — перечитать файл (для тестов).
    """
    global _cached_config

    if _cached_config is not None and not force:
        return _cached_config

    try:
        strategy_path = _STRATEGY_PATH
        if not strategy_path.exists():
            logger.warning(f"strategy_loader: STRATEGY.md not found at {strategy_path}, using defaults")
            _cached_config = StrategyConfig()
            return _cached_config

        text = strategy_path.read_text(encoding="utf-8")
        _cached_config = _parse_strategy(text)
        logger.info(f"strategy_loader: loaded config from STRATEGY.md")
        return _cached_config

    except Exception as e:
        logger.error(f"strategy_loader: failed to load STRATEGY.md: {e}, using defaults")
        _cached_config = StrategyConfig()
        return _cached_config


def reset_cache() -> None:
    """Сбросить кеш (для тестов)."""
    global _cached_config
    _cached_config = None
