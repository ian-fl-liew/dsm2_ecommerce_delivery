-- one row per order line item
-- stg_order_items (seller_id) --> dim_seller (seller_id) --> dim_geolocation (seller_zip_code_prefix) --> lat, lng values
-- stg_order_items (order_id) --> fact_orders (order_id + customer_id) --> dim_customer (customer_id) --> dim_geolocation (customer_zip_code_prefix) --> lat, lng values
-- need alias for seller, customer, for each dim_geolocation link to avoid SQL confusion

SELECT DISTINCT
    oi.order_id,
    oi.seller_id,
    seller_geo.centroid_lat as seller_lat,
    seller_geo.centroid_lng as seller_lng,
    customer_geo.centroid_lat as customer_lat,
    customer_geo.centroid_lng as customer_lng,
    ST_DISTANCE(
        ST_GEOGPOINT(seller_geo.centroid_lng, seller_geo.centroid_lat),
        ST_GEOGPOINT(customer_geo.centroid_lng, customer_geo.centroid_lat)
    ) AS distance_meters
FROM {{ ref('stg_order_items') }} AS oi
JOIN {{ ref('dim_seller') }} AS s ON oi.seller_id = s.seller_id
JOIN {{ ref('dim_geolocation') }} AS seller_geo ON s.seller_zip_code_prefix = seller_geo.zip_code_prefix
JOIN {{ ref('fact_orders') }} AS f ON oi.order_id = f.order_id
JOIN {{ ref('dim_customer') }} AS c ON f.customer_id = c.customer_id
JOIN {{ ref('dim_geolocation') }} AS customer_geo ON c.customer_zip_code_prefix = customer_geo.zip_code_prefix

