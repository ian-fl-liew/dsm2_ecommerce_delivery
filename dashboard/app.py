import pandas as pd
import streamlit as st
import plotly.express as px

from utils.bigquery_client import REPORTING_DATASET, query


# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(
    page_title="Olist Delivery & Seller Performance",
    layout="wide"
)

st.title("Olist Delivery & Seller Performance")

st.caption(
    f"Business dashboard using reporting tables from "
    f"`{REPORTING_DATASET}`."
)


# ============================================================
# DELIVERY STATUS LABELS
# ============================================================

status_labels = {
    "early": "Early",
    "on_time": "On time",
    "late_1_3_days": "1–3 days late",
    "late_4_7_days": "4–7 days late",
    "late_8_plus_days": "8+ days late",
    "not_delivered": "Not delivered"
}


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Overview",
    "🏪 Seller Performance",
    "🚚 Delivery Performance",
    "⭐ Customer Satisfaction"
    
])


# ============================================================
# TAB 1 — OVERVIEW
# ============================================================

with tab1:

    st.header("Business Overview")

    st.write(
        "How are order volume and revenue changing over time?"
    )

    monthly_sales = query(f"""
        SELECT
            order_month,
            order_count,
            total_revenue
        FROM `{REPORTING_DATASET}.mart_monthly_sales`
        ORDER BY order_month
        LIMIT 30
    """)

    monthly_sales["order_month"] = pd.to_datetime(
        monthly_sales["order_month"]
    )

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Monthly order volume")

        st.line_chart(
            monthly_sales.set_index("order_month")["order_count"]
        )

        st.caption(
            "Number of orders placed each month."
        )

    with col2:

        st.subheader("Monthly revenue")

        st.line_chart(
            monthly_sales.set_index("order_month")["total_revenue"]
        )

        st.caption(
            "Total order revenue generated each month."
        )


# ============================================================
# TAB 2 — DELIVERY PERFORMANCE
# ============================================================

