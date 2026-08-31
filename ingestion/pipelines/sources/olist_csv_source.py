"""dlt source: reads the Kaggle Olist CSVs downloaded locally by
scripts/download_dataset.py and yields one dlt resource per file.

Filenames match the Kaggle export as-is; dbt staging models handle renaming/typing
from here, not this source.
"""
from pathlib import Path

import dlt
import pandas as pd

TABLE_FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "product_category_name_translation": "product_category_name_translation.csv",
}


@dlt.source
def olist_csv_source(data_dir: str = "data/raw"):
    """Only yields a resource for tables whose CSV is actually present in data_dir —
    lets the team land more tables over time (sellers, products, geolocation, ...) just
    by copying more files into data/raw/, no code change needed.
    """
    data_path = Path(data_dir)

    def make_resource(table_name: str, filename: str):
        @dlt.resource(name=table_name, write_disposition="replace")
        def _resource():
            yield pd.read_csv(data_path / filename)

        return _resource

    return [
        make_resource(name, filename)
        for name, filename in TABLE_FILES.items()
        if (data_path / filename).exists()
    ]
