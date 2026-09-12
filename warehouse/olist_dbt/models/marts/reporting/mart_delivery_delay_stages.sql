-- Business Question 5: Which stage causes the most delay? 
-- (Stages defined as: Approval delay, Seller Handling Delay or Transportation?)

-- Grain: One row per stage

-- Selecting all columns related to delays
WITH delivery_delay_stage AS (
    SELECT
        order_id,
        approval_delay_days,
        seller_handling_days,
        transit_days,
        delivery_status
    FROM {{ ref('fact_orders') }}
    -- fact_orders is item grain and the stage metrics are order-level, so
    -- is_order_header_row collapses to one row per order before the SUMs below.
    WHERE delivery_status LIKE 'late%'
      AND is_order_header_row
),

-- Aggregate all same stage delays into one grand total
stage_totals AS (
    SELECT
    SUM(dds.approval_delay_days) AS approval_delay,
    SUM(dds.seller_handling_days) AS seller_delay,
    SUM(dds.transit_days) AS transit_delay
FROM delivery_delay_stage AS dds
)

-- Convert shape, 3 columns of stages to 3 rows (One order per stage)
SELECT
    'approval' AS stage,
    approval_delay AS total_days,
    SAFE_DIVIDE(approval_delay, approval_delay + seller_delay + transit_delay) AS pct_of_delay
FROM stage_totals

UNION ALL

SELECT
    'seller_handling' AS stage,
    seller_delay AS total_days,
    SAFE_DIVIDE(seller_delay, approval_delay + seller_delay + transit_delay) AS pct_of_delay
FROM stage_totals

UNION ALL

SELECT
    'transit' AS stage,
    transit_delay AS total_days,
    SAFE_DIVIDE(transit_delay,  approval_delay + seller_delay + transit_delay) AS pct_of_delay
FROM stage_totals
