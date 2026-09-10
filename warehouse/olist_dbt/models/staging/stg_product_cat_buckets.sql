SELECT 
    *,
    -- Creates bigger product category buckets for analysis
    CASE 
        -- 1. Electronics & Technology
        WHEN product_category_name_english IN (
            'audio', 'computers', 'computers_accessories', 'consoles_games', 
            'electronics', 'fixed_telephony', 'telephony', 'tablets_printing_image'
        ) THEN 'Electronics & Technology'

        -- 2. Home, Living & Furniture
        WHEN product_category_name_english IN (
            'air_conditioning', 'bed_bath_table', 'furniture_bedroom', 'furniture_decor', 
            'furniture_living_room', 'furniture_mattress_and_upholstery', 'home_appliances', 
            'home_appliances_2', 'home_confort', 'home_comfort_2', 'housewares', 
            'kitchen_dining_laundry_garden_furniture', 'la_cuisine', 'office_furniture', 
            'small_appliances', 'small_appliances_home_oven_and_coffee'
        ) THEN 'Home, Living & Furniture'

        -- 3. Fashion, Luggage & Watches
        WHEN product_category_name_english IN (
            'fashion_bags_accessories', 'fashion_childrens_clothes', 'fashio_female_clothing', 
            'fashion_male_clothing', 'fashion_shoes', 'fashion_sport', 'fashion_underwear_beach', 
            'luggage_accessories', 'watches_gifts'
        ) THEN 'Fashion, Luggage & Watches'

        -- 4. Health, Beauty & Baby
        WHEN product_category_name_english IN (
            'baby', 'diapers_and_hygiene', 'health_beauty', 'perfumery'
        ) THEN 'Health, Beauty & Baby'

        -- 5. Home Improvement (Construction), Garden & Pets
        WHEN product_category_name_english IN (
            'construction_tools_construction', 'costruction_tools_garden', 'construction_tools_lights', 
            'construction_tools_safety', 'costruction_tools_tools', 'flowers', 
            'garden_tools', 'home_construction', 'pet_shop'
        ) THEN 'Home Improvement (Construction), Garden & Pets'

        -- 6. Books, Media & Hobbies
        WHEN product_category_name_english IN (
            'art', 'arts_and_craftmanship', 'books_general_interest', 'books_imported', 
            'books_technical', 'cds_dvds_musicals', 'cine_photo', 'cool_stuff', 
            'dvds_blu_ray', 'music', 'musical_instruments', 'sports_leisure', 
            'stationery', 'toys'
        ) THEN 'Books, Media & Hobbies'

        -- 7. Food, Beverage & Party
        WHEN product_category_name_english IN (
            'drinks', 'food', 'food_drink', 'party_supplies', 'christmas_supplies'
        ) THEN 'Food, Beverage & Party'

        -- 8. Automotive, Industrial & B2B
        WHEN product_category_name_english IN (
            'auto', 'agro_industry_and_commerce', 'industry_commerce_and_business', 
            'market_place', 'security_and_services', 'signaling_and_security'
        ) THEN 'Automotive, Industrial & B2B'

        ELSE 'Uncategorized'
    END AS product_category_buckets

FROM {{ source('olist_raw', 'product_category_name_translation') }}