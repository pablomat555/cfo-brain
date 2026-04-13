-- Migration 005: Add fx_rate and rate_type columns to upload_sessions table
-- Created: 13 апреля 2026, 19:24 (Kyiv)

-- Добавляем колонки fx_rate и rate_type в таблицу upload_sessions
ALTER TABLE upload_sessions ADD COLUMN fx_rate REAL NOT NULL DEFAULT 0.0;
ALTER TABLE upload_sessions ADD COLUMN rate_type TEXT NOT NULL DEFAULT 'skip' CHECK (rate_type IN ('manual', 'skip'));

-- Комментарий к колонкам
COMMENT ON COLUMN upload_sessions.fx_rate IS 'Курс UAH/USD применённый при загрузке (0.0 если /skip)';
COMMENT ON COLUMN upload_sessions.rate_type IS 'Тип курса: manual (пользовательский) или skip (пропущено)';