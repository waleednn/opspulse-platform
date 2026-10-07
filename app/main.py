import sys
import os
import sqlite3
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

# Append src folder to Python path for seamless module imports
SRC_PATH = Path(__file__).resolve().parent.parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

from database import DB_PATH
from guardrails import validate_and_sanitize_sql
from agent import generate_sql, execute_query, generate_insights

# Configure Streamlit page layout and theme
st.set_page_config(
    page_title="OpsPulse | AI Operational Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 15px;
        border-left: 5px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_kpis():
    """Fetches high-level executive KPIs from SQLite database."""
    con = sqlite3.connect(str(DB_PATH))
    kpi_query = """
    SELECT 
        COUNT(shipment_id) AS total_shipments,
        ROUND(AVG(is_sla_breached) * 100, 2) AS sla_breach_rate,
        ROUND(SUM(CASE WHEN is_sla_breached = 1 OR delivery_status = 'Returned' THEN shipping_fee ELSE 0 END), 2) AS revenue_at_risk,
        ROUND(AVG(delivery_delay_hours), 2) AS avg_delay_hours
    FROM fact_shipments;
    """
    df = pd.read_sql_query(kpi_query, con)
    con.close()
    return df.iloc[0]

@st.cache_data(ttl=600)
def load_chart_data():
    """Loads baseline aggregation data for dashboard charts."""
    con = sqlite3.connect(str(DB_PATH))
    
    # Courier performance data
    courier_query = """
    SELECT 
        c.courier_name,
        COUNT(f.shipment_id) AS total_shipments,
        ROUND(AVG(f.is_sla_breached) * 100, 2) AS breach_rate_pct,
        ROUND(AVG(f.delivery_delay_hours), 2) AS avg_delay_hours
    FROM fact_shipments f
    JOIN dim_couriers c ON f.courier_id = c.courier_id
    GROUP BY c.courier_name;
    """
    couriers_df = pd.read_sql_query(courier_query, con)

    # Hub performance data
    hub_query = """
    SELECT 
        h.hub_name,
        h.city,
        COUNT(f.shipment_id) AS total_shipments,
        ROUND(AVG(f.is_sla_breached) * 100, 2) AS breach_rate_pct,
        ROUND(AVG(f.dispatch_delay_hours), 2) AS avg_dispatch_lag
    FROM fact_shipments f
    JOIN dim_hubs h ON f.hub_id = h.hub_id
    GROUP BY h.hub_name, h.city;
    """
    hubs_df = pd.read_sql_query(hub_query, con)
    con.close()
    return couriers_df, hubs_df

# Sidebar controls
with st.sidebar:
    st.title("⚡ OpsPulse Platform")
    st.caption("AI-Powered Supply Chain Intelligence")
    st.markdown("---")
    st.info("System connected to local analytical database (**SQLite OLAP**).")
    
    if st.button("🔄 Refresh Data Cache"):
        st.cache_data.clear()
        st.rerun()

# Header
st.title("Operations & Logistics Intelligence Dashboard")
st.markdown("Real-time monitoring of SLA adherence, operational bottlenecks, and automated root-cause analysis.")

# 1. Executive KPI Metrics Strip
kpis = load_kpis()
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Shipments",
        value=f"{int(kpis['total_shipments']):,}"
    )
with col2:
    st.metric(
        label="SLA Breach Rate",
        value=f"{kpis['sla_breach_rate']}%",
        delta=f"{kpis['sla_breach_rate'] - 15:.1f}% vs Target" if kpis['sla_breach_rate'] > 15 else "On Track",
        delta_color="inverse"
    )
with col3:
    st.metric(
        label="Revenue at Risk",
        value=f"${kpis['revenue_at_risk']:,.2f}",
        delta="Breached & Returned",
        delta_color="inverse"
    )
with col4:
    st.metric(
        label="Avg Delivery Delay",
        value=f"{kpis['avg_delay_hours']} hrs"
    )

st.markdown("---")

# Navigation Tabs
tab_dashboard, tab_copilot = st.tabs(["📊 Executive Analytics", "🤖 AI Operations Copilot"])

# TAB 1: EXECUTIVE ANALYTICS
with tab_dashboard:
    couriers_df, hubs_df = load_chart_data()
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("Carrier Performance & Breach Rate")
        fig_couriers = px.bar(
            couriers_df,
            x="courier_name",
            y="breach_rate_pct",
            color="breach_rate_pct",
            color_continuous_scale="Reds",
            labels={"courier_name": "Carrier", "breach_rate_pct": "SLA Breach Rate (%)"},
            text_auto=True
        )
        fig_couriers.update_layout(showlegend=False)
        st.plotly_chart(fig_couriers, use_container_width=True)

    with chart_col2:
        st.subheader("Warehouse Dispatch Processing Lag")
        fig_hubs = px.bar(
            hubs_df,
            x="hub_name",
            y="avg_dispatch_lag",
            color="avg_dispatch_lag",
            color_continuous_scale="Blues",
            labels={"hub_name": "Distribution Hub", "avg_dispatch_lag": "Avg Dispatch Lag (Hours)"},
            text_auto=True
        )
        fig_hubs.update_layout(showlegend=False)
        st.plotly_chart(fig_hubs, use_container_width=True)

    st.subheader("Regional Hub Breakdown")
    st.dataframe(hubs_df, use_container_width=True)

# TAB 2: AI OPERATIONS COPILOT
with tab_copilot:
    st.subheader("Ask OpsPulse Copilot")
    st.caption("Ask ad-hoc operational questions in plain Arabic or English. The engine validates the SQL query, retrieves live data, and synthesizes root-cause insights.")

    # Initialize chat history in session state
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Preset quick-prompt buttons
    st.markdown("**Sample inquiries to explore:**")
    quick_col1, quick_col2, quick_col3 = st.columns(3)
    preset_query = None

    if quick_col1.button("📍 قارن شركات الشحن في الرياض"):
        preset_query = "قارن بين أداء شركات الشحن المختلفة في منطقة الرياض من حيث نسبة التأخير ومتوسط ساعات التأخير"
    if quick_col2.button("⏱️ فحص تأخيرات مستودع جدة"):
        preset_query = "ما هو متوسط وقت التجهيز في مستودع جدة خلال أيام عطلة نهاية الأسبوع مقارنة بباقي الأيام؟"
    if quick_col3.button("💰 الفئات الأكثر مساهمة في تعريض الأرباح للخطر"):
        preset_query = "من هي أكثر شرائح العملاء B2B أو B2C مساهمة في الأرباح المعرضة للخطر (Revenue at Risk)؟"

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.write(msg["content"])
            else:
                st.markdown(msg["insight"])
                if "sql" in msg:
                    with st.expander("🔍 View Validated SQL Query"):
                        st.code(msg["sql"], language="sql")
                if "data" in msg and not msg["data"].empty:
                    with st.expander("📋 View Underlying Data"):
                        st.dataframe(msg["data"], use_container_width=True)

    # Process user query
    user_prompt = st.chat_input("اكتب استفسارك التشغيلي هنا...") or preset_query

    if user_prompt:
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.write(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing operational data and generating root cause report..."):
                try:
                    # 1. Translate question to SQL
                    generated_sql = generate_sql(user_prompt)
                    
                    # 2. Enforce guardrails
                    sanitized_sql = validate_and_sanitize_sql(generated_sql)
                    
                    # 3. Execute query
                    result_df = execute_query(sanitized_sql)
                    
                    # 4. Generate operational insights
                    insight_text = generate_insights(user_prompt, sanitized_sql, result_df)
                    
                    # Render outputs
                    st.markdown(insight_text)
                    
                    with st.expander("🔍 View Validated SQL Query"):
                        st.code(sanitized_sql, language="sql")
                        
                    with st.expander("📋 View Underlying Data"):
                        st.dataframe(result_df, use_container_width=True)

                    # Persist response in session history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "insight": insight_text,
                        "sql": sanitized_sql,
                        "data": result_df
                    })
                except Exception as err:
                    error_msg = f"⚠️ Could not process query: {str(err)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "insight": error_msg
                    })