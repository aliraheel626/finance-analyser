"""Budget Tracker GUI Application using ttkbootstrap."""

import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Optional

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.tableview import Tableview

from src.database import init_db
from src.services import (
    AnalyticsService,
    BankStatementProcessingService,
    TransactionPipeline,
    TransactionService,
)


class App(ttk.Window):
    """Main application window."""

    def __init__(self):
        """Initialize the application."""
        super().__init__(themename="darkly")

        self.title("Budget Tracker")
        self.geometry("1200x800")

        # Initialize database
        init_db()

        # Initialize services
        self.transaction_service = TransactionService()
        self.analytics_service = AnalyticsService()
        self.processing_service = BankStatementProcessingService()
        self.pipeline = TransactionPipeline()

        # Current state
        self.current_page = 1
        self.page_size = 20
        self.selected_transaction_id: Optional[int] = None

        # Create UI
        self._create_notebook()

    def _create_notebook(self):
        """Create the main notebook with tabs."""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        # Create tabs
        self._create_import_tab()
        self._create_transactions_tab()
        self._create_dashboard_tab()

    def _create_import_tab(self):
        """Create the CSV import tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Import CSV")

        # Title
        ttk.Label(
            frame,
            text="Import Bank Statement",
            font=("Helvetica", 18, "bold"),
        ).pack(pady=(0, 20))

        # File selection frame
        file_frame = ttk.Frame(frame)
        file_frame.pack(fill=X, pady=10)

        self.file_path_var = tk.StringVar()
        ttk.Entry(
            file_frame,
            textvariable=self.file_path_var,
            width=60,
            state="readonly",
        ).pack(side=LEFT, padx=(0, 10))

        ttk.Button(
            file_frame,
            text="Select CSV",
            command=self._select_csv_file,
            bootstyle="primary",
        ).pack(side=LEFT)

        # Import button
        ttk.Button(
            frame,
            text="Import Transactions",
            command=self._import_transactions,
            bootstyle="success",
            width=20,
        ).pack(pady=20)

        # Status label
        self.import_status_var = tk.StringVar(value="Select a CSV file to import")
        ttk.Label(
            frame,
            textvariable=self.import_status_var,
            font=("Helvetica", 12),
        ).pack(pady=10)

    def _select_csv_file(self):
        """Open file dialog to select CSV file."""
        file_path = filedialog.askopenfilename(
            title="Select Bank Statement CSV",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.import_status_var.set("Ready to import")

    def _import_transactions(self):
        """Import transactions from selected CSV file."""
        file_path = self.file_path_var.get()
        if not file_path:
            messagebox.showwarning("No File", "Please select a CSV file first.")
            return

        try:
            result = self.pipeline.process(file_path, annotate=False)
            self.import_status_var.set(
                f"Imported {result['inserted']} new transactions "
                f"(from {result['extracted']} total in file)"
            )
            messagebox.showinfo(
                "Import Complete",
                f"Successfully imported {result['inserted']} new transactions!",
            )
            # Refresh transactions view
            self._load_transactions()
            self._update_dashboard()
        except Exception as e:
            messagebox.showerror("Import Error", f"Error importing file: {e}")
            self.import_status_var.set(f"Error: {e}")

    def _create_transactions_tab(self):
        """Create the transactions view tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Transactions")

        # Title and controls frame
        controls_frame = ttk.Frame(frame)
        controls_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(
            controls_frame,
            text="Transactions",
            font=("Helvetica", 18, "bold"),
        ).pack(side=LEFT)

        # Pagination controls
        pagination_frame = ttk.Frame(controls_frame)
        pagination_frame.pack(side=RIGHT)

        ttk.Button(
            pagination_frame,
            text="← Previous",
            command=self._prev_page,
            bootstyle="secondary-outline",
        ).pack(side=LEFT, padx=2)

        self.page_label_var = tk.StringVar(value="Page 1 of 1")
        ttk.Label(
            pagination_frame,
            textvariable=self.page_label_var,
            width=15,
        ).pack(side=LEFT, padx=10)

        ttk.Button(
            pagination_frame,
            text="Next →",
            command=self._next_page,
            bootstyle="secondary-outline",
        ).pack(side=LEFT, padx=2)

        # Transactions table
        columns = [
            {"text": "ID", "stretch": False, "width": 50},
            {"text": "Date", "stretch": False, "width": 100},
            {"text": "Description", "stretch": True, "width": 300},
            {"text": "Debit", "stretch": False, "width": 100},
            {"text": "Credit", "stretch": False, "width": 100},
            {"text": "Balance", "stretch": False, "width": 100},
            {"text": "Category", "stretch": False, "width": 100},
        ]

        self.transactions_table = Tableview(
            frame,
            coldata=columns,
            rowdata=[],
            paginated=False,
            searchable=True,
            bootstyle="primary",
            height=20,
        )
        self.transactions_table.pack(fill=BOTH, expand=YES)

        # Bind selection event
        self.transactions_table.view.bind("<<TreeviewSelect>>", self._on_row_select)

        # Action buttons frame
        actions_frame = ttk.Frame(frame)
        actions_frame.pack(fill=X, pady=(10, 0))

        ttk.Button(
            actions_frame,
            text="Edit Selected",
            command=self._edit_transaction,
            bootstyle="info",
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            actions_frame,
            text="Delete Selected",
            command=self._delete_transaction,
            bootstyle="danger",
        ).pack(side=LEFT, padx=5)

        ttk.Button(
            actions_frame,
            text="Refresh",
            command=self._load_transactions,
            bootstyle="secondary",
        ).pack(side=RIGHT, padx=5)

        # Load initial data
        self._load_transactions()

    def _load_transactions(self):
        """Load transactions into the table."""
        try:
            result = self.transaction_service.read_transactions(
                page=self.current_page,
                page_size=self.page_size,
            )

            # Update page label
            self.page_label_var.set(
                f"Page {result['page']} of {result['total_pages']}"
            )

            # Clear and reload table
            self.transactions_table.delete_rows()

            rows = []
            for txn in result["transactions"]:
                rows.append(
                    (
                        txn["id"],
                        txn["booking_date_time"].strftime("%Y-%m-%d")
                        if isinstance(txn["booking_date_time"], datetime)
                        else str(txn["booking_date_time"])[:10],
                        txn["bank_statement_description"][:50] + "..."
                        if len(txn["bank_statement_description"]) > 50
                        else txn["bank_statement_description"],
                        f"{txn['debit']:.2f}" if txn["debit"] else "",
                        f"{txn['credit']:.2f}" if txn["credit"] else "",
                        f"{txn['available_balance']:.2f}",
                        txn["category"] or "",
                    )
                )

            self.transactions_table.insert_rows(END, rows)
            self.transactions_table.load_table_data()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load transactions: {e}")

    def _on_row_select(self, event):
        """Handle row selection in transactions table."""
        selection = self.transactions_table.view.selection()
        if selection:
            item = self.transactions_table.view.item(selection[0])
            values = item.get("values", [])
            if values:
                self.selected_transaction_id = values[0]

    def _prev_page(self):
        """Go to previous page."""
        if self.current_page > 1:
            self.current_page -= 1
            self._load_transactions()

    def _next_page(self):
        """Go to next page."""
        result = self.transaction_service.read_transactions(
            page=self.current_page,
            page_size=self.page_size,
        )
        if self.current_page < result["total_pages"]:
            self.current_page += 1
            self._load_transactions()

    def _edit_transaction(self):
        """Open dialog to edit selected transaction."""
        if not self.selected_transaction_id:
            messagebox.showwarning("No Selection", "Please select a transaction first.")
            return

        # Get current transaction data
        result = self.transaction_service.read_transactions(
            transaction_id=self.selected_transaction_id
        )

        if not result["transactions"]:
            messagebox.showerror("Error", "Transaction not found.")
            return

        txn = result["transactions"][0]

        # Create edit dialog
        dialog = EditTransactionDialog(self, txn)
        self.wait_window(dialog)

        if dialog.result:
            try:
                self.transaction_service.update_transaction_by_id(
                    self.selected_transaction_id, dialog.result
                )
                messagebox.showinfo("Success", "Transaction updated successfully!")
                self._load_transactions()
                self._update_dashboard()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update: {e}")

    def _delete_transaction(self):
        """Delete selected transaction."""
        if not self.selected_transaction_id:
            messagebox.showwarning("No Selection", "Please select a transaction first.")
            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            "Are you sure you want to delete this transaction?",
        )

        if confirm:
            try:
                self.transaction_service.delete_transaction(
                    self.selected_transaction_id
                )
                messagebox.showinfo("Success", "Transaction deleted successfully!")
                self.selected_transaction_id = None
                self._load_transactions()
                self._update_dashboard()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete: {e}")

    def _create_dashboard_tab(self):
        """Create the analytics dashboard tab."""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Dashboard")

        # Title
        ttk.Label(
            frame,
            text="Financial Dashboard",
            font=("Helvetica", 18, "bold"),
        ).pack(pady=(0, 20))

        # Stats frame
        stats_frame = ttk.Frame(frame)
        stats_frame.pack(fill=X, pady=10)

        # Create stat cards
        self.stat_cards = {}

        cards_data = [
            ("total_income", "Total Income", "success"),
            ("total_expenditure", "Total Expenditure", "danger"),
            ("ratio", "Income/Expense Ratio", "info"),
            ("avg_expense", "Average Expense", "warning"),
        ]

        for i, (key, label, style) in enumerate(cards_data):
            card = self._create_stat_card(stats_frame, label, "0.00", style)
            card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
            self.stat_cards[key] = card
            stats_frame.columnconfigure(i, weight=1)

        # Expenditure stats frame
        exp_stats_frame = ttk.LabelFrame(frame, text="Expenditure Statistics")
        exp_stats_frame.pack(fill=X, pady=20)

        self.exp_stats_labels = {}
        exp_stats = [("min", "Minimum"), ("max", "Maximum"), ("std_dev", "Std Dev"), ("mean", "Mean")]

        for i, (key, label) in enumerate(exp_stats):
            ttk.Label(exp_stats_frame, text=f"{label}:").grid(
                row=0, column=i * 2, padx=5, sticky="e"
            )
            value_label = ttk.Label(exp_stats_frame, text="0.00", font=("Helvetica", 12, "bold"))
            value_label.grid(row=0, column=i * 2 + 1, padx=5, sticky="w")
            self.exp_stats_labels[key] = value_label

        # Monthly forecast frame
        forecast_frame = ttk.LabelFrame(frame, text="Monthly Forecast")
        forecast_frame.pack(fill=X, pady=10)

        self.forecast_labels = {}
        forecast_items = [
            ("current", "Current Month Spent"),
            ("daily_avg", "Daily Average"),
            ("forecast", "Forecasted Total"),
        ]

        for i, (key, label) in enumerate(forecast_items):
            ttk.Label(forecast_frame, text=f"{label}:").grid(
                row=0, column=i * 2, padx=10, sticky="e"
            )
            value_label = ttk.Label(
                forecast_frame, text="0.00", font=("Helvetica", 14, "bold")
            )
            value_label.grid(row=0, column=i * 2 + 1, padx=10, sticky="w")
            self.forecast_labels[key] = value_label

        # Refresh button
        ttk.Button(
            frame,
            text="Refresh Dashboard",
            command=self._update_dashboard,
            bootstyle="primary",
        ).pack(pady=20)

        # Initial update
        self._update_dashboard()

    def _create_stat_card(
        self, parent, title: str, value: str, style: str
    ) -> ttk.Frame:
        """Create a statistics card widget."""
        card = ttk.Frame(parent)
        card.configure(bootstyle=f"{style}")

        ttk.Label(
            card,
            text=title,
            font=("Helvetica", 10),
        ).pack()

        value_label = ttk.Label(
            card,
            text=value,
            font=("Helvetica", 24, "bold"),
        )
        value_label.pack(pady=5)

        # Store reference to value label for updates
        card.value_label = value_label

        return card

    def _update_dashboard(self):
        """Update all dashboard statistics."""
        try:
            # Get totals
            total_income = self.analytics_service.get_total_income()
            total_exp = self.analytics_service.get_total_expenditure()
            ratio = self.analytics_service.get_income_expenditure_ratio()

            # Update stat cards
            self.stat_cards["total_income"].value_label.config(
                text=f"{total_income:,.2f}"
            )
            self.stat_cards["total_expenditure"].value_label.config(
                text=f"{total_exp:,.2f}"
            )
            self.stat_cards["ratio"].value_label.config(text=f"{ratio:.2f}")

            # Get expenditure stats
            exp_stats = self.analytics_service.get_expenditure_stats()
            self.stat_cards["avg_expense"].value_label.config(
                text=f"{exp_stats['mean']:,.2f}"
            )

            for key in ["min", "max", "std_dev", "mean"]:
                self.exp_stats_labels[key].config(text=f"{exp_stats[key]:,.2f}")

            # Get monthly forecast
            now = datetime.now()
            forecast = self.analytics_service.get_monthly_forecast(now.year, now.month)

            self.forecast_labels["current"].config(
                text=f"{forecast['current_total']:,.2f}"
            )
            self.forecast_labels["daily_avg"].config(
                text=f"{forecast['daily_mean']:,.2f}"
            )
            self.forecast_labels["forecast"].config(
                text=f"{forecast['forecasted_total']:,.2f}"
            )

        except Exception as e:
            print(f"Error updating dashboard: {e}")


class EditTransactionDialog(tk.Toplevel):
    """Dialog for editing a transaction."""

    def __init__(self, parent, transaction: dict):
        """Initialize the edit dialog."""
        super().__init__(parent)

        self.title("Edit Transaction")
        self.geometry("500x400")
        self.transient(parent)
        self.grab_set()

        self.result = None
        self.transaction = transaction

        self._create_form()

    def _create_form(self):
        """Create the edit form."""
        frame = ttk.Frame(self)
        frame.pack(fill=BOTH, expand=YES)

        # Description field
        ttk.Label(frame, text="Description:").grid(row=0, column=0, sticky="w", pady=5)
        self.description_var = tk.StringVar(
            value=self.transaction.get("description") or ""
        )
        ttk.Entry(frame, textvariable=self.description_var, width=40).grid(
            row=0, column=1, pady=5, sticky="ew"
        )

        # Category field
        ttk.Label(frame, text="Category:").grid(row=1, column=0, sticky="w", pady=5)
        self.category_var = tk.StringVar(
            value=self.transaction.get("category") or ""
        )
        categories = [
            "Food",
            "Transport",
            "Shopping",
            "Bills",
            "Transfer",
            "Salary",
            "Entertainment",
            "ATM",
            "Subscription",
            "Government",
            "Other",
        ]
        ttk.Combobox(
            frame,
            textvariable=self.category_var,
            values=categories,
            width=37,
        ).grid(row=1, column=1, pady=5, sticky="ew")

        # Originator name field
        ttk.Label(frame, text="Originator:").grid(row=2, column=0, sticky="w", pady=5)
        self.originator_var = tk.StringVar(
            value=self.transaction.get("originator_name") or ""
        )
        ttk.Entry(frame, textvariable=self.originator_var, width=40).grid(
            row=2, column=1, pady=5, sticky="ew"
        )

        # Group field
        ttk.Label(frame, text="Group:").grid(row=3, column=0, sticky="w", pady=5)
        self.group_var = tk.StringVar(
            value=self.transaction.get("group_name") or ""
        )
        ttk.Entry(frame, textvariable=self.group_var, width=40).grid(
            row=3, column=1, pady=5, sticky="ew"
        )

        # Is taxes checkbox
        self.is_taxes_var = tk.BooleanVar(
            value=self.transaction.get("is_taxes", False)
        )
        ttk.Checkbutton(
            frame,
            text="Is Tax Transaction",
            variable=self.is_taxes_var,
            bootstyle="round-toggle",
        ).grid(row=4, column=1, pady=10, sticky="w")

        # Buttons
        buttons_frame = ttk.Frame(frame)
        buttons_frame.grid(row=5, column=0, columnspan=2, pady=20)

        ttk.Button(
            buttons_frame,
            text="Save",
            command=self._save,
            bootstyle="success",
            width=15,
        ).pack(side=LEFT, padx=10)

        ttk.Button(
            buttons_frame,
            text="Cancel",
            command=self.destroy,
            bootstyle="secondary",
            width=15,
        ).pack(side=LEFT, padx=10)

        frame.columnconfigure(1, weight=1)

    def _save(self):
        """Save the changes and close dialog."""
        self.result = {
            "description": self.description_var.get() or None,
            "category": self.category_var.get() or None,
            "originator_name": self.originator_var.get() or None,
            "group_name": self.group_var.get() or None,
            "is_taxes": self.is_taxes_var.get(),
        }
        self.destroy()
