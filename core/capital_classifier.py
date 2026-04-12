"""
Asset classification for capital snapshot.
Rules are hardcoded per D-30/D-31 and TASK #1B.
"""

from typing import Tuple


def classify_asset(symbol: str) -> Tuple[str, str]:
    """
    Classify asset symbol into asset_type and liquidity_bucket.

    Parameters
    ----------
    symbol : str
        Asset symbol (case-insensitive, e.g., 'USDT', 'BTC', 'VOO').

    Returns
    -------
    Tuple[str, str]
        (asset_type, liquidity_bucket)

    Rules (hardcoded):
    - USDT / Trust Wallet USDT → stablecoin → liquid
    - Crypto (BTC, ETH, LTC...) → crypto → semi_liquid
    - SGOV → bond_etf → semi_liquid
    - ETF (VOO, QQQ, VXUS) → etf → investment
    - Steam → alternative → semi_liquid
    - Loans → receivable → illiquid
    - Cash USD/UAH → cash → liquid
    """
    symbol_upper = symbol.strip().upper()

    # Stablecoin
    if symbol_upper in ("USDT", "USDT-TRUST"):
        return "stablecoin", "liquid"

    # Crypto
    crypto_symbols = {
        "BTC", "ETH", "LTC", "XRP", "ADA", "DOT", "SOL", "BNB", "DOGE", "SHIB",
        "MATIC", "AVAX", "ATOM", "LINK", "UNI", "AAVE", "ALGO", "XTZ", "XLM",
        "VET", "TRX", "ETC", "BCH", "BSV", "EOS", "XMR", "ZEC", "DASH", "NEO",
    }
    if symbol_upper in crypto_symbols:
        return "crypto", "semi_liquid"

    # Bond ETF
    if symbol_upper == "SGOV":
        return "bond_etf", "semi_liquid"

    # ETFs
    etf_symbols = {"VOO", "QQQ", "VXUS", "VTI", "SPY", "IVV", "IWM", "EFA", "EEM"}
    if symbol_upper in etf_symbols:
        return "etf", "investment"

    # Alternative (Steam)
    if symbol_upper == "STEAM":
        return "alternative", "semi_liquid"

    # Loans (receivable)
    if symbol_upper.startswith("LOAN"):
        return "receivable", "illiquid"

    # Cash
    if symbol_upper in ("CASH", "USD", "UAH", "EUR", "GBP"):
        return "cash", "liquid"

    # Default fallback (treat as crypto-like)
    return "crypto", "semi_liquid"


# Quick test if run directly
if __name__ == "__main__":
    test_symbols = [
        "USDT", "BTC", "ETH", "SGOV", "VOO", "QQQ", "STEAM", "LOAN-USD", "LOAN-UAH",
        "CASH", "USD", "UAH", "UNKNOWN"
    ]
    for sym in test_symbols:
        asset_type, bucket = classify_asset(sym)
        print(f"{sym:15} -> {asset_type:15} {bucket}")