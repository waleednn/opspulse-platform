import os
import sqlite3
import pandas as pd
from src.database import DB_PATH

def test_database_file_exists():
    """Check if SQLite database file exists at DB_PATH."""
    assert os.path.exists(str(DB_PATH)), "Database file opspulse.db was not found."

def test_tables_existence():
    """Verify all four required schema tables are present in the database."""
    con = sqlite3.connect(str(DB_PATH))
    cursor = con.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    con.close()
    
    expected_tables = {'dim_hubs', 'dim_couriers', 'dim_customers', 'fact_shipments'}
    assert expected_tables.issubset(tables), f"Missing tables. Found: {tables}"

def test_fact_shipments_record_count():
    """Check that fact_shipments contains records."""
    con = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql_query("SELECT COUNT(*) as cnt FROM fact_shipments;", con)
    con.close()
    assert df['cnt'].iloc[0] > 0, "fact_shipments table is empty."