with tab3:

    st.header("Delivery Performance")

    st.write(
        "Business Question 2: How well is the delivery network performing?"
    )

    st.markdown(
        """
        ### Where is delivery risk greatest?

        We compare **revenue by state** with the **late-delivery rate**.

        States with **high revenue and high late-delivery rates**
        represent important areas for management attention.
        """
    )

    # --------------------------------------------------------
    # LOAD REVENUE RISK DATA
    # --------------------------------------------------------

    revenue_risk = query(f"""
        SELECT
            customer_state,
            total_revenue,
            total_orders,
            late_orders,
            late_revenue,
            late_delivery_pct,
            late_revenue_pct
        FROM `{REPORTING_DATASET}.mart_delivery_revenue_risk`
        ORDER BY total_revenue DESC
    """)

    # ========================================================
    # CHART 1 — REVENUE VS DELIVERY RISK
    # ========================================================

    st.subheader(
        "Revenue vs. late-delivery rate"
    )

    scatter_data = revenue_risk.copy()

    scatter_data["late_delivery_pct_display"] = (
        scatter_data["late_delivery_pct"] * 100
    )

    fig_scatter = px.scatter(
        scatter_data,
        x="late_delivery_pct_display",
        y="total_revenue",
        size="total_orders",
        hover_name="customer_state",
        hover_data={
            "late_delivery_pct_display": ":.1f",
            "total_revenue": ":,.0f",
            "total_orders": ":,",
            "late_orders": ":,",
            "late_revenue": ":,.0f",
            "late_delivery_pct": False,
            "late_revenue_pct": ":.1%"
        },
        labels={
            "late_delivery_pct_display": "Late delivery rate (%)",
            "total_revenue": "Total revenue",
            "total_orders": "Orders",
            "late_revenue_pct": "Late revenue share"
        },
        title="Which high-revenue states have higher delivery risk?"
    )

    fig_scatter.update_layout(
        height=550,
        margin=dict(
            t=70,
            l=20,
            r=20,
            b=20
        )
    )

    st.plotly_chart(
        fig_scatter,
        use_container_width=True
    )

    st.caption(
        "Each bubble represents a state. Bubble size represents "
        "order volume. States with both high revenue and high "
        "late-delivery rates are priority areas for investigation."
    )

    # ========================================================
    # CHART 2 — SUNBURST
    # ========================================================

    st.subheader(
        "Revenue exposure by delivery outcome"
    )

    st.markdown(
        """
        **Top 10 revenue-generating states → Delivery outcome → Revenue**

        Click a state to explore how its revenue is distributed
        across different delivery outcomes.
        """
    )

    # --------------------------------------------------------
    # LOAD SUNBURST DATA FROM REPORTING MART
    # --------------------------------------------------------

    sunburst_data = query(f"""
        SELECT
            customer_state,
            delivery_status,
            order_count,
            revenue
        FROM `{REPORTING_DATASET}.mart_delivery_sunburst`
    """)

    # Convert technical delivery status into business-friendly labels

    sunburst_data["delivery_outcome"] = (
        sunburst_data["delivery_status"]
        .map(status_labels)
        .fillna(sunburst_data["delivery_status"])
    )

    # --------------------------------------------------------
    # SUNBURST CHART
    # --------------------------------------------------------

    fig_sunburst = px.sunburst(
        sunburst_data,
        path=[
            "customer_state",
            "delivery_outcome"
        ],
        values="revenue",
        title="Top 10 revenue states → delivery outcome → revenue"
    )

    fig_sunburst.update_traces(
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Revenue: $%{value:,.0f}<br>"
            "Share: %{percentParent:.1%}"
            "<extra></extra>"
        )
    )

    fig_sunburst.update_layout(
        height=650,
        margin=dict(
            t=70,
            l=10,
            r=10,
            b=10
        )
    )

    st.plotly_chart(
        fig_sunburst,
        use_container_width=True
    )

    st.caption(
        "Click a state to explore the revenue associated with "
        "different delivery outcomes."
    )

    # ========================================================
    # TABLE — TOP 10 REVENUE STATES
    # ========================================================

    st.subheader(
        "Revenue and delivery risk — top 10 states"
    )

    top_10_states = (
        revenue_risk
        .sort_values(
            "total_revenue",
            ascending=False
        )
        .head(10)
        .copy()
    )

    display_risk = top_10_states[
        [
            "customer_state",
            "total_revenue",
            "total_orders",
            "late_orders",
            "late_revenue",
            "late_delivery_pct",
            "late_revenue_pct"
        ]
    ].copy()

    display_risk = display_risk.rename(
        columns={
            "customer_state": "State",
            "total_revenue": "Total revenue",
            "total_orders": "Orders",
            "late_orders": "Late orders",
            "late_revenue": "Late-delivery revenue",
            "late_delivery_pct": "Late delivery %",
            "late_revenue_pct": "Late revenue %"
        }
    )

    display_risk["Total revenue"] = (
        display_risk["Total revenue"].round(0)
    )

    display_risk["Late-delivery revenue"] = (
        display_risk["Late-delivery revenue"].round(0)
    )

    display_risk["Late delivery %"] = (
        display_risk["Late delivery %"] * 100
    ).round(1)

    display_risk["Late revenue %"] = (
        display_risk["Late revenue %"] * 100
    ).round(1)

    st.dataframe(
        display_risk,
        hide_index=True,
        use_container_width=True
    )

    st.caption(
        "Late-delivery revenue represents revenue from orders "
        "that were delivered late. It should be interpreted as "
        "revenue exposure associated with delivery issues, not "
        "revenue proven to be lost because of late delivery."
    )


# ============================================================
# TAB 3 — CUSTOMER SATISFACTION
# ============================================================

