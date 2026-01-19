# Budget Tracker

# Stack
- Language: Python
- GUI: ttkbootstrap
- Database: sqlite

# Features
- should use pydantic setting
- GUI
    - to select csv file for parsing
    - to create dashboard to show fiscal analysis
    - to view transactions paginated and have the ability to update them
    - to view transactions paginated and have the ability to delete them
- BankStatementProcessingService 
    - should have methods to extract transactions from CSV file and insert them to, should have entry method extract, 
    - should add day_order_id to transactions within day

- TransactionService 
    - function to read transactions from database
        - should return transactions as list of dict
        - should return transactions sorted by date and order key
        - should return transactions with related taxes as nested dict in parent transaction dict instead of seperate transaction
        - should be able to filter transactions by date range, custom_name, category, name, id
        - should relate taxes to parent transaction using stan id and identify a tax transaction using is_taxes column
        - should have pagination
    - function to insert transactions to database
        - using day_order_id and date_time as composity unique keys to insert only not found transactions and not update the already existing transactions
    - should provide a function to update transactions in bulk
    - should provide a function to update transaction by id
- AnalyticsService
    - should be able to give total expenditure for date range
    - should be able to give percentile breakdown of expenditures and income
    - should be able to give percentile income to expenditure ratio
    - should be able to give min-max of expenditures and standard deviation
    - should be able to give mean of expenditures of given a given month and use it forecast total expenditures at end of month
- TransactionAnnotationService
    - should be able to use langchain gpt5-nano in order to extract transaction description, category, originator_name, is_taxes
    - should be able to process transactions in batches
- TransactionModel
    - should have fields: id, booking_date_time, value_date_time, day_order_id, bank_statement_descriptionstan_id, debit, credit, available_balance,, description, category, originator_name, group, is_taxes
- Should create a pipeline using TransactionExtractionService.extract()->TransactionAnnotationService.annotate() -> TransactionService.update()

# Architecture
- GUI Layer, Service Layer are seperate
- All components are classes


# Assumptions
- Transactions do not update
- Transaction order is maintained in the csv via a hidden id key


