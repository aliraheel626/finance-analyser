"""Pipeline for processing transactions end-to-end."""

from typing import Any


class TransactionPipeline:
    """Pipeline for processing transactions end-to-end."""

    def __init__(self):
        """Initialize pipeline services."""
        # Lazy imports to avoid circular dependencies
        self._extraction_service = None
        self._annotation_service = None
        self._transaction_service = None

    @property
    def extraction_service(self):
        """Get extraction service lazily."""
        if self._extraction_service is None:
            from src.services.processing_service import BankStatementProcessingService
            self._extraction_service = BankStatementProcessingService()
        return self._extraction_service

    @property
    def annotation_service(self):
        """Get annotation service lazily."""
        if self._annotation_service is None:
            from src.services.annotation_service import TransactionAnnotationService
            self._annotation_service = TransactionAnnotationService()
        return self._annotation_service

    @property
    def transaction_service(self):
        """Get transaction service lazily."""
        if self._transaction_service is None:
            from src.services.transaction_service import TransactionService
            self._transaction_service = TransactionService()
        return self._transaction_service

    def process(self, csv_path: str, annotate: bool = False) -> dict[str, Any]:
        """
        Run the full pipeline: extract -> (optionally annotate) -> insert.

        Returns dict with counts of operations performed.
        """
        # Extract transactions from CSV
        transactions = self.extraction_service.extract(csv_path)

        # Insert into database
        inserted = self.transaction_service.insert_transactions(transactions)

        result = {
            "extracted": len(transactions),
            "inserted": inserted,
            "annotated": 0,
        }

        # Optionally annotate
        if annotate:
            result["annotated"] = self.annotation_service.annotate_all_unannotated()

        return result
