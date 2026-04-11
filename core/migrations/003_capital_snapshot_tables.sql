-- Migration 003: Capital Snapshot Tables
-- Created: 2026-04-11
-- Purpose: Create tables for capital snapshot (account balances and portfolio positions)

-- Таблица балансов счетов
CREATE TABLE account_balances (
    id           INTEGER PRIMARY KEY,
    account_name TEXT NOT NULL,
    balance      REAL NOT NULL,
    currency     TEXT NOT NULL,
    fx_rate      REAL NOT NULL DEFAULT 1.0,
    bucket       TEXT NOT NULL CHECK (bucket IN ('liquid', 'semi_liquid', 'investment')),
    as_of_date   DATE NOT NULL,
    source       TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'csv')),
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_name, as_of_date)
);

-- Таблица позиций портфеля (структура, данные будут в Task #1B)
CREATE TABLE portfolio_positions (
    id               INTEGER PRIMARY KEY,
    account_name     TEXT NOT NULL,
    asset_symbol     TEXT NOT NULL,
    asset_type       TEXT NOT NULL,
    quantity         REAL NOT NULL,
    market_value     REAL NOT NULL,
    currency         TEXT NOT NULL,
    fx_rate          REAL NOT NULL DEFAULT 1.0,
    liquidity_bucket TEXT NOT NULL CHECK (liquidity_bucket IN ('liquid', 'semi_liquid', 'investment')),
    as_of_date       DATE NOT NULL,
    source           TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'csv')),
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_name, asset_symbol, as_of_date)
);

-- Индексы для производительности
CREATE INDEX idx_account_balances_date ON account_balances(as_of_date);
CREATE INDEX idx_account_balances_bucket ON account_balances(bucket);
CREATE INDEX idx_portfolio_positions_date ON portfolio_positions(as_of_date);
CREATE INDEX idx_portfolio_positions_bucket ON portfolio_positions(liquidity_bucket);

-- Триггер для обновления updated_at при изменении записи в account_balances
CREATE TRIGGER update_account_balances_timestamp 
AFTER UPDATE ON account_balances
BEGIN
    UPDATE account_balances 
    SET updated_at = CURRENT_TIMESTAMP 
    WHERE id = NEW.id;
END;