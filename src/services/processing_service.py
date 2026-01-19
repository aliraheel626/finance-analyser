"""Service for processing bank statement CSV files."""

import csv
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional


class BankStatementProcessingService:
    """Service for processing bank statement CSV files."""

    # Known date formats in the CSV
    DATE_FORMAT = "%d %b %Y"

    def __init__(self):
        """Initialize the service."""
        # Lazy import to avoid circular dependency
        self._transaction_service = None

    @property
    def transaction_service(self):
        """Get transaction service lazily."""
        if self._transaction_service is None:
            from src.services.transaction_service import TransactionService
            self._transaction_service = TransactionService()
        return self._transaction_service

    def extract(self, csv_path: str) -> list[dict[str, Any]]:
        """
        Extract transactions from a CSV file.

        Args:
            csv_path: Path to the CSV file

        Returns:
            List of transaction dictionaries
        """
        transactions = []
        day_counts: dict[str, int] = defaultdict(int)

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            rows = list(reader)

        # Find the header row (contains "Booking Date")
        header_idx = None
        for i, row in enumerate(rows):
            if row and "Booking Date" in row[0]:
                header_idx = i
                break

        if header_idx is None:
            raise ValueError("Could not find header row in CSV")

        # Parse transactions after header
        for row in rows[header_idx + 1 :]:
            # Skip empty rows or summary rows
            if not row[0] or row[0].strip() == "":
                continue

            try:
                transaction = self._parse_row(row, day_counts)
                if transaction:
                    transactions.append(transaction)
            except (ValueError, IndexError):
                # Skip malformed rows
                continue

        return transactions

    def _parse_row(
        self, row: list[str], day_counts: dict[str, int]
    ) -> Optional[dict[str, Any]]:
        """Parse a single CSV row into a transaction dict."""
        booking_date_str = row[0].strip()
        value_date_str = row[1].strip()

        # Skip if no valid date
        if not booking_date_str:
            return None

        # Parse dates
        booking_date = datetime.strptime(booking_date_str, self.DATE_FORMAT)
        value_date = datetime.strptime(value_date_str, self.DATE_FORMAT)

        # Get day key for ordering
        day_key = booking_date.strftime("%Y-%m-%d")
        day_counts[day_key] += 1
        day_order_id = day_counts[day_key]

        # Parse description and extract STAN ID
        description = row[3].strip() if len(row) > 3 else ""
        stan_id = self._extract_stan_id(description)

        # Parse amounts
        debit = self._parse_amount(row[4]) if len(row) > 4 else None
        credit = self._parse_amount(row[5]) if len(row) > 5 else None
        balance = self._parse_amount(row[6]) if len(row) > 6 else 0.0

        # Check if this is a tax transaction
        is_taxes = self._is_tax_transaction(description)

        return {
            "booking_date_time": booking_date,
            "value_date_time": value_date,
            "day_order_id": day_order_id,
            "bank_statement_description": description,
            "stan_id": stan_id,
            "debit": debit,
            "credit": credit,
            "available_balance": balance or 0.0,
            "is_taxes": is_taxes,
        }

    def _extract_stan_id(self, description: str) -> Optional[str]:
        """Extract STAN ID from description."""
        # Pattern: STAN (123456) or STAN(123456)
        match = re.search(r"STAN\s*\((\d+)\)", description, re.IGNORECASE)
        return match.group(1) if match else None

    def _is_tax_transaction(self, description: str) -> bool:
        """Check if transaction is a tax-related entry."""
        tax_patterns = [
            r"FBRTax",
            r"Withholding Tax",
            r"Charges Taxes",
            r"CHG:.*Tax",
        ]
        for pattern in tax_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                return True
        return False

    def _parse_amount(self, value: str) -> Optional[float]:
        """Parse amount string to float."""
        if not value or not value.strip():
            return None
        try:
            # Remove any currency symbols and commas
            cleaned = re.sub(r"[^\d.-]", "", value.strip())
            return float(cleaned) if cleaned else None
        except ValueError:
            return None

    def process_and_insert(self, csv_path: str) -> int:
        """
        Extract transactions from CSV and insert into database.

        Returns:
            Number of new transactions inserted
        """
        transactions = self.extract(csv_path)
        return self.transaction_service.insert_transactions(transactions)
