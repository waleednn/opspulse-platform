import sqlite3
import pandas as pd
from database import DB_PATH

con = sqlite3.connect(str(DB_PATH))

# Check SpeedX performance: Riyadh vs Other Cities
query = """
SELECT 
    c.courier_name,
    h.city AS hub_city,
    COUNT(f.shipment_id) AS shipments,
    ROUND(AVG(f.is_sla_breached) * 100, 2) AS breach_rate_pct,
    ROUND(AVG(f.delivery_delay_hours), 2) AS avg_delay_hours
FROM fact_shipments f
JOIN dim_couriers c ON f.courier_id = c.courier_id
JOIN dim_hubs h ON f.hub_id = h.hub_id
WHERE c.courier_name = 'SpeedX Logistics'
GROUP BY c.courier_name, h.city
ORDER BY breach_rate_pct DESC;
"""

df = pd.read_sql_query(query, con)
print("\n--- SpeedX Performance by Hub City ---")
print(df)
con.close()