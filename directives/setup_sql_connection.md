# Directive: Initial Setup and SQL Server Connection

## Goal
Establish a connection to a SQL Server database for the Esopo dashboard application and create a basic Python environment.

## Inputs
- Database credentials (to be provided in `.env`)

## Execution Steps
1. Create a Python virtual environment (if needed, but for now we'll use the system/current environment).
2. Install necessary libraries: `pyodbc`, `pandas`, `dash` or `streamlit`.
3. Create an execution script to test connectivity.
4. Define the data schema for the dashboard.

## Edge Cases
- Driver not installed (ODBC Driver for SQL Server).
- Credential errors.
- Network access.
