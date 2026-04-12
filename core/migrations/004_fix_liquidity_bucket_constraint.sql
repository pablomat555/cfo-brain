-- Migration 004: Fix liquidity_bucket constraint to include 'illiquid'
-- Created: 2026-04-12
-- Purpose: Add 'illiquid' to CHECK constraint on portfolio_positions.liquidity_bucket
--          (required for Loans receivable per D-31)

-- SQLite does not support ALTER TABLE to modify CHECK constraints.
-- We need to recreate the table with the new constraint.

-- Step 1: Create new table with updated constraint
CREATE TABLE portfolio_positions_new (
    id               INTEGER PRIMARY KEY,
    account_name     TEXT NOT NULL,
    asset_symbol     TEXT NOT NULL,
    asset_type       TEXT NOT NULL,
    quantity         REAL NOT NULL,
    market_value     REAL NOT NULL,
    currency         TEXT NOT NULL,
    fx_rate          REAL NOT NULL DEFAULT 1.0,
    liquidity_bucket TEXT NOT NULL CHECK (liquidity_bucket IN ('liquid', 'semi_liquid', 'investment', 'illiquid')),
    as_of_date       DATE NOT NULL,
    source           TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'csv')),
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_name, asset_symbol, as_of_date)
);

-- Step 2: Copy existing data (if any)
INSERT INTO portfolio_positions_new 
SELECT * FROM portfolio_positions;

-- Step 3: Drop old table
DROP TABLE portfolio_positions;

-- Step 4: Rename new table to original name
ALTER TABLE portfolio_positions_new RENAME TO portfolio_positions;

-- Step 5: Recreate indexes
CREATE INDEX idx_portfolio_positions_date ON portfolio_positions(as_of_date);
CREATE INDEX idx_portfolio_positions_bucket ON portfolio_positions(liquidity_bucket);

-- Note: No need to recreate trigger because portfolio_positions doesn't have an updated_at column.