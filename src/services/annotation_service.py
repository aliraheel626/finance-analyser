"""Service for AI-powered transaction annotation using LangChain."""

from typing import Any

from sqlmodel import or_, select

from src.config import settings
from src.database import get_session
from src.models import Transaction


class TransactionAnnotationService:
    """Service for AI-powered transaction annotation using LangChain."""

    def __init__(self):
        """Initialize the annotation service."""
        self._llm = None
        self._transaction_service = None

    @property
    def transaction_service(self):
        """Get transaction service lazily."""
        if self._transaction_service is None:
            from src.services.transaction_service import TransactionService
            self._transaction_service = TransactionService()
        return self._transaction_service

    def _get_llm(self):
        """Lazy-load the LLM to avoid import errors if not configured."""
        if self._llm is None:
            from langchain_openai import ChatOpenAI

            if not settings.openai_api_key:
                raise ValueError(
                    "OpenAI API key not configured. Set OPENAI_API_KEY in .env file."
                )

            self._llm = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=settings.openai_api_key,
                temperature=0,
            )
        return self._llm

    def annotate_transaction(self, description: str) -> dict[str, Any]:
        """
        Use LLM to extract transaction metadata from description.

        Returns dict with: description, category, originator_name, is_taxes
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = self._get_llm()

        system_prompt = """You are a financial transaction analyzer. Given a bank transaction description, extract:
1. description: A clean, human-readable description of what this transaction is for
2. category: One of: Food, Transport, Shopping, Bills, Transfer, Salary, Entertainment, ATM, Subscription, Government, Other
3. originator_name: The merchant, person, or entity involved (if identifiable)
4. is_taxes: true if this is a tax-related charge, false otherwise

Respond in JSON format only, no other text:
{"description": "...", "category": "...", "originator_name": "...", "is_taxes": false}"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Transaction: {description}"),
        ]

        response = llm.invoke(messages)

        # Parse JSON response
        import json

        try:
            result = json.loads(response.content)
            return {
                "description": result.get("description", ""),
                "category": result.get("category", "Other"),
                "originator_name": result.get("originator_name"),
                "is_taxes": result.get("is_taxes", False),
            }
        except json.JSONDecodeError:
            return {
                "description": description,
                "category": "Other",
                "originator_name": None,
                "is_taxes": False,
            }

    def annotate_batch(self, transaction_ids: list[int], batch_size: int = 10) -> int:
        """
        Annotate multiple transactions in batches.

        Returns number of transactions annotated
        """
        annotated = 0

        with get_session() as session:
            for txn_id in transaction_ids:
                transaction = session.get(Transaction, txn_id)
                if not transaction:
                    continue

                # Skip already annotated transactions
                if transaction.description and transaction.category:
                    continue

                try:
                    annotations = self.annotate_transaction(
                        transaction.bank_statement_description
                    )

                    # Update transaction
                    for key, value in annotations.items():
                        if hasattr(transaction, key):
                            setattr(transaction, key, value)

                    session.add(transaction)
                    annotated += 1

                    # Commit in batches
                    if annotated % batch_size == 0:
                        session.commit()

                except Exception as e:
                    print(f"Error annotating transaction {txn_id}: {e}")
                    continue

            # Final commit
            session.commit()

        return annotated

    def annotate_all_unannotated(self, batch_size: int = 10) -> int:
        """Annotate all transactions that haven't been annotated yet."""
        with get_session() as session:
            query = select(Transaction.id).where(
                or_(
                    Transaction.description.is_(None),
                    Transaction.category.is_(None),
                )
            )
            ids = list(session.exec(query).all())

        return self.annotate_batch(ids, batch_size)
