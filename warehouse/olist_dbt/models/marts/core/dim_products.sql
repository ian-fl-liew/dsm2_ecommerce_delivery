select
    product_id,
    product_category_name,
    product_category_name_english,
    product_category_buckets,
    product_name_length,
    product_description_length,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm,
    (product_length_cm + product_height_cm + product_width_cm) as product_dimension,
    (product_length_cm * product_height_cm * product_width_cm) as product_volume
from {{ ref('stg_products') }} 