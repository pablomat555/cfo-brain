from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional
from sqlalchemy import Column, Integer, Date, String, DateTime, Numeric, UniqueConstraint
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
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }