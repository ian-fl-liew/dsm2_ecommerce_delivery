import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

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

# Variable names stay tied to their "with tabN:" content blocks below;
# only the unpacking ORDER changes here to control left-to-right tab position.
tab1, tab3, tab5, tab2, tab4 = st.tabs([
    "📊 Overview",
    "🚚 Delivery Performance",
    "🔎 Delay Root Cause",
    "🏪 Seller Performance",
    "⭐ Customer Satisfaction"
])


# ============================================================
# TAB 1 — OVERVIEW
# ============================================================

with tab1:

    st.header("Business Overview")

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

    # Cut off at Aug 2018 -- the static Kaggle extract has very sparse data
    # from Sept 2018 onward, which shows up as a sharp, misleading drop-off.
    monthly_sales = monthly_sales[
        monthly_sales["order_month"] < pd.Timestamp("2018-09-01")
    ]

    # --------------------------------------------------------
    # PEAK (NOV 2017) -> AUG 2018 DROP
    # --------------------------------------------------------

    peak_row = monthly_sales[
        monthly_sales["order_month"] == pd.Timestamp("2017-11-01")
    ]
    latest_row = monthly_sales[
        monthly_sales["order_month"] == pd.Timestamp("2018-08-01")
    ]

    if not peak_row.empty and not latest_row.empty:

        peak_orders = peak_row["order_count"].iloc[0]
        peak_revenue = peak_row["total_revenue"].iloc[0]
        latest_orders = latest_row["order_count"].iloc[0]
        latest_revenue = latest_row["total_revenue"].iloc[0]

        order_drop_pct = (peak_orders - latest_orders) / peak_orders * 100
        revenue_drop_pct = (peak_revenue - latest_revenue) / peak_revenue * 100

        st.markdown(
            f"<div style='text-align: center; font-size: 1.4em;'>"
            f"Order volume and revenue peaked in <b>November 2017</b>, then fell "
            f"<b>{order_drop_pct:.0f}%</b> in order volume and "
            f"<b>{revenue_drop_pct:.0f}%</b> in revenue by <b>August 2018</b>."
            f"</div>",
            unsafe_allow_html=True
        )

    else:

        st.write(
            "How are order volume and revenue changing over time?"
        )

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Monthly order volume")

        fig_orders = go.Figure(go.Scatter(
            x=monthly_sales["order_month"],
            y=monthly_sales["order_count"],
            mode="lines",
            line=dict(color="#1f77b4", width=2),
            fill="tozeroy",
            fillcolor="rgba(13, 58, 97, 0.25)"
        ))
        fig_orders.update_layout(
            height=350,
            margin=dict(t=10, l=10, r=10, b=10),
            xaxis_title=None,
            yaxis_title="Orders"
        )

        st.plotly_chart(fig_orders, use_container_width=True)

        st.caption(
            "Number of orders placed each month (through August 2018)."
        )

    with col2:

        st.subheader("Monthly revenue")

        fig_revenue = go.Figure(go.Scatter(
            x=monthly_sales["order_month"],
            y=monthly_sales["total_revenue"],
            mode="lines",
            line=dict(color="#1f77b4", width=2),
            fill="tozeroy",
            fillcolor="rgba(13, 58, 97, 0.25)"
        ))
        fig_revenue.update_layout(
            height=350,
            margin=dict(t=10, l=10, r=10, b=10),
            xaxis_title=None,
            yaxis_title="Revenue"
        )

        st.plotly_chart(fig_revenue, use_container_width=True)

        st.caption(
            "Total order revenue generated each month (through August 2018)."
        )


# ============================================================
# TAB 2 — DELIVERY PERFORMANCE
# ============================================================

with tab3:

    st.header("Delivery Performance")

    st.write(
        "Business Question: How well is the delivery network performing?"
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
        size_max=60,
        color="customer_state",
        hover_name="customer_state",
        hover_data={
            "late_delivery_pct_display": ":.1f",
            "total_revenue": ":,.0f",
            "total_orders": ":,",
            "late_orders": ":,",
            "late_revenue": ":,.0f",
            "late_delivery_pct": False,
            "late_revenue_pct": ":.1%",
            "customer_state": False
        },
        labels={
            "late_delivery_pct_display": "Late delivery rate (%)",
            "total_revenue": "Total revenue",
            "total_orders": "Orders",
            "late_revenue_pct": "Late revenue share",
            "customer_state": "State"
        },
        title="Which high-revenue states have higher delivery risk?"
    )
    fig_scatter.update_layout(showlegend=False)

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
# TAB 4 — CUSTOMER SATISFACTION
# ============================================================

with tab4:

    st.header("Customer Satisfaction")

    st.write(
        "Business Question: Does delivery performance relate "
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
        "Business Question: How well are sellers fulfilling orders?"
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

# ============================================================
# TAB 5 — DELAY ROOT CAUSE
# ============================================================

with tab5:

    st.header("Delay Root Cause")

    st.write(
        "Business Question: Which stage causes the most delay, "
        "and does distance or product size make it worse?"
    )

    # --------------------------------------------------------
    # SECTION 1 -- WHICH STAGE CAUSES THE MOST DELAY
    # --------------------------------------------------------

    st.subheader("81.6% of delays in the delivery process happen in transit.")

    delay_stages = query(f"""
        SELECT
            stage,
            total_days,
            pct_of_delay
        FROM `{REPORTING_DATASET}.mart_delivery_delay_stages`
    """)

    stage_labels = {
        "approval": "Approval",
        "seller_handling": "Seller handling",
        "transit": "Transit"
    }
    stage_order = ["approval", "seller_handling", "transit"]

    delay_stages["stage"] = pd.Categorical(
        delay_stages["stage"], categories=stage_order, ordered=True
    )
    delay_stages = delay_stages.sort_values("stage")
    delay_stages["stage_label"] = delay_stages["stage"].astype(str).map(stage_labels)
    delay_stages["pct_display"] = delay_stages["pct_of_delay"] * 100

    fig_stages = px.bar(
        delay_stages,
        x="pct_display",
        y="stage_label",
        orientation="h",
        text=delay_stages["pct_display"].round(1).astype(str) + "%",
        labels={"stage_label": "Delivery stage", "pct_display": "Share of total delay (%)"},
        title="Share of total delay days, by stage (late orders only)"
    )
    fig_stages.update_traces(textposition="outside")
    fig_stages.update_layout(height=350, xaxis_range=[0, 100])
    fig_stages.update_yaxes(categoryorder="array", categoryarray=delay_stages["stage_label"].tolist()[::-1])

    st.plotly_chart(fig_stages, use_container_width=True)

    st.caption(
        "Transit consistently accounts for the majority of delay days across "
        "late orders. Seller handling and approval delays are comparatively small."
    )

    st.divider()

    # --------------------------------------------------------
    # SECTION 2 -- DOES DISTANCE OR PRODUCT SIZE MAKE DELAY WORSE
    # --------------------------------------------------------

    st.subheader("Does shipping distance or product size make delay worse?")

    st.markdown(
        "<div style='font-size: 2.0em;'>"
        "There is a correlation between delays and both product size and distance."
        "</div>",
        unsafe_allow_html=True
    )


    dist_size = query(f"""
        SELECT
            distance_bucket,
            size_bucket,
            order_item_count,
            late_pct
        FROM `{REPORTING_DATASET}.mart_delay_pdt_vs_dist`
    """)

    zone_order = ["Zone 1", "Zone 2", "Zone 3", "Zone 4"]
    size_order = ["S", "M", "L", "XL", "Too Large or Too Heavy for Delivery"]

    dist_size["distance_bucket"] = pd.Categorical(
        dist_size["distance_bucket"], categories=zone_order, ordered=True
    )
    dist_size["size_bucket"] = pd.Categorical(
        dist_size["size_bucket"],
        categories=[s for s in size_order if s in dist_size["size_bucket"].unique()],
        ordered=True
    )
    dist_size = dist_size.sort_values(["distance_bucket", "size_bucket"])
    dist_size["late_pct_display"] = dist_size["late_pct"] * 100

    # ---- interactive filters ----

    available_zones = [z for z in zone_order if z in dist_size["distance_bucket"].unique()]
    available_sizes = [s for s in size_order if s in dist_size["size_bucket"].unique()]

    col_f1, col_f2 = st.columns(2)

    with col_f1:
        selected_zones = st.multiselect(
            "Distance zones to include: Zone 1: \u2264100km, Zone 2: 100\u2013500km, "
            "Zone 3: 500\u20131500km, Zone 4: >1500km",
            options=available_zones,
            default=available_zones,
            key="delay_dist_zone_filter"
        )

    with col_f2:
        selected_sizes = st.multiselect(
            "Size buckets to include",
            options=available_sizes,
            default=available_sizes,
            key="delay_dist_size_filter"
        )

    filtered = dist_size[
        dist_size["distance_bucket"].isin(selected_zones)
        & dist_size["size_bucket"].isin(selected_sizes)
    ].copy()

    if filtered.empty:
        st.warning("No data for the selected filters — pick at least one zone and one size bucket.")
    else:

        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:

            st.markdown("**Heatmap — late % by zone and size**")

            heatmap_data = filtered.pivot(
                index="distance_bucket", columns="size_bucket", values="late_pct_display"
            )

            fig_heatmap = px.imshow(
                heatmap_data,
                text_auto=".1f",
                color_continuous_scale="Reds",
                labels=dict(x="Size bucket", y="Distance zone", color="Late %"),
                aspect="auto"
            )
            fig_heatmap.update_layout(height=450)

            st.plotly_chart(fig_heatmap, use_container_width=True)

        with col_chart2:

            st.markdown("**Grouped bar — late % by zone, split by size**")

            fig_grouped = px.bar(
                filtered,
                x="distance_bucket",
                y="late_pct_display",
                color="size_bucket",
                barmode="group",
                labels={
                    "distance_bucket": "Distance zone",
                    "late_pct_display": "Late %",
                    "size_bucket": "Size bucket"
                }
            )
            fig_grouped.update_layout(height=450)

            st.plotly_chart(fig_grouped, use_container_width=True)

        st.caption(
            "Both charts show the same underlying data: the late-item percentage "
            "for each distance zone / product-size combination. The biggest single "
            "jump is size (S to XL) at Zone 1, suggesting product size is the "
            "stronger single lever, especially for local deliveries though both "
            "factors' effects shrink once the other is already at its worst level."
        )

        with st.expander("View underlying data"):
            display_dist_size = filtered[
                ["distance_bucket", "size_bucket", "order_item_count", "late_pct_display"]
            ].rename(columns={
                "distance_bucket": "Distance zone",
                "size_bucket": "Size bucket",
                "order_item_count": "Order items",
                "late_pct_display": "Late %"
            })
            display_dist_size["Late %"] = display_dist_size["Late %"].round(1)
            st.dataframe(display_dist_size, hide_index=True, use_container_width=True)


    st.divider()

    # --------------------------------------------------------
    # SECTION 3 -- WHAT DRIVES TRANSIT TIME BEYOND DISTANCE ALONE
    # --------------------------------------------------------

    st.subheader("What drives transit time beyond distance alone?")

    st.markdown(
        "<div style='font-size: 2.0em;'>"
        "Seller's consistently slow handoff time adds to the overall delay."
        "</div>",
        unsafe_allow_html=True
    )

    transit_drivers = query(f"""
        SELECT
            order_shape,
            distance_band,
            order_count,
            pct_of_orders,
            avg_transit_days,
            avg_seller_handling_days,
            late_pct
        FROM `{REPORTING_DATASET}.mart_transit_drivers`
    """)

    transit_drivers = transit_drivers[transit_drivers["distance_band"] != "4. unknown"]
    # Unclassified bars rest on ~14 delivered orders; shown in the expander below instead.
    transit_drivers = transit_drivers[transit_drivers["order_shape"] != "unclassified"]

    distance_order = ["1. same_city", "2. same_state", "3. cross_state"]
    distance_labels = {
        "1. same_city": "Same city",
        "2. same_state": "Same state",
        "3. cross_state": "Cross-state"
    }
    shape_order = [
        "single_seller_normal_handoff",
        "single_seller_slow_handoff",
        "multi_seller",
        "unclassified"
    ]
    shape_labels = {
        "single_seller_normal_handoff": "Single seller (normal handoff)",
        "single_seller_slow_handoff": "Single seller (slow handoff)",
        "multi_seller": "Multi-seller",
        "unclassified": "Unclassified"
    }

    transit_drivers["distance_band"] = pd.Categorical(
        transit_drivers["distance_band"],
        categories=[d for d in distance_order if d in transit_drivers["distance_band"].unique()],
        ordered=True
    )
    transit_drivers["order_shape"] = pd.Categorical(
        transit_drivers["order_shape"],
        categories=[s for s in shape_order if s in transit_drivers["order_shape"].unique()],
        ordered=True
    )
    transit_drivers = transit_drivers.sort_values(["distance_band", "order_shape"])

    transit_drivers["distance_band_label"] = transit_drivers["distance_band"].astype(str).map(distance_labels)
    transit_drivers["order_shape_label"] = transit_drivers["order_shape"].astype(str).map(shape_labels)
    transit_drivers["pct_of_orders_display"] = transit_drivers["pct_of_orders"] * 100
    transit_drivers["late_pct_display"] = transit_drivers["late_pct"] * 100

    shape_color_map = {
        "Single seller (normal handoff)": "green",
        "Single seller (slow handoff)": "red",
        "Multi-seller": "blue",
        "Unclassified": "grey"
    }

    fig_transit = px.bar(
        transit_drivers,
        x="distance_band_label",
        y="avg_transit_days",
        color="order_shape_label",
        barmode="group",
        color_discrete_map=shape_color_map,
        labels={
            "distance_band_label": "Distance band",
            "avg_transit_days": "Avg transit days",
            "order_shape_label": "Order shape"
        },
        title="Average transit time by fulfillment shape, within each distance band"
    )
    fig_transit.update_layout(height=480)

    st.plotly_chart(fig_transit, use_container_width=True)

    st.caption(
        "Compare bars *within* the same distance band (same x-axis position) that "
        "isolates the effect of how an order was fulfilled from the effect of how far "
        "it had to travel or due to product size."
    )

    with st.expander("View order volume and late % by segment"):
        display_transit = transit_drivers[
            [
                "distance_band_label", "order_shape_label", "order_count",
                "pct_of_orders_display", "avg_seller_handling_days", "late_pct_display"
            ]
        ].rename(columns={
            "distance_band_label": "Distance band",
            "order_shape_label": "Order shape",
            "order_count": "Orders",
            "pct_of_orders_display": "% of all orders",
            "avg_seller_handling_days": "Avg seller handling days",
            "late_pct_display": "Late %"
        })
        display_transit["% of all orders"] = display_transit["% of all orders"].round(1)
        display_transit["Avg seller handling days"] = display_transit["Avg seller handling days"].round(2)
        display_transit["Late %"] = display_transit["Late %"].round(1)
        st.dataframe(display_transit, hide_index=True, use_container_width=True)

    st.caption(
        "Order volume (% of all orders), slow seller handoff could be one of the underlying issue for delivery transits."
    )

    # --------------------------------------------------------
    # LATE % BY ORDER SHAPE
    # --------------------------------------------------------

    fig_late = px.bar(
        transit_drivers,
        x="distance_band_label",
        y="late_pct_display",
        color="order_shape_label",
        barmode="group",
        color_discrete_map=shape_color_map,
        text=transit_drivers["late_pct_display"].round(1).astype(str) + "%",
        labels={
            "distance_band_label": "Distance band",
            "late_pct_display": "Late %",
            "order_shape_label": "Order shape"
        },
        title="Late % by order shape, within each distance band"
    )
    fig_late.update_traces(textposition="outside")
    fig_late.update_layout(height=480)

    st.plotly_chart(fig_late, use_container_width=True)

    st.caption(
        "Late % = share of delivered orders that arrived after the estimated delivery date "
        "Olist showed the customer at purchase. Undelivered orders are excluded. Slow "
        "handoff barely changes transit time above, but it multiplies the late rate: the "
        "delay happens before the parcel reaches the carrier."
    )

    # --------------------------------------------------------
    # UNCLASSIFIED ORDERS
    # --------------------------------------------------------

    with st.expander("View unclassified orders (excluded from the charts above)"):
        unclassified = query(f"""
            SELECT
                distance_band,
                unclassified_reason,
                order_status,
                order_count,
                delivered_order_count,
                avg_transit_days
            FROM `{REPORTING_DATASET}.mart_transit_unclassified`
        """)

        reason_labels = {
            "no_items_on_order": "No items on order",
            "never_approved_or_shipped": "Never approved or shipped",
            "approval_timestamp_missing": "Approval timestamp missing",
            "never_handed_to_carrier": "Never handed to carrier"
        }
        all_distance_labels = {**distance_labels, "4. unknown": "Unknown (no seller)"}

        total_unclassified = int(unclassified["order_count"].sum())
        total_delivered = int(unclassified["delivered_order_count"].sum())

        st.markdown(
            f"**{total_unclassified:,} orders** could not be classified because no seller "
            f"handoff could be measured. Only **{total_delivered:,}** of them were delivered "
            f"with a transit time, which is too few to plot alongside the other segments."
        )

        by_reason = (
            unclassified.groupby("unclassified_reason", as_index=False)[
                ["order_count", "delivered_order_count"]
            ].sum()
            .sort_values("order_count", ascending=False)
        )
        by_reason["unclassified_reason"] = by_reason["unclassified_reason"].map(reason_labels)
        st.dataframe(
            by_reason.rename(columns={
                "unclassified_reason": "Reason",
                "order_count": "Orders",
                "delivered_order_count": "Delivered (has transit time)"
            }),
            hide_index=True,
            use_container_width=True
        )

        detail = unclassified.copy()
        detail["distance_band"] = detail["distance_band"].map(all_distance_labels)
        detail["unclassified_reason"] = detail["unclassified_reason"].map(reason_labels)
        detail["avg_transit_days"] = detail["avg_transit_days"].round(1)
        st.dataframe(
            detail.rename(columns={
                "distance_band": "Distance band",
                "unclassified_reason": "Reason",
                "order_status": "Order status",
                "order_count": "Orders",
                "delivered_order_count": "Delivered",
                "avg_transit_days": "Avg transit days"
            }),
            hide_index=True,
            use_container_width=True
        )
    
