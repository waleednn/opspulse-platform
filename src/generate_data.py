import random
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from faker import Faker
from database import get_connection


fake = Faker()
random.seed(42)
np.random.seed(42)

def populate_dimensions(con):
    """Populate dimension tables with realistic values"""
    
    # Hubs
    hubs = [
        ("HUB_RUH_01", "Riyadh Central Hub", "Riyadh", 15000),
        ("HUB_JED_01", "Jeddah Port Hub", "Jeddah", 12000),
        ("HUB_DMM_01", "Dammam Logistics Hub", "Dammam", 8000),
        ("HUB_MED_01", "Madinah Regional Hub", "Madinah", 4000)
    ]
    con.executemany("INSERT OR REPLACE INTO dim_hubs VALUES (?, ?, ?, ?)", hubs)

    # Couriers
    couriers = [
        ("CR_FAST", "FastTrack Express", "Vans & Bikes", 24, 1.20),
        ("CR_SPDX", "SpeedX Logistics", "Heavy Trucks", 48, 0.85),
        ("CR_NAQL", "Al-Naql Reliable", "Mixed Fleet", 24, 1.10),
        ("CR_DESR", "Desert Cargo", "Long Haul", 72, 0.70)
    ]
    con.executemany("INSERT OR REPLACE INTO dim_couriers VALUES (?, ?, ?, ?, ?)", couriers)

    # Customers (2,000 unique customers)
    customers = []
    cities = ["Riyadh", "Jeddah", "Dammam", "Madinah"]
    tiers = ["Standard", "Premium", "Enterprise"]
    for i in range(1, 2001):
        c_id = f"CUST_{i:05d}"
        c_type = "B2B" if random.random() < 0.25 else "B2C"
        c_city = random.choice(cities)
        c_tier = random.choices(tiers, weights=[0.7, 0.2, 0.1])[0]
        customers.append((c_id, c_type, c_city, c_tier))
        
    con.executemany("INSERT OR REPLACE INTO dim_customers VALUES (?, ?, ?, ?)", customers)
    print("Dimensions populated successfully.")

def generate_shipments(con, num_records=30000):
    """Generate 30,000 shipment records with temporal calculations and specific anomalies"""
    print(f"Generating {num_records} shipment records...")
    
    hubs = con.execute("SELECT hub_id, city FROM dim_hubs").fetchall()
    couriers = con.execute("SELECT courier_id, contract_sla_hours, cost_per_km FROM dim_couriers").fetchall()
    customers = con.execute("SELECT customer_id, city, tier FROM dim_customers").fetchall()

    start_date = datetime.now() - timedelta(days=90)
    records = []

    # Generate shipment records with temporal calculations and specific anomalies.

    for i in range(1, num_records + 1):
        shipment_id = f"SHP_{i:07d}"
        
        # Order creation time within the last 90 days.
        order_time = start_date + timedelta(
            seconds=random.randint(0, int(90 * 24 * 3600))
        )
        
        hub_id, hub_city = random.choice(hubs)
        courier_id, sla_hours, cost_km = random.choice(couriers)
        cust_id, cust_city, cust_tier = random.choice(customers)

        # Calculate the distance.
        distance = round(random.uniform(5.0, 35.0), 1) if hub_city == cust_city else round(random.uniform(380.0, 950.0), 1)
        shipping_fee = round(max(15.0, (distance * cost_km * 0.4) + random.uniform(10, 25)), 2)

        # Default processing time: 2 to 8 hours.
        dispatch_delay = round(random.uniform(2.0, 8.0), 2)
        
        # [Anomaly 1]: Jeddah hub congestion on the weekend (Friday/Saturday).
        if hub_id == "HUB_JED_01" and order_time.weekday() in [4, 5]:
            dispatch_delay += round(random.uniform(14.0, 28.0), 2)

        dispatch_time = order_time + timedelta(hours=dispatch_delay)
        promised_time = order_time + timedelta(hours=sla_hours)

        # Default transit and delivery time.
        transit_hours = (distance / 50.0) + random.uniform(1.0, 6.0)
        
        # [Anomaly 2]: SpeedX failures in Riyadh.
        is_speedx_ruh = (courier_id == "CR_SPDX" and hub_id == "HUB_RUH_01")
        if is_speedx_ruh and random.random() < 0.45:
            transit_hours += random.uniform(20.0, 50.0)  # Intentional major delay.
        
        actual_delivery = dispatch_time + timedelta(hours=transit_hours)
        
        # Calculate the SLA breach.
        is_breached = actual_delivery > promised_time
        total_delay = round((actual_delivery - promised_time).total_seconds() / 3600, 2)
        delivery_delay = max(0.0, total_delay)

        # Set the delivery status and rating.
        if is_breached and random.random() < 0.08:
            status = "Returned"
            rating = 1
        else:
            status = "Delivered"
            if is_breached:
                rating = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
            else:
                rating = random.choices([4, 5, 3], weights=[0.65, 0.30, 0.05])[0]

        records.append((
            shipment_id,
            order_time,
            dispatch_time,
            promised_time,
            actual_delivery,
            hub_id,
            courier_id,
            cust_id,
            distance,
            shipping_fee,
            status,
            is_breached,
            dispatch_delay,
            delivery_delay,
            rating
        ))

    # Insert all records into DuckDB in a single batch.
    con.executemany("""
    INSERT INTO fact_shipments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, records)
    print(f"Successfully generated and inserted {len(records)} shipments.")

if __name__ == "__main__":
    conn = get_connection()
    populate_dimensions(conn)
    generate_shipments(conn, num_records=35000)
    conn.close()