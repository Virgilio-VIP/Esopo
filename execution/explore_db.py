import pyodbc
import os
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '..', '.env')
load_dotenv(dotenv_path=env_path)

def get_db_connection():
    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_DATABASE')
    username = os.getenv('DB_USERNAME')
    password = os.getenv('DB_PASSWORD')
    driver = os.getenv('DB_DRIVER')
    
    connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    return pyodbc.connect(connection_string)

def explore_db():
    try:
        conn = get_db_connection()
        
        # Get tables
        query_tables = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'"
        tables = pd.read_sql(query_tables, conn)
        
        print("Tables in database:")
        print(tables.head(20))
        
        # Get top row count for each table to see which ones have data
        for table in tables['TABLE_NAME'].head(10):
            try:
                count_query = f"SELECT COUNT(*) FROM [{table}]"
                count = pd.read_sql(count_query, conn).iloc[0,0]
                print(f"Table: {table} - Rows: {count}")
            except:
                pass
                
        conn.close()
    except Exception as e:
        print(f"Error exploring database: {e}")

if __name__ == "__main__":
    explore_db()
