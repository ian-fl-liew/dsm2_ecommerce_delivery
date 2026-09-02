-- 1 row per product_id. Note: Olist mints a new product_id per order — the repeat-product identity is product_unique_id. This starter keys dim_product on product_id (order-scoped location snapshot); a repeat-product analysis would need to key on product_unique_id instead.
select
    p.product_id,
    p.product_category_name,
    t.product_category_name_english,
    p.product_name_lenght,
    p.product_description_lenght,
    p.product_photos_qty,
    p.product_weight_g,
    p.product_length_cm,
    p.product_height_cm,
    p.product_width_cm
from {{ source('olist_raw', 'products') }} as p
left join {{ source('olist_raw', 'product_category_name_translation') }} as t
    on p.product_category_name = t.product_category_name