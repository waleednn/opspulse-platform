import sqlite3
from pathlib import Path

# Database path in the data folder
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "opspulse.db"

def get_connection():
    """Establish connection to SQLite database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(DB_PATH))

def init_database():
    """Initialize Star Schema tables."""
    con = get_connection()
    cur = con.cursor()

    # 1. Hubs Dimension
    cur.execute("""
    CREATE TABLE IF NOT EXISTS dim_hubs (
        hub_id TEXT PRIMARY KEY,
        hub_name TEXT NOT NULL,
        city TEXT NOT NULL,
        capacity_per_day INTEGER NOT NULL
    );
    """)

    # 2. Couriers Dimension
    cur.execute("""
    CREATE TABLE IF NOT EXISTS dim_couriers (
        courier_id TEXT PRIMARY KEY,
        courier_name TEXT NOT NULL,
        fleet_type TEXT NOT NULL,
        contract_sla_hours INTEGER NOT NULL,
        cost_per_km REAL NOT NULL
    );
    """)

    # 3. Customers Dimension
    cur.execute("""
    CREATE TABLE IF NOT EXISTS dim_customers (
        customer_id TEXT PRIMARY KEY,
        customer_type TEXT NOT NULL,
        city TEXT NOT NULL,
        tier TEXT NOT NULL
    );
    """)

    # 4. Shipments Fact Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fact_shipments (
        shipment_id TEXT PRIMARY KEY,
        order_timestamp TEXT NOT NULL,
        dispatch_timestamp TEXT,
        promised_delivery_timestamp TEXT NOT NULL,
        actual_delivery_timestamp TEXT,
        hub_id TEXT REFERENCES dim_hubs(hub_id),
        courier_id TEXT REFERENCES dim_couriers(courier_id),
        customer_id TEXT REFERENCES dim_customers(customer_id),
        distance_km REAL NOT NULL,
        shipping_fee REAL NOT NULL,
        delivery_status TEXT NOT NULL,
        is_sla_breached INTEGER NOT NULL,
        dispatch_delay_hours REAL,
        delivery_delay_hours REAL,
        customer_rating INTEGER
    );
    """)

    con.commit()
    con.close()
    print(f"Database schema initialized successfully at: {DB_PATH}")

if __name__ == "__main__":
    init_database()