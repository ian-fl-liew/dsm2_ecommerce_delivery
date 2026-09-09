-- 1 row per product_id. Note: Olist mints a new product_id per order — the repeat-product identity is product_unique_id. This starter keys dim_product on product_id (order-scoped location snapshot); a repeat-product analysis would need to key on product_unique_id instead.
with prepared_products as (
    select
        product_id,
        -- Replaces NULL values with 'uncategorized'
        coalesce(product_category_name, 'uncategorized') as product_category_name,
        -- Standardizing the Olist dataset typos here
        product_name_lenght as product_name_length,
        product_description_lenght as product_description_length,
        product_photos_qty,
        product_weight_g,
        product_length_cm,
        product_height_cm,
        product_width_cm
    from {{ source('olist_raw', 'products') }}
)

select
    p.product_id,
    p.product_category_name,
    -- Handles nulls from the translation table
    coalesce(t.product_category_name_english, 'uncategorized') as product_category_name_english,
    coalesce(t.product_category_buckets, 'Uncategorized') as product_category_buckets,
    p.product_name_length,
    p.product_description_length,
    p.product_photos_qty,
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm
from prepared_products as p
left join {{ ref('stg_product_cat_buckets') }} as t
    on p.product_category_name = t.product_category_name