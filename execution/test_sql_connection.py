import pyodbc
import os
import sys
from dotenv import load_dotenv

# Load environment variables from the same directory as the script
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '..', '.env')
load_dotenv(dotenv_path=env_path)

def test_connection():
    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_DATABASE')
    username = os.getenv('DB_USERNAME')
    password = os.getenv('DB_PASSWORD')
    driver = os.getenv('DB_DRIVER', '{ODBC Driver 17 for SQL Server}')

    connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}'
    
    print(f"Attempting to connect to {server}/{database}...")
    
    try:
        conn = pyodbc.connect(connection_string)
        print("Success! Connected to SQL Server.")
        
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        row = cursor.fetchone()
        print(f"SQL Server Version: {row[0]}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"Error connecting to SQL Server: {e}")
        return False

if __name__ == "__main__":
    if not test_connection():
        sys.exit(1)
