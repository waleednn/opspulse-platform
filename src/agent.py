import os
import time
import sqlite3
import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError

from database import DB_PATH
from guardrails import validate_and_sanitize_sql

# Load environment variables
load_dotenv()

# Initialize Gemini Client
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY is missing. Please set it in your .env file.")

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-3.8-flash"

# Comprehensive database schema metadata provided to LLM
DATABASE_CONTEXT = """
Database Schema (SQLite dialect):

1. dim_hubs:
   - hub_id (TEXT, PRIMARY KEY): Hub identifier ('HUB_RUH_01', 'HUB_JED_01', 'HUB_DMM_01', 'HUB_MED_01')
   - hub_name (TEXT): Facility name ('Riyadh Central Hub', 'Jeddah Port Hub', etc.)
   - city (TEXT): Location city ('Riyadh', 'Jeddah', 'Dammam', 'Madinah')
   - capacity_per_day (INTEGER): Processing capacity

2. dim_couriers:
   - courier_id (TEXT, PRIMARY KEY): Courier ID ('CR_FAST', 'CR_SPDX', 'CR_NAQL', 'CR_DESR')
   - courier_name (TEXT): Carrier name ('FastTrack Express', 'SpeedX Logistics', 'Al-Naql Reliable', 'Desert Cargo')
   - fleet_type (TEXT): Vehicle type
   - contract_sla_hours (INTEGER): Agreed SLA window in hours (24, 48, 72)
   - cost_per_km (REAL): Contract rate per kilometer

3. dim_customers:
   - customer_id (TEXT, PRIMARY KEY): Customer ID
   - customer_type (TEXT): 'B2B' or 'B2C'
   - city (TEXT): Destination city
   - tier (TEXT): 'Standard', 'Premium', 'Enterprise'

4. fact_shipments:
   - shipment_id (TEXT, PRIMARY KEY): Shipment record identifier
   - order_timestamp (TEXT): Format 'YYYY-MM-DD HH:MM:SS'
   - dispatch_timestamp (TEXT): Warehouse dispatch timestamp
   - promised_delivery_timestamp (TEXT): SLA deadline
   - actual_delivery_timestamp (TEXT): Actual delivery timestamp
   - hub_id (TEXT, FK -> dim_hubs.hub_id)
   - courier_id (TEXT, FK -> dim_couriers.courier_id)
   - customer_id (TEXT, FK -> dim_customers.customer_id)
   - distance_km (REAL): Route distance in KM
   - shipping_fee (REAL): Charged freight fee
   - delivery_status (TEXT): 'Delivered', 'Delayed', 'Returned'
   - is_sla_breached (INTEGER): 1 if delayed past promised delivery, else 0
   - dispatch_delay_hours (REAL): Internal warehouse processing time
   - delivery_delay_hours (REAL): Delivery delay beyond SLA deadline (0 if on-time)
   - customer_rating (INTEGER): Rating from 1 to 5

Key Business Calculations:
- SLA Breach Rate % = ROUND(AVG(f.is_sla_breached) * 100, 2)
- Revenue at Risk = SUM(f.shipping_fee) WHERE is_sla_breached = 1 OR delivery_status = 'Returned'
- Internal Processing Lag = dispatch_delay_hours
- Transit Delay = delivery_delay_hours
"""

SYSTEM_SQL_PROMPT = f"""
You are an expert SQL analytics engineer specializing in supply chain logistics.
Generate a single SQLite query that directly answers the user's business question.

{DATABASE_CONTEXT}

Strict Guidelines:
1. Output ONLY the raw SQL query. Do not wrap in markdown quotes (no ```sql or ```).
2. Do not include any explanations, greetings, or conversational text.
3. Write clean, optimized SQLite queries using JOINs, GROUP BY, and aggregate functions where applicable.
4. Always filter or aggregate appropriately to provide actionable operational metrics.
"""

