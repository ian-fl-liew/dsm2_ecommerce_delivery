-- raw record, one row per record, not yet collapsed to one row per prefix

SELECT
    geolocation_zip_code_prefix AS zip_code_prefix,
    geolocation_lat AS latitude,
    geolocation_lng AS longitude,
    geolocation_city AS city,
    geolocation_state AS state
FROM {{ source('olist_raw', 'geolocation') }}