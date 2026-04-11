from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional
from sqlalchemy import Column, Integer, Date, String, DateTime, Numeric, UniqueConstraint, Float
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel

Base = declarative_base()


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False)
    description = Column(String)
    amount = Column(Numeric(12, 2))  # Decimal with 2 decimal places
    currency = Column(String, default="UAH")
    category = Column(String, nullable=True)
    account = Column(String, nullable=True)
    source_file = Column(String)  # имя CSV из которого загружено
    created_at = Column(DateTime, default=datetime.utcnow)

    # Уникальный constraint для защиты от дублей
    __table_args__ = (
        UniqueConstraint("date", "amount", "account", "description", name="uq_transaction"),
    )

    def __repr__(self):
        return f"<Transaction(id={self.id}, date={self.date}, amount={self.amount}, currency={self.currency})>"


class PeriodReport(BaseModel):
    """Модель финансового отчёта за период"""
    total_income: float
    total_expenses: float
    net_savings: float
    savings_rate: float  # процент 0-100
    burn_rate: float  # сумма расходов в валюте
    by_category: Dict[str, float]
    by_account: Dict[str, float]
    top_expenses: List[Dict[str, Any]]
    month: datetime
    currency: str = "UAH"
    period_type: str = "custom"  # custom, this_month, previous_month
    ai_verdict: Optional[str] = None
    # Мультивалютные поля
    currency_breakdown: Optional[Dict[str, Dict[str, Any]]] = None
    rate: Optional[float] = None
    rate_type: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class UploadSession(Base):
    """Модель для хранения метаданных загрузки CSV файлов"""
    __tablename__ = "upload_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    min_date = Column(Date, nullable=False)
    max_date = Column(Date, nullable=False)
    transactions_count = Column(Integer, nullable=False)

    def __repr__(self):
        return f"<UploadSession(id={self.id}, uploaded_at={self.uploaded_at}, " \
               f"min_date={self.min_date}, max_date={self.max_date}, count={self.transactions_count})>"


# Observer Foundation Models (НАБЛЮДАТЕЛЬ)

class MonthlyMetrics(Base):
    """SQLAlchemy модель для таблицы monthly_metrics"""
    __tablename__ = "monthly_metrics"

    id = Column(Integer, primary_key=True)
    month_key = Column(String, nullable=False, unique=True)  # 'YYYY-MM'
    total_spent = Column(Float, nullable=False)  # всегда в USD
    total_income = Column(Float, nullable=False)  # всегда в USD
    savings_rate = Column(Float, nullable=False)  # (income - spent) / income
    burn_rate = Column(Float, nullable=False)  # total_spent в USD (по курсу ingest)
    currency = Column(String, nullable=False, default="USD")  # всегда 'USD'; 'multi' запрещён
    fx_rate = Column(Float, nullable=False)  # курс UAH/USD применённый при ingest (0.0 если /skip)
    rate_type = Column(String, nullable=False)  # 'manual' | 'skip'
    tx_count = Column(Integer, nullable=False)
    updated_at = Column(String, nullable=False)  # ISO datetime последнего пересчёта

    def __repr__(self):
        return f"<MonthlyMetrics(month_key={self.month_key}, total_spent={self.total_spent}, " \
               f"total_income={self.total_income}, savings_rate={self.savings_rate}%)>"


class CategoryMetrics(Base):
    """SQLAlchemy модель для таблицы category_metrics"""
    __tablename__ = "category_metrics"

    id = Column(Integer, primary_key=True)
    month_key = Column(String, nullable=False)  # FK → monthly_metrics.month_key
    category = Column(String, nullable=False)
    total = Column(Float, nullable=False)  # в USD (конвертировано по fx_rate месяца)
    tx_count = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("month_key", "category", name="uq_category_metrics"),
    )

    def __repr__(self):
        return f"<CategoryMetrics(month_key={self.month_key}, category={self.category}, " \
               f"total={self.total}, tx_count={self.tx_count})>"


class AnomalyEvent(Base):
    """SQLAlchemy модель для таблицы anomaly_events"""
    __tablename__ = "anomaly_events"

    id = Column(Integer, primary_key=True)
    month_key = Column(String, nullable=False)
    category = Column(String, nullable=False)
    current_val = Column(Float, nullable=False)  # в USD
    baseline_val = Column(Float, nullable=False)  # среднее за 3 предыдущих месяца, в USD
    delta_pct = Column(Float, nullable=False)  # (current - baseline) / baseline * 100
    threshold = Column(Float, nullable=False)  # порог срабатывания (default: 50%)
    status = Column(String, nullable=False)  # 'new' | 'notified' | 'dismissed'
    detected_at = Column(String, nullable=False)  # ISO datetime обнаружения

    def __repr__(self):
        return f"<AnomalyEvent(month_key={self.month_key}, category={self.category}, " \
               f"delta_pct={self.delta_pct}%, status={self.status})>"


