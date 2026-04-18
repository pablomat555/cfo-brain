"""
Asset classification for capital snapshot.
Rules loaded from config/classifier.yml (configurable).
"""

from typing import Tuple
from functools import lru_cache
import yaml
from pathlib import Path


@lru_cache(maxsize=1)
def _load_rules() -> dict:
    """
    Загружает правила классификации из config/classifier.yml.
    
    Результат кэшируется на весь lifecycle контейнера (lru_cache).
    Изменения в YAML вступают в силу только после рестарта контейнера.
    Это намеренное поведение — правила меняются только через git+deploy.
    """
    path = Path(__file__).parent.parent / "config" / "classifier.yml"
    with open(path) as f:
        return yaml.safe_load(f)


def classify_asset(symbol: str) -> Tuple[str, str]:
    """
    Classify asset symbol into asset_type and liquidity_bucket.

    Rules are loaded from config/classifier.yml.
    Matching order: exact → prefix → fallback.
    """
    rules = _load_rules()
    symbol_upper = symbol.strip().upper()

    # exact match по всем категориям (кроме prefix_rules и fallback)
    for category, rule in rules.items():
        if category in ("prefix_rules", "fallback"):
            continue
        if symbol_upper in [s.upper() for s in rule.get("symbols", [])]:
            return rule["asset_type"], rule["liquidity_bucket"]

    # prefix match
    for prefix_rule in rules.get("prefix_rules", []):
        if symbol_upper.startswith(prefix_rule["prefix"].upper()):
            return prefix_rule["asset_type"], prefix_rule["liquidity_bucket"]

    # fallback
    fb = rules["fallback"]
    return fb["asset_type"], fb["liquidity_bucket"]


# Quick test if run directly
if __name__ == "__main__":
    test_symbols = [
        "USDT", "BTC", "ETH", "SGOV", "VOO", "QQQ", "STEAM", "LOAN-USD", "LOAN-UAH",
        "CASH", "USD", "UAH", "UNKNOWN"
    ]
    for sym in test_symbols:
        asset_type, bucket = classify_asset(sym)
        print(f"{sym:15} -> {asset_type:15} {bucket}")