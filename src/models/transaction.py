"""Transaction model for the budget tracker."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Transaction(SQLModel, table=True):
    """Transaction model representing a bank statement entry."""

    __tablename__ = "transactions"

    id: Optional[int] = Field(default=None, primary_key=True)

    # Date fields
    booking_date_time: datetime = Field(index=True)
    value_date_time: datetime

    # Order tracking within a day
    day_order_id: int = Field(default=0)

    # Bank statement data
    bank_statement_description: str
    stan_id: Optional[str] = Field(default=None, index=True)
    debit: Optional[float] = Field(default=None)
    credit: Optional[float] = Field(default=None)
    available_balance: float

    # Annotation fields (can be set via AI or manually)
    description: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None, index=True)
    originator_name: Optional[str] = Field(default=None)
    group_name: Optional[str] = Field(default=None)
    is_taxes: bool = Field(default=False, index=True)

    class Config:
        """Model configuration."""

        table_args = {"sqlite_autoincrement": True}
