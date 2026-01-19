"""Service for managing transactions in the database."""

from datetime import datetime
from typing import Any, Optional

from sqlmodel import and_, select

from src.config import settings
from src.database import get_session
from src.models import Transaction


class TransactionService:
    """Service for managing transactions in the database."""

    def read_transactions(
        self,
        page: int = 1,
        page_size: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category: Optional[str] = None,
        custom_name: Optional[str] = None,
        name: Optional[str] = None,
        transaction_id: Optional[int] = None,
        include_taxes_nested: bool = True,
        only_annotated: bool = False,
    ) -> dict[str, Any]:
        """
        Read transactions with filtering, sorting, and pagination.

        Returns:
            Dict with 'transactions', 'total', 'page', 'page_size', 'total_pages'
        """
        if page_size is None:
            page_size = settings.default_page_size

        with get_session() as session:
            # Build base query - exclude tax transactions if nesting
            query = select(Transaction)

            if include_taxes_nested:
                query = query.where(Transaction.is_taxes == False)

            # Apply filters
            if start_date:
                query = query.where(Transaction.booking_date_time >= start_date)
            if end_date:
                query = query.where(Transaction.booking_date_time <= end_date)
            if category:
                query = query.where(Transaction.category == category)
            if custom_name:
                query = query.where(Transaction.description.ilike(f"%{custom_name}%"))
            if name:
                query = query.where(Transaction.originator_name.ilike(f"%{name}%"))
            if transaction_id:
                query = query.where(Transaction.id == transaction_id)
            if only_annotated:
                query = query.where(Transaction.description.isnot(None))
                query = query.where(Transaction.category.isnot(None))

            # Get total count
            count_query = select(Transaction)
            if include_taxes_nested:
                count_query = count_query.where(Transaction.is_taxes == False)
            if start_date:
                count_query = count_query.where(
                    Transaction.booking_date_time >= start_date
                )
            if end_date:
                count_query = count_query.where(
                    Transaction.booking_date_time <= end_date
                )
            if category:
                count_query = count_query.where(Transaction.category == category)
            if only_annotated:
                count_query = count_query.where(Transaction.description.isnot(None))
                count_query = count_query.where(Transaction.category.isnot(None))

            all_for_count = session.exec(count_query).all()
            total = len(all_for_count)

            # Sort by date and day_order_id
            query = query.order_by(
                Transaction.booking_date_time.desc(), Transaction.day_order_id.desc()
            )

            # Apply pagination
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)

            transactions = session.exec(query).all()

            # Convert to dicts and nest taxes
            result = []
            for txn in transactions:
                txn_dict = txn.model_dump()

                if include_taxes_nested and txn.stan_id:
                    # Find related tax transactions
                    tax_query = select(Transaction).where(
                        and_(
                            Transaction.is_taxes == True,
                            Transaction.stan_id == txn.stan_id,
                        )
                    )
                    taxes = session.exec(tax_query).all()
                    txn_dict["related_taxes"] = [t.model_dump() for t in taxes]
                else:
                    txn_dict["related_taxes"] = []

                result.append(txn_dict)

            total_pages = (total + page_size - 1) // page_size if total > 0 else 1

            return {
                "transactions": result,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            }

    def insert_transactions(self, transactions: list[dict[str, Any]]) -> int:
        """
        Insert transactions using composite unique key check.

        Only inserts transactions that don't already exist (by booking_date_time + day_order_id).

        Returns:
            Number of new transactions inserted
        """
        inserted = 0

        with get_session() as session:
            for txn_data in transactions:
                # Check if transaction already exists
                existing = session.exec(
                    select(Transaction).where(
                        and_(
                            Transaction.booking_date_time
                            == txn_data["booking_date_time"],
                            Transaction.day_order_id == txn_data["day_order_id"],
                        )
                    )
                ).first()

                if not existing:
                    transaction = Transaction(**txn_data)
                    session.add(transaction)
                    inserted += 1

            session.commit()

        return inserted

    def update_transaction_by_id(
        self, transaction_id: int, updates: dict[str, Any]
    ) -> bool:
        """
        Update a single transaction by ID.

        Returns:
            True if updated, False if not found
        """
        with get_session() as session:
            transaction = session.get(Transaction, transaction_id)
            if not transaction:
                return False

            for key, value in updates.items():
                if hasattr(transaction, key):
                    setattr(transaction, key, value)

            session.add(transaction)
            session.commit()
            return True

    def update_transactions_bulk(
        self, transaction_ids: list[int], updates: dict[str, Any]
    ) -> int:
        """
        Update multiple transactions with the same updates.

        Returns:
            Number of transactions updated
        """
        updated = 0

        with get_session() as session:
            for txn_id in transaction_ids:
                transaction = session.get(Transaction, txn_id)
                if transaction:
                    for key, value in updates.items():
                        if hasattr(transaction, key):
                            setattr(transaction, key, value)
                    session.add(transaction)
                    updated += 1

            session.commit()

        return updated

    def delete_transaction(self, transaction_id: int) -> bool:
        """
        Delete a transaction by ID.

        Returns:
            True if deleted, False if not found
        """
        with get_session() as session:
            transaction = session.get(Transaction, transaction_id)
            if not transaction:
                return False

            session.delete(transaction)
            session.commit()
            return True

    def get_all_categories(self) -> list[str]:
        """Get all unique categories."""
        with get_session() as session:
            query = select(Transaction.category).where(
                Transaction.category.isnot(None)
            ).distinct()
            return [c for c in session.exec(query).all() if c]
