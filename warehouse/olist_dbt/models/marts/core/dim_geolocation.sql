WITH city_state_counts AS (
    SELECT
        zip_code_prefix,
        city,
        state,
        COUNT(*) AS occurence_count
    FROM {{ ref('stg_geolocation')}}
    GROUP BY zip_code_prefix, city, state
),

-- find the MODE (most occurence) from city_state_counts
mode_city_state AS (
    SELECT
        zip_code_prefix,
        city,
        state
    FROM city_state_counts
    QUALIFY row_number() OVER (PARTITION BY zip_code_prefix ORDER BY occurence_count DESC) = 1
),

-- using zip_code_prefix, get geography values (lng, lat)
centroid AS (
    SELECT
        zip_code_prefix,
        ST_CENTROID(ST_UNION_AGG(ST_GEOGPOINT(longitude, latitude))) AS geog_value
    FROM {{ ref('stg_geolocation')}}
    GROUP BY zip_code_prefix
)

SELECT
    m.zip_code_prefix,
    m.city,
    m.state,
    ST_X(c.geog_value) AS centroid_lng,
    ST_Y(c.geog_value) AS centroid_lat
FROM mode_city_state as m
LEFT JOIN centroid as c on m.zip_code_prefix = c.zip_code_prefix