# Budget Tracker

# Stack
- Language: Python
- GUI: tkbootstrap
- Database: sqlite

# Features
- Add CSV using frontend
- insert missing transactions from csv to sqlite
- set desc and category default values to null
- Create dashboard to show fiscal analysis
- annotate transactions with description and category using GUI
- relate transaction taxes with parent transactions using STAN as id
- create key to identify transaction order within one day
- sort transactions by date and order key

# Architecture
- GUI Layer, Service Layer, Data Access Layer


# Assumptions
- Transactions do not update
- Transaction order is maintained in the csv via a hidden id key


