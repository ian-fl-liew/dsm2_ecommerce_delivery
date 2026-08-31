"""Wraps warehouse/olist_dbt as Dagster assets — one asset per dbt model, with lineage
and column-level metadata pulled straight from the dbt manifest. Runs `dbt build`
(models + tests) rather than just `dbt run`.
"""
from pathlib import Path

import dagster as dg
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

DBT_PROJECT_DIR = Path(__file__).parents[3] / "warehouse" / "olist_dbt"

dbt_project = DbtProject(project_dir=DBT_PROJECT_DIR)
dbt_project.prepare_if_dev()


@dbt_assets(manifest=dbt_project.manifest_path)
def olist_dbt_assets(context: dg.AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()
