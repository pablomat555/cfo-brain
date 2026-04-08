-- Migration 002: Observer Foundation Tables
-- Created: 2026-04-08
-- Purpose: Create tables for НАБЛЮДАТЕЛЬ metrics storage

-- Агрегаты по месяцу (один ряд на месяц)
CREATE TABLE monthly_metrics (
    id           INTEGER PRIMARY KEY,
    month_key    TEXT NOT NULL UNIQUE,  -- 'YYYY-MM'
    total_spent  REAL NOT NULL,         -- всегда в USD
    total_income REAL NOT NULL,         -- всегда в USD
    savings_rate REAL NOT NULL,         -- (income - spent) / income
    burn_rate    REAL NOT NULL,         -- total_spent в USD (по курсу ingest)
    currency     TEXT NOT NULL DEFAULT 'USD',  -- всегда 'USD'; 'multi' запрещён
    fx_rate      REAL NOT NULL,         -- курс UAH/USD применённый при ingest (0.0 если /skip)
    rate_type    TEXT NOT NULL,         -- 'manual' | 'skip'
    tx_count     INTEGER NOT NULL,
    updated_at   TEXT NOT NULL          -- ISO datetime последнего пересчёта
);

-- Агрегаты по категории внутри месяца
CREATE TABLE category_metrics (
    id           INTEGER PRIMARY KEY,
    month_key    TEXT NOT NULL,         -- FK → monthly_metrics.month_key
    category     TEXT NOT NULL,
    total        REAL NOT NULL,         -- в USD (конвертировано по fx_rate месяца)
    tx_count     INTEGER NOT NULL,
    UNIQUE(month_key, category)
);

-- Зафиксированные аномалии
CREATE TABLE anomaly_events (
    id           INTEGER PRIMARY KEY,
    month_key    TEXT NOT NULL,
    category     TEXT NOT NULL,
    current_val  REAL NOT NULL,         -- в USD
    baseline_val REAL NOT NULL,         -- среднее за 3 предыдущих месяца, в USD
    delta_pct    REAL NOT NULL,         -- (current - baseline) / baseline * 100
    threshold    REAL NOT NULL,         -- порог срабатывания (default: 50%)
    status       TEXT NOT NULL,         -- 'new' | 'notified' | 'dismissed'
    detected_at  TEXT NOT NULL
);

-- Индексы для производительности
CREATE INDEX idx_category_metrics_month ON category_metrics(month_key);
CREATE INDEX idx_anomaly_events_month   ON anomaly_events(month_key);
CREATE INDEX idx_anomaly_events_status  ON anomaly_events(status);

-- Примечание: FX consistency rule (критично):
-- Все суммы в monthly_metrics и category_metrics хранятся в USD
-- Конвертация происходит один раз — в момент ingest, по курсу введённому пользователем
-- fx_rate фиксируется вместе с метриками — исторические данные не пересчитываются никогда
-- При /skip: fx_rate = 0.0, rate_type = 'skip' — метрики не сопоставимы с USD-периодами,
-- аномалия детекция для таких месяцев отключена (detection_status = 'skip_mode')