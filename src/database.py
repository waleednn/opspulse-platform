import duckdb
from pathlib import Path

# specify the path to the database file inside the data folder
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "opspulse.duckdb"

def get_connection():
    """Create a connection to the DuckDB database"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))

def init_database():
    """Create the Star Schema tables and indices"""
    con = get_connection()
    
    # 1. Table for Warehouses and Distribution Centers
    con.execute("""
    CREATE TABLE IF NOT EXISTS dim_hubs (
        hub_id VARCHAR PRIMARY KEY,
        hub_name VARCHAR NOT NULL,
        city VARCHAR NOT NULL,
        capacity_per_day INTEGER NOT NULL
    );
    """)

    # 2. Table for Shipping and Couriers Companies
    con.execute("""
    CREATE TABLE IF NOT EXISTS dim_couriers (
        courier_id VARCHAR PRIMARY KEY,
        courier_name VARCHAR NOT NULL,
        fleet_type VARCHAR NOT NULL,
        contract_sla_hours INTEGER NOT NULL,
        cost_per_km DOUBLE NOT NULL
    );
    """)

    # 3. Table for Customers
    con.execute("""
    CREATE TABLE IF NOT EXISTS dim_customers (
        customer_id VARCHAR PRIMARY KEY,
        customer_type VARCHAR NOT NULL,   -- 'B2B' or 'B2C'
        city VARCHAR NOT NULL,
        tier VARCHAR NOT NULL             -- 'Standard', 'Premium', 'Enterprise'
    );
    """)

    # 4. Fact Table for Shipments
    con.execute("""
    CREATE TABLE IF NOT EXISTS fact_shipments (
        shipment_id VARCHAR PRIMARY KEY,
        order_timestamp TIMESTAMP NOT NULL,
        dispatch_timestamp TIMESTAMP,
        promised_delivery_timestamp TIMESTAMP NOT NULL,
        actual_delivery_timestamp TIMESTAMP,
        hub_id VARCHAR REFERENCES dim_hubs(hub_id),
        courier_id VARCHAR REFERENCES dim_couriers(courier_id),
        customer_id VARCHAR REFERENCES dim_customers(customer_id),
        distance_km DOUBLE NOT NULL,
        shipping_fee DOUBLE NOT NULL,
        delivery_status VARCHAR NOT NULL,  -- 'Delivered', 'Returned', 'Delayed'
        is_sla_breached BOOLEAN NOT NULL,
        dispatch_delay_hours DOUBLE,
        delivery_delay_hours DOUBLE,
        customer_rating INTEGER
    );
    """)

    print(f"Database schema initialized successfully at: {DB_PATH}")
    con.close()

if __name__ == "__main__":
    init_database()