def call_gemini_with_retry(prompt: str, system_instruction: str = None, temperature: float = 0.0, max_retries: int = 4) -> str:
    """Invokes Gemini with exponential backoff on 503 server overload."""
    for attempt in range(1, max_retries + 1):
        try:
            config_args = {"temperature": temperature}
            if system_instruction:
                config_args["system_instruction"] = system_instruction
            
            config = types.GenerateContentConfig(**config_args)
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config,
            )
            return response.text.strip()
        except (ServerError, APIError) as e:
            if "503" in str(e) or isinstance(e, ServerError):
                wait_time = attempt * 3
                print(f"[Server Notice] Model busy. Retrying in {wait_time}s (Attempt {attempt}/{max_retries})...")
                time.sleep(wait_time)
            else:
                raise e
    raise RuntimeError("Gemini service is currently overloaded. Please wait a few moments and try again.")

def generate_sql(question: str) -> str:
    """Uses Gemini to translate natural language question into an executable SQLite query."""
    raw_sql = call_gemini_with_retry(
        prompt=question,
        system_instruction=SYSTEM_SQL_PROMPT,
        temperature=0.0
    )
    
    # Strip potential markdown code fences
    if raw_sql.startswith("```"):
        lines = raw_sql.split("\n")
        raw_sql = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])
    return raw_sql.strip()

def execute_query(sanitized_sql: str) -> pd.DataFrame:
    """Executes validated SQL query on SQLite database and returns a DataFrame."""
    con = sqlite3.connect(str(DB_PATH))
    try:
        return pd.read_sql_query(sanitized_sql, con)
    finally:
        con.close()

def generate_insights(question: str, sanitized_sql: str, data_df: pd.DataFrame) -> str:
    """Generates an executive operational summary with root cause and recommendations."""
    if data_df.empty:
        return "No data returned for this inquiry. Please verify the query parameters or timeframe."

    data_summary = data_df.to_string(index=False)
    prompt = f"""
User Question: {question}

Executed SQL Query:
{sanitized_sql}

Retrieved Data:
{data_summary}

Provide a concise, professional operational insight response tailored for a Logistics Operations Manager:
1. Executive Summary: Direct, data-backed answer to the question in 2-3 sentences.
2. Root Cause Analysis: Pinpoint the exact operational bottleneck (e.g., specific carrier, hub, or day).
3. Actionable Next Steps: 2 concrete business recommendations to resolve the issue.

Respond in professional Arabic (or English if the user asked in English). Keep it sharp, objective, and executive-ready.
"""
    return call_gemini_with_retry(prompt=prompt, temperature=0.2)

def run_ops_agent(question: str):
    """End-to-end orchestration pipeline."""
    print(f"\n[User Question]: {question}\n")
    
    # Step 1: Generate SQL
    print("1. Generating SQL query via Gemini...")
    raw_sql = generate_sql(question)
    print(f"Generated SQL:\n{raw_sql}\n")
    
    # Step 2: Validate via Guardrails
    print("2. Validating SQL against security guardrails...")
    try:
        safe_sql = validate_and_sanitize_sql(raw_sql)
        print(f"Sanitized SQL:\n{safe_sql}\n")
    except ValueError as e:
        print(f"Guardrail Blocked Execution: {e}")
        return
    
    # Step 3: Execute query
    print("3. Querying SQLite database...")
    df = execute_query(safe_sql)
    print(f"Results Preview ({len(df)} rows returned):")
    print(df.head(10))
    print("\n" + "-" * 50)
    
    # Step 4: Generate Operational Insights
    print("4. Generating business insight and recommendations via Gemini...")
    insight = generate_insights(question, safe_sql, df)
    print("\n[Operations Copilot Insight]:")
    print(insight)
    print("-" * 50)

if __name__ == "__main__":
    sample_question = "قارن بين أداء شركات الشحن المختلفة في منطقة الرياض من حيث نسبة التأخير ومتوسط ساعات التأخير"
    run_ops_agent(sample_question)