# Pydantic модели для API responses

class MonthlyMetricsResponse(BaseModel):
    """Pydantic модель для ответа API с monthly_metrics"""
    month_key: str
    total_spent: float
    total_income: float
    savings_rate: float
    burn_rate: float
    currency: str = "USD"
    fx_rate: float
    rate_type: str
    tx_count: int
    updated_at: str

    class Config:
        from_attributes = True


class CategoryMetricsResponse(BaseModel):
    """Pydantic модель для ответа API с category_metrics"""
    month_key: str
    category: str
    total: float
    tx_count: int

    class Config:
        from_attributes = True


class AnomalyEventResponse(BaseModel):
    """Pydantic модель для ответа API с anomaly_events"""
    month_key: str
    category: str
    current_val: float
    baseline_val: float
    delta_pct: float
    threshold: float
    status: str
    detected_at: str

    class Config:
        from_attributes = True


# Capital Snapshot Models

class AccountBalance(Base):
    """SQLAlchemy модель для таблицы account_balances"""
    __tablename__ = "account_balances"

    id = Column(Integer, primary_key=True)
    account_name = Column(String, nullable=False)
    balance = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    fx_rate = Column(Float, nullable=False, default=1.0)
    bucket = Column(String, nullable=False)  # liquid, semi_liquid, investment
    as_of_date = Column(Date, nullable=False)
    source = Column(String, nullable=False, default="manual")  # manual, csv
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("account_name", "as_of_date", name="uq_account_balance"),
    )

    def __repr__(self):
        return f"<AccountBalance(account_name={self.account_name}, balance={self.balance}, " \
               f"currency={self.currency}, bucket={self.bucket}, as_of_date={self.as_of_date})>"


class PortfolioPosition(Base):
    """SQLAlchemy модель для таблицы portfolio_positions"""
    __tablename__ = "portfolio_positions"

    id = Column(Integer, primary_key=True)
    account_name = Column(String, nullable=False)
    asset_symbol = Column(String, nullable=False)
    asset_type = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    market_value = Column(Float, nullable=False)
    currency = Column(String, nullable=False)
    fx_rate = Column(Float, nullable=False, default=1.0)
    liquidity_bucket = Column(String, nullable=False)  # liquid, semi_liquid, investment
    as_of_date = Column(Date, nullable=False)
    source = Column(String, nullable=False, default="manual")  # manual, csv
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("account_name", "asset_symbol", "as_of_date", name="uq_portfolio_position"),
    )

    def __repr__(self):
        return f"<PortfolioPosition(account_name={self.account_name}, asset_symbol={self.asset_symbol}, " \
               f"market_value={self.market_value}, currency={self.currency}, as_of_date={self.as_of_date})>"


# Pydantic модели для Capital Snapshot API

class AccountBalanceCreate(BaseModel):
    """Pydantic модель для создания/обновления баланса счёта"""
    account_name: str
    balance: float
    currency: str
    fx_rate: float = 1.0
    bucket: str  # liquid, semi_liquid, investment
    as_of_date: str  # YYYY-MM-DD

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AccountBalanceResponse(BaseModel):
    """Pydantic модель для ответа API с балансом счёта"""
    id: int
    account_name: str
    balance: float
    currency: str
    fx_rate: float
    bucket: str
    as_of_date: str
    source: str
    created_at: str
    updated_at: str
    balance_usd: float  # вычисленное поле: balance * fx_rate

    class Config:
        from_attributes = True


class CapitalStateResponse(BaseModel):
    """Pydantic модель для ответа API с состоянием капитала"""
    as_of_date: str
    total_net_worth_usd: float
    by_bucket: Dict[str, Dict[str, Any]]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AccountListResponse(BaseModel):
    """Pydantic модель для ответа API со списком счетов"""
    accounts: List[str]


class CapitalSnapshotIngestResponse(BaseModel):
    """Pydantic модель для ответа API при загрузке снапшота"""
    rows_loaded: int
    snapshot_type: str  # account | portfolio
    as_of_date: str
    accounts: List[str]