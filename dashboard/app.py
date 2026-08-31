import pandas as pd
import streamlit as st
from utils.bigquery_client import REPORTING_DATASET, query

st.set_page_config(page_title="Olist Delivery & Seller Performance", layout="wide")

st.title("Olist Delivery & Seller Performance")
st.caption(
    f"Starter dashboard, reading pre-aggregated tables from `{REPORTING_DATASET}` "
    "(built by dbt on top of the CSV -> MongoDB -> BigQuery pipeline) -- proves the "
    "end-to-end flow: Kaggle -> dlt -> MongoDB -> dlt -> BigQuery raw -> dbt star schema "
    "-> dbt datamart -> here."
)

col1, col2 = st.columns(2)

# --- Business Question 3: delivery performance vs. customer satisfaction ---
satisfaction = query(f"""
    SELECT delivery_status, order_count, avg_review_score, avg_delivery_days
    FROM `{REPORTING_DATASET}.mart_satisfaction_by_delivery`
    ORDER BY avg_review_score DESC
""")

status_order = [
    "early", "on_time", "late_1_3_days", "late_4_7_days", "late_8_plus_days", "not_delivered",
]
satisfaction["delivery_status"] = pd.Categorical(
    satisfaction["delivery_status"], categories=status_order, ordered=True
)
satisfaction = satisfaction.sort_values("delivery_status")

with col1:
    st.subheader("Does late delivery hurt reviews?")
    st.bar_chart(satisfaction.set_index("delivery_status")["avg_review_score"])
    st.dataframe(satisfaction, hide_index=True, use_container_width=True)

# --- Monthly sales trend ---
monthly_sales = query(f"""
    SELECT order_month, order_count, total_revenue
    FROM `{REPORTING_DATASET}.mart_monthly_sales`
    ORDER BY order_month
""")
monthly_sales["order_month"] = pd.to_datetime(monthly_sales["order_month"])

with col2:
    st.subheader("Monthly order volume & revenue")
    st.line_chart(monthly_sales.set_index("order_month")[["order_count"]])
    st.line_chart(monthly_sales.set_index("order_month")[["total_revenue"]])

# --- Business Question 2: delivery network performance by state ---
st.subheader("Delivery performance by state")
delivery_kpis = query(f"""
    SELECT
        customer_state,
        SUM(order_count) AS order_count,
        SAFE_DIVIDE(SUM(late_count), SUM(order_count)) AS late_pct,
        SAFE_DIVIDE(SUM(avg_delivery_days * order_count), SUM(order_count)) AS avg_delivery_days
    FROM `{REPORTING_DATASET}.mart_delivery_kpis`
    GROUP BY customer_state
    HAVING order_count >= 20
    ORDER BY late_pct DESC
    LIMIT 15
""")
st.bar_chart(delivery_kpis.set_index("customer_state")["late_pct"])
st.dataframe(delivery_kpis, hide_index=True, use_container_width=True)
