"""Service for financial analytics and reporting."""

import calendar
import statistics
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

from sqlmodel import and_, select

from src.database import get_session
from src.models import Transaction


class AnalyticsService:
    """Service for financial analytics and reporting."""

    def get_total_expenditure(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> float:
        """Get total expenditure (debits) for date range."""
        with get_session() as session:
            query = select(Transaction).where(Transaction.debit.isnot(None))

            if start_date:
                query = query.where(Transaction.booking_date_time >= start_date)
            if end_date:
                query = query.where(Transaction.booking_date_time <= end_date)

            transactions = session.exec(query).all()
            return sum(t.debit for t in transactions if t.debit)

    def get_total_income(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> float:
        """Get total income (credits) for date range."""
        with get_session() as session:
            query = select(Transaction).where(Transaction.credit.isnot(None))

            if start_date:
                query = query.where(Transaction.booking_date_time >= start_date)
            if end_date:
                query = query.where(Transaction.booking_date_time <= end_date)

            transactions = session.exec(query).all()
            return sum(t.credit for t in transactions if t.credit)

    def get_percentile_breakdown(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, Any]:
        """
        Get percentile breakdown of expenditures and income by category.

        Returns dict with 'expenditure_by_category' and 'income_by_category'
        """
        with get_session() as session:
            query = select(Transaction)
            if start_date:
                query = query.where(Transaction.booking_date_time >= start_date)
            if end_date:
                query = query.where(Transaction.booking_date_time <= end_date)

            transactions = session.exec(query).all()

            # Group by category
            expenditure_by_cat: dict[str, float] = defaultdict(float)
            income_by_cat: dict[str, float] = defaultdict(float)

            for t in transactions:
                cat = t.category or "Uncategorized"
                if t.debit:
                    expenditure_by_cat[cat] += t.debit
                if t.credit:
                    income_by_cat[cat] += t.credit

            # Calculate percentiles
            total_exp = sum(expenditure_by_cat.values()) or 1
            total_inc = sum(income_by_cat.values()) or 1

            exp_percentiles = {
                cat: (val / total_exp) * 100 for cat, val in expenditure_by_cat.items()
            }
            inc_percentiles = {
                cat: (val / total_inc) * 100 for cat, val in income_by_cat.items()
            }

            return {
                "expenditure_by_category": exp_percentiles,
                "income_by_category": inc_percentiles,
                "total_expenditure": total_exp,
                "total_income": total_inc,
            }

    def get_income_expenditure_ratio(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> float:
        """Get income to expenditure ratio (>1 means saving, <1 means spending more)."""
        income = self.get_total_income(start_date, end_date)
        expenditure = self.get_total_expenditure(start_date, end_date)

        if expenditure == 0:
            return float("inf") if income > 0 else 0.0

        return income / expenditure

    def get_expenditure_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict[str, float]:
        """
        Get min, max, and standard deviation of expenditures.

        Returns dict with 'min', 'max', 'std_dev', 'mean'
        """
        with get_session() as session:
            query = select(Transaction).where(Transaction.debit.isnot(None))

            if start_date:
                query = query.where(Transaction.booking_date_time >= start_date)
            if end_date:
                query = query.where(Transaction.booking_date_time <= end_date)

            transactions = session.exec(query).all()
            debits = [t.debit for t in transactions if t.debit]

            if not debits:
                return {"min": 0.0, "max": 0.0, "std_dev": 0.0, "mean": 0.0}

            return {
                "min": min(debits),
                "max": max(debits),
                "std_dev": statistics.stdev(debits) if len(debits) > 1 else 0.0,
                "mean": statistics.mean(debits),
            }

    def get_monthly_forecast(self, year: int, month: int) -> dict[str, float]:
        """
        Get mean daily expenditure for a month and forecast total for month.

        Returns dict with 'daily_mean', 'days_elapsed', 'current_total', 'forecasted_total'
        """
        start_date = datetime(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime(year, month, last_day, 23, 59, 59)

        # Get current date to determine days elapsed
        today = datetime.now()
        if today.year == year and today.month == month:
            days_elapsed = today.day
        elif today > end_date:
            days_elapsed = last_day
        else:
            days_elapsed = 0

        with get_session() as session:
            query = select(Transaction).where(
                and_(
                    Transaction.debit.isnot(None),
                    Transaction.booking_date_time >= start_date,
                    Transaction.booking_date_time <= end_date,
                )
            )

            transactions = session.exec(query).all()
            current_total = sum(t.debit for t in transactions if t.debit)

            if days_elapsed > 0:
                daily_mean = current_total / days_elapsed
                forecasted_total = daily_mean * last_day
            else:
                daily_mean = 0.0
                forecasted_total = 0.0

            return {
                "daily_mean": daily_mean,
                "days_elapsed": days_elapsed,
                "days_in_month": last_day,
                "current_total": current_total,
                "forecasted_total": forecasted_total,
            }
