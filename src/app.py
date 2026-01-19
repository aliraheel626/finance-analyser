"""Budget Tracker GUI Application using NiceGUI."""

import io
from datetime import datetime
from typing import Optional

import plotly.graph_objects as go
from nicegui import events, ui

from src.database import init_db
from src.services import (
    AnalyticsService,
    BankStatementProcessingService,
    TransactionPipeline,
    TransactionService,
)


class App:
    """Main application frontend using NiceGUI."""

    def __init__(self):
        """Initialize the application."""
        init_db()

        # Initialize services
        self.transaction_service = TransactionService()
        self.analytics_service = AnalyticsService()
        self.processing_service = BankStatementProcessingService()
        self.pipeline = TransactionPipeline()

        # UI State
        self.selected_rows = []
        
        # Build UI
        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        """Setup custom styles and colors."""
        ui.colors(primary='#38bdf8', secondary='#0ea5e9', accent='#0369a1')
        ui.query('body').style('background-color: #0f172a; color: #f8fafc;')

    def _build_ui(self):
        """Construct the layout."""
        with ui.header().classes('items-center justify-between bg-slate-900 border-b border-slate-700'):
            ui.label('Budget Tracker').classes('text-2xl font-bold text-sky-400')
            with ui.row().classes('items-center gap-4'):
                ui.button('Refresh All', on_click=self.refresh_all, icon='refresh').props('flat color=white')

        with ui.tabs().classes('w-full bg-slate-900 text-slate-400') as tabs:
            self.import_tab = ui.tab('Import', icon='cloud_upload')
            self.transactions_tab = ui.tab('Transactions', icon='list')
            self.dashboard_tab = ui.tab('Dashboard', icon='dashboard')

        with ui.tab_panels(tabs, value=self.transactions_tab).classes('w-full grow bg-transparent'):
            with ui.tab_panel(self.import_tab):
                self._build_import_tab()
            with ui.tab_panel(self.transactions_tab):
                self._build_transactions_tab()
            with ui.tab_panel(self.dashboard_tab):
                self._build_dashboard_tab()

    def _build_import_tab(self):
        """Build the CSV import section."""
        with ui.column().classes('w-full max-w-2xl mx-auto items-center py-12 gap-6'):
            ui.label('Import Bank Statement').classes('text-3xl font-bold')
            ui.label('Select your bank statement CSV file to process and import transactions.').classes('text-slate-400 text-center')
            
            with ui.card().classes('w-full p-8 bg-slate-800 border border-slate-700'):
                ui.upload(
                    label='Upload CSV', 
                    on_upload=self._handle_upload,
                    auto_upload=True
                ).props('accept=.csv').classes('w-full')

    def _build_transactions_tab(self):
        """Build the transactions table section."""
        with ui.column().classes('w-full grow p-4'):
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label('Recent Transactions').classes('text-2xl font-bold')
                with ui.row().classes('gap-2'):
                    ui.button('Edit Selected', on_click=self._edit_selected).bind_visibility_from(self, 'selected_rows', backward=lambda x: len(x) == 1)
                    ui.button('Delete Selected', on_click=self._delete_selected, color='red').bind_visibility_from(self, 'selected_rows', backward=lambda x: len(x) > 0)

            # Table configuration using ui.table
            columns = [
                {'name': 'id', 'label': 'ID', 'field': 'id', 'sortable': True, 'align': 'left'},
                {'name': 'date', 'label': 'Date', 'field': 'booking_date_time', 'sortable': True, 'align': 'left'},
                {'name': 'description', 'label': 'Description', 'field': 'bank_statement_description', 'sortable': True, 'align': 'left'},
                {'name': 'debit', 'label': 'Debit', 'field': 'debit', 'sortable': True, 'align': 'right'},
                {'name': 'credit', 'label': 'Credit', 'field': 'credit', 'sortable': True, 'align': 'right'},
                {'name': 'category', 'label': 'Category', 'field': 'category', 'sortable': True, 'align': 'left'},
            ]
            
            self.table = ui.table(columns=columns, rows=[], row_key='id', selection='multiple', pagination=20).classes('w-full')
            self.table.on('selection', lambda e: setattr(self, 'selected_rows', e.args[1]))
            
            self._load_transactions()

    def _build_dashboard_tab(self):
        """Build the analytics dashboard."""
        with ui.column().classes('w-full grow p-4 gap-6'):
            ui.label('Financial Insights').classes('text-2xl font-bold')
            
            # Stats Cards
            with ui.row().classes('w-full gap-4'):
                self.income_card = self._stat_card('Total Income', '0.00', 'green-400')
                self.expense_card = self._stat_card('Total Expenditure', '0.00', 'red-400')
                self.ratio_card = self._stat_card('Savings Ratio', '0.00', 'blue-400')
                self.forecast_card = self._stat_card('Monthly Forecast', '0.00', 'purple-400')

            # Charts
            with ui.row().classes('w-full gap-4'):
                with ui.card().classes('grow p-4 bg-slate-800 border-slate-700'):
                    ui.label('Expenditure by Category').classes('text-lg font-bold mb-4')
                    self.pie_chart = ui.plotly({}).classes('w-full h-80')

            self._update_analytics()

    def _stat_card(self, title: str, value: str, color: str):
        with ui.card().classes(f'grow p-6 bg-slate-800 border border-slate-700 items-center justify-center') as card:
            ui.label(title).classes('text-slate-400 uppercase text-xs tracking-wider')
            card.value_label = ui.label(value).classes(f'text-3xl font-bold text-{color}')
        return card

    # Logic Methods
    async def _handle_upload(self, e: events.UploadEventArguments):
        """Process uploaded CSV."""
        try:
            # NiceGUI 3.5.0 uses e.file with async read() method
            file_content = await e.file.read()
            content = file_content.decode('utf-8')
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            
            try:
                result = self.pipeline.process(tmp_path, annotate=False)
                ui.notify(f"Successfully imported {result['inserted']} new transactions!", type='positive')
                self.refresh_all()
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
        except Exception as ex:
            ui.notify(f"Import failed: {ex}", type='negative')

    def _load_transactions(self):
        """Fetch transactions and update table."""
        result = self.transaction_service.read_transactions(page_size=1000)
        data = result['transactions']
        print(f"[DEBUG] Loaded {len(data)} transactions")
        # Format dates for table
        for d in data:
            if isinstance(d.get('booking_date_time'), datetime):
                d['booking_date_time'] = d['booking_date_time'].strftime('%Y-%m-%d')
        # Update table rows
        self.table.rows = data
        self.table.update()
        print(f"[DEBUG] Table rows set to {len(self.table.rows)} items")

    def _update_analytics(self):
        """Fetch stats and update visuals."""
        income = self.analytics_service.get_total_income()
        expense = self.analytics_service.get_total_expenditure()
        ratio = self.analytics_service.get_income_expenditure_ratio()
        
        now = datetime.now()
        forecast = self.analytics_service.get_monthly_forecast(now.year, now.month)

        self.income_card.value_label.set_text(f"{income:,.2f}")
        self.expense_card.value_label.set_text(f"{expense:,.2f}")
        self.ratio_card.value_label.set_text(f"{ratio:.2f}")
        self.forecast_card.value_label.set_text(f"{forecast['forecasted_total']:,.2f}")

        # Update Pie Chart
        stats = self.analytics_service.get_percentile_breakdown()
        cats = list(stats['expenditure_by_category'].keys())
        vals = list(stats['expenditure_by_category'].values())
        
        fig = go.Figure(data=[go.Pie(labels=cats, values=vals, hole=.4)])
        fig.update_layout(
            margin=dict(t=0, b=0, l=0, r=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f8fafc'),
            showlegend=True
        )
        self.pie_chart.update_figure(fig)

    async def _handle_cell_change(self, e):
        """Handle inline edits in AG Grid."""
        row_id = e.args['data']['id']
        field = e.args['colId']
        new_val = e.args['newValue']
        
        self.transaction_service.update_transaction_by_id(row_id, {field: new_val})
        ui.notify(f"Updated {field} for transaction {row_id}")
        self._update_analytics()

    def _edit_selected(self):
        """Open edit dialog for selected row."""
        if not self.selected_rows: return
        txn = self.selected_rows[0]
        
        with ui.dialog() as dialog, ui.card().classes('w-96'):
            ui.label('Edit Transaction').classes('text-xl font-bold mb-4')
            desc = ui.input('Description', value=txn['bank_statement_description']).classes('w-full')
            cat = ui.select(['Food', 'Transport', 'Shopping', 'Bills', 'Transfer', 'Salary', 'Entertainment', 'ATM', 'Subscription', 'Government', 'Other'], 
                           label='Category', value=txn['category']).classes('w-full')
            
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('Cancel', on_click=dialog.close).props('flat')
                ui.button('Save', on_click=lambda: self._save_edit(txn['id'], desc.value, cat.value, dialog))
        dialog.open()

    def _save_edit(self, txn_id, desc, cat, dialog):
        self.transaction_service.update_transaction_by_id(txn_id, {
            'bank_statement_description': desc,
            'category': cat
        })
        dialog.close()
        ui.notify('Transaction updated')
        self.refresh_all()

    async def _delete_selected(self):
        """Delete all selected rows."""
        count = len(self.selected_rows)
        with ui.dialog() as dialog, ui.card():
            ui.label(f'Are you sure you want to delete {count} transactions?').classes('text-lg')
            with ui.row().classes('w-full justify-end'):
                ui.button('Cancel', on_click=dialog.close).props('flat')
                ui.button('Delete', color='red', on_click=lambda: self._perform_delete(dialog))
        dialog.open()

    def _perform_delete(self, dialog):
        for row in self.selected_rows:
            self.transaction_service.delete_transaction(row['id'])
        dialog.close()
        self.selected_rows = []
        ui.notify(f'Deleted transactions')
        self.refresh_all()

    def refresh_all(self):
        """Refresh all data views."""
        self._load_transactions()
        self._update_analytics()

# The UI is built during initialization of the App class.
# NiceGUI elements are global, so we just need to instantiate the class.