with tab4:

    st.header("Customer Satisfaction")

    st.write(
        "Business Question 3: Does delivery performance relate "
        "to customer satisfaction?"
    )

    satisfaction = query(f"""
        SELECT
            delivery_status,
            order_count,
            avg_review_score,
            avg_delivery_days
        FROM `{REPORTING_DATASET}.mart_satisfaction_by_delivery`
        ORDER BY avg_review_score DESC
    """)

    status_order = [
        "early",
        "on_time",
        "late_1_3_days",
        "late_4_7_days",
        "late_8_plus_days",
        "not_delivered",
    ]

    satisfaction["delivery_status"] = pd.Categorical(
        satisfaction["delivery_status"],
        categories=status_order,
        ordered=True
    )

    satisfaction = satisfaction.sort_values(
        "delivery_status"
    )

    satisfaction["delivery_outcome"] = (
        satisfaction["delivery_status"]
        .astype(str)
        .map(status_labels)
    )

    st.subheader(
        "Does late delivery relate to lower reviews?"
    )

    st.bar_chart(
        satisfaction.set_index(
            "delivery_outcome"
        )["avg_review_score"]
    )

    st.caption(
        "Average customer review score by delivery outcome."
    )

    display_satisfaction = satisfaction[
        [
            "delivery_outcome",
            "order_count",
            "avg_review_score",
            "avg_delivery_days"
        ]
    ].copy()

    display_satisfaction = display_satisfaction.rename(
        columns={
            "delivery_outcome": "Delivery outcome",
            "order_count": "Orders",
            "avg_review_score": "Avg review score",
            "avg_delivery_days": "Avg delivery days"
        }
    )

    display_satisfaction["Avg review score"] = (
        display_satisfaction["Avg review score"].round(2)
    )

    display_satisfaction["Avg delivery days"] = (
        display_satisfaction["Avg delivery days"].round(1)
    )

    st.dataframe(
        display_satisfaction,
        hide_index=True,
        use_container_width=True
    )


# ============================================================
# TAB 4 — SELLER PERFORMANCE
# ============================================================

with tab2:

    st.header("Seller Performance")

    st.write(
        "Business Question 1: How well are sellers fulfilling orders?"
    )

    seller_performance = query(f"""
        SELECT
            seller_id,
            order_count,
            item_count,
            total_revenue,
            late_shipping_pct,
            late_delivery_pct,
            avg_delivery_days
        FROM `{REPORTING_DATASET}.mart_seller_performance`
        WHERE order_count >= 20
        ORDER BY total_revenue DESC
        LIMIT 100
    """)

    # --------------------------------------------------------
    # TOP SELLERS BY REVENUE
    # --------------------------------------------------------

    st.subheader("Top sellers by revenue")

    top_sellers = (
        seller_performance
        .sort_values(
            "total_revenue",
            ascending=False
        )
        .head(10)
        .copy()
    )

    top_sellers["seller_label"] = (
        "Seller "
        + top_sellers["seller_id"].str[:8]
    )

    st.bar_chart(
        top_sellers.set_index(
            "seller_label"
        )["total_revenue"]
    )

    st.caption(
        "Top 10 sellers by total order revenue."
    )

    # --------------------------------------------------------
    # HIGHEST LATE-SHIPPING RATE
    # --------------------------------------------------------

    st.subheader(
        "Sellers with the highest late-shipping rate"
    )

    worst_shipping = (
        seller_performance
        .dropna(subset=["late_shipping_pct"])
        .sort_values(
            "late_shipping_pct",
            ascending=False
        )
        .head(10)
        .copy()
    )

    worst_shipping["seller_label"] = (
        "Seller "
        + worst_shipping["seller_id"].str[:8]
    )

    worst_shipping["late_shipping_display"] = (
        worst_shipping["late_shipping_pct"] * 100
    )

    st.bar_chart(
        worst_shipping.set_index(
            "seller_label"
        )["late_shipping_display"]
    )

    st.caption(
        "Top 10 sellers with the highest percentage of "
        "order items handed to the carrier after the shipping limit."
    )