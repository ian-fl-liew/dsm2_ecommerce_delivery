"""Validate that every row in the source CSVs actually landed in MongoDB and BigQuery.

The pipeline is two hops -- CSV -> MongoDB `olist_landing` -> BigQuery `olist_raw` (there is
no direct CSV -> BigQuery path; see orchestration/olist_orchestration/assets/ingestion.py).
A row can therefore be lost or mangled at either hop, so this checks all three layers and
reports WHICH hop broke rather than just that the totals disagree.

    python scripts/validate_ingestion.py                      # all tables, standard checks
    python scripts/validate_ingestion.py --tables orders,products
    python scripts/validate_ingestion.py --deep               # + full key-set fingerprint
    python scripts/validate_ingestion.py --skip-mongo         # CSV vs BigQuery only
    python scripts/validate_ingestion.py --json report.json   # machine-readable output

Exits 1 if any check fails, so it can gate a CI step.

Checks per table:
  row_count       CSV == Mongo == BigQuery, exactly
  columns         every CSV column present in both destinations
  missing_values  per-column missing count matches across layers
  distinct_keys   distinct natural-key count matches (catches dupes AND drops that a
                  plain row count would cancel out against each other)
  numeric_totals  sum of each numeric column matches within float tolerance
  key_fingerprint --deep only: sha256 over the sorted key set, CSV vs each destination.
                  This is the only check that proves the SAME rows arrived rather than
                  merely the same number of them.

WHY MISSING VALUES NEED CARE. pandas turns blank CSV fields into NaN floats, and
csv_to_mongo_pipeline inserts those verbatim -- so in MongoDB a missing value is a NaN
double, NOT a BSON null. Querying {field: None} there returns 0 and a naive null check
would pass while telling you nothing. dlt then converts NaN to a real NULL on the way into
BigQuery. "Missing" is therefore defined per layer: NaN in pandas, null-or-NaN-or-absent in
Mongo, IS NULL in BigQuery.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
import sys
import tomllib
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]

# Source of truth for these lives in the ingestion code; read rather than duplicated so a
# new table added there is picked up here automatically.
CSV_SOURCE = REPO_ROOT / "ingestion" / "pipelines" / "sources" / "olist_csv_source.py"
MONGO_PIPELINE = REPO_ROOT / "ingestion" / "pipelines" / "csv_to_mongo_pipeline.py"
BQ_PIPELINE = REPO_ROOT / "ingestion" / "pipelines" / "mongo_to_bigquery_pipeline.py"
SECRETS_PATH = REPO_ROOT / "ingestion" / ".dlt" / "secrets.toml"

# Columns the pipeline adds that have no CSV counterpart: Mongo's ObjectId and dlt's
# bookkeeping. Excluded from column/missing comparisons.
ARTIFACT_COLUMNS = {"_id", "_dlt_id", "_dlt_load_id"}

# Natural keys, used for the distinct-count and fingerprint checks. These are the source's
# own grain -- NOT an assertion that they are unique (Olist's order_reviews genuinely
# repeats review_id). The check is that each layer agrees with the CSV, so real source
# duplicates must survive the trip too.
NATURAL_KEYS: dict[str, list[str] | None] = {
    "orders": ["order_id"],
    "order_items": ["order_id", "order_item_id"],
    "order_payments": ["order_id", "payment_sequential"],
    "order_reviews": ["review_id", "order_id"],
    "customers": ["customer_id"],
    "sellers": ["seller_id"],
    "products": ["product_id"],
    "product_category_name_translation": ["product_category_name"],
    # geolocation has no natural key in the source (repeated zip prefixes are legitimate),
    # so it is validated on counts, missing values and numeric totals only.
    "geolocation": None,
}

NULL_SENTINEL = "\x00NULL\x00"  # distinguishes a real null from the string "None"
KEY_SEP = "\x01"
FLOAT_REL_TOL = 1e-9
FLOAT_ABS_TOL = 1e-6


def module_constant(path: Path, name: str):
    """Read a module-level literal without importing the module.

    Importing olist_csv_source would pull in dlt, and csv_to_mongo_pipeline would pull in
    pymongo -- neither is needed when running with --skip-mongo or --skip-bq, and a
    validator should not fail because an unrelated dependency is missing.
    """
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return ast.literal_eval(node.value)
    raise KeyError(f"{name} not found in {path}")


TABLE_FILES: dict[str, str] = module_constant(CSV_SOURCE, "TABLE_FILES")
MONGO_DATABASE: str = module_constant(MONGO_PIPELINE, "DATABASE_NAME")
BQ_DATASET: str = module_constant(BQ_PIPELINE, "DATASET_NAME")


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def key_string(values) -> str:
    parts = []
    for v in values:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            parts.append(NULL_SENTINEL)
        elif isinstance(v, float) and v.is_integer():
            # 1.0 from a float64 column must match the "1" BigQuery returns for an INT64.
            parts.append(str(int(v)))
        else:
            parts.append(str(v))
    return KEY_SEP.join(parts)


def fingerprint(keys) -> str:
    h = hashlib.sha256()
    for k in sorted(keys):
        h.update(k.encode())
        h.update(b"\n")
    return h.hexdigest()


def floats_match(a, b) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return math.isclose(float(a), float(b), rel_tol=FLOAT_REL_TOL, abs_tol=FLOAT_ABS_TOL)


# --------------------------------------------------------------------------------------
# per-layer probes -- each returns the same shape so they can be compared directly
# --------------------------------------------------------------------------------------
def probe_csv(table: str, deep: bool) -> dict:
    df = pd.read_csv(REPO_ROOT / "data" / "raw" / TABLE_FILES[table])
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    keys = NATURAL_KEYS.get(table)

    out = {
        "row_count": int(len(df)),
        "columns": list(df.columns),
        "numeric_columns": numeric,
        "missing": {c: int(df[c].isna().sum()) for c in df.columns},
        "sums": {c: (None if df[c].isna().all() else float(df[c].sum())) for c in numeric},
        "distinct_keys": None,
        "fingerprint": None,
    }
    if keys:
        key_series = [key_string(row) for row in df[keys].itertuples(index=False, name=None)]
        out["distinct_keys"] = len(set(key_series))
        if deep:
            out["fingerprint"] = fingerprint(set(key_series))
    return out


def probe_mongo(table: str, columns: list[str], numeric: list[str],
                keys: list[str] | None, deep: bool) -> dict:
    from pymongo import MongoClient

    url = tomllib.loads(SECRETS_PATH.read_text())["destination"]["mongodb"]["connection_url"]
    db = MongoClient(url, serverSelectionTimeoutMS=30000)[MONGO_DATABASE]
    if table not in db.list_collection_names():
        return {"error": f"collection '{table}' does not exist in {MONGO_DATABASE}"}
    coll = db[table]

    def missing_expr(col: str):
        # A value is missing if the field is absent, BSON null, or a NaN double. The NaN
        # arm is the one that matters: see the module docstring.
        return {"$or": [
            {"$eq": [{"$type": f"${col}"}, "missing"]},
            {"$eq": [f"${col}", None]},
            {"$eq": [f"${col}", float("nan")]},
        ]}

    group: dict = {"_id": None, "row_count": {"$sum": 1}}
    for col in columns:
        group[f"null__{col}"] = {"$sum": {"$cond": [missing_expr(col), 1, 0]}}
    for col in numeric:
        # Guard the NaN, otherwise it poisons the whole sum.
        group[f"sum__{col}"] = {"$sum": {"$cond": [missing_expr(col), 0, f"${col}"]}}

    agg = list(coll.aggregate([{"$group": group}], allowDiskUse=True))
    row = agg[0] if agg else {"row_count": 0}

    out = {
        "row_count": int(row.get("row_count", 0)),
        "columns": sorted(set(coll.find_one() or {}) - ARTIFACT_COLUMNS),
        "missing": {c: int(row.get(f"null__{c}", 0)) for c in columns},
        "sums": {c: row.get(f"sum__{c}") for c in numeric},
        "distinct_keys": None,
        "fingerprint": None,
    }
    if keys:
        pipeline = [{"$group": {"_id": {k: f"${k}" for k in keys}}}, {"$count": "n"}]
        res = list(coll.aggregate(pipeline, allowDiskUse=True))
        out["distinct_keys"] = int(res[0]["n"]) if res else 0
        if deep:
            projection = {k: 1 for k in keys}
            projection["_id"] = 0
            out["fingerprint"] = fingerprint(
                {key_string([doc.get(k) for k in keys]) for doc in coll.find({}, projection)}
            )
    return out


def probe_bigquery(table: str, columns: list[str], numeric: list[str],
                   keys: list[str] | None, deep: bool, project: str) -> dict:
    from google.cloud import bigquery

    client = bigquery.Client(project=project)
    fq = f"`{project}.{BQ_DATASET}.{table}`"

    try:
        schema = client.get_table(f"{project}.{BQ_DATASET}.{table}").schema
    except Exception as exc:  # noqa: BLE001 -- surfaced as a finding, not a crash
        return {"error": f"BigQuery table {BQ_DATASET}.{table} unreadable: {exc}"}

    present = {f.name for f in schema}
    selects = ["COUNT(*) AS row_count"]
    for col in columns:
        if col in present:
            selects.append(f"COUNTIF(`{col}` IS NULL) AS `null__{col}`")
    for col in numeric:
        if col in present:
            selects.append(f"SUM(`{col}`) AS `sum__{col}`")
    if keys and all(k in present for k in keys):
        parts = ", ".join(
            f"IFNULL(CAST(`{k}` AS STRING), '{NULL_SENTINEL}')" for k in keys
        )
        selects.append(
            f"COUNT(DISTINCT CONCAT({parts})) AS distinct_keys"
            if len(keys) == 1
            else f"COUNT(DISTINCT ARRAY_TO_STRING([{parts}], '{KEY_SEP}')) AS distinct_keys"
        )

    row = dict(next(iter(client.query(f"SELECT {', '.join(selects)} FROM {fq}").result())))

    out = {
        "row_count": int(row["row_count"]),
        "columns": sorted(present - ARTIFACT_COLUMNS),
        "missing": {c: row.get(f"null__{c}") for c in columns},
        "sums": {c: row.get(f"sum__{c}") for c in numeric},
        "distinct_keys": row.get("distinct_keys"),
        "fingerprint": None,
    }
    if deep and keys and all(k in present for k in keys):
        cols = ", ".join(f"`{k}`" for k in keys)
        rows = client.query(f"SELECT DISTINCT {cols} FROM {fq}").result()
        out["fingerprint"] = fingerprint(
            {key_string([r[k] for k in keys]) for r in rows}
        )
    return out


# --------------------------------------------------------------------------------------
# comparison
# --------------------------------------------------------------------------------------
def compare(table: str, csv: dict, layers: dict[str, dict]) -> list[dict]:
    findings = []

    def add(check, layer, ok, detail):
        findings.append({"table": table, "check": check, "layer": layer,
                         "ok": ok, "detail": detail})

    for name, layer in layers.items():
        if "error" in layer:
            add("reachable", name, False, layer["error"])
            continue

        add("row_count", name, layer["row_count"] == csv["row_count"],
            f"csv={csv['row_count']:,} {name}={layer['row_count']:,} "
            f"(diff {layer['row_count'] - csv['row_count']:+,})")

        missing_cols = [c for c in csv["columns"] if c not in layer["columns"]]
        add("columns", name, not missing_cols,
            "all present" if not missing_cols else f"absent: {', '.join(missing_cols)}")

        bad = {c: (csv["missing"][c], layer["missing"].get(c))
               for c in csv["columns"]
               if c in layer["columns"] and layer["missing"].get(c) != csv["missing"][c]}
        add("missing_values", name, not bad,
            "match" if not bad else
            "; ".join(f"{c}: csv={a} {name}={b}" for c, (a, b) in list(bad.items())[:4]))

        if csv["distinct_keys"] is not None and layer["distinct_keys"] is not None:
            add("distinct_keys", name, layer["distinct_keys"] == csv["distinct_keys"],
                f"csv={csv['distinct_keys']:,} {name}={layer['distinct_keys']:,}")

        bad_sums = {c: (csv["sums"][c], layer["sums"].get(c))
                    for c in csv["numeric_columns"]
                    if not floats_match(csv["sums"][c], layer["sums"].get(c))}
        if csv["numeric_columns"]:
            add("numeric_totals", name, not bad_sums,
                "match" if not bad_sums else
                "; ".join(f"{c}: csv={a} {name}={b}" for c, (a, b) in list(bad_sums.items())[:4]))

        if csv["fingerprint"] and layer["fingerprint"]:
            ok = csv["fingerprint"] == layer["fingerprint"]
            add("key_fingerprint", name, ok,
                "identical key set" if ok
                else f"csv={csv['fingerprint'][:12]} {name}={layer['fingerprint'][:12]}")

    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tables", help="comma-separated subset (default: all)")
    ap.add_argument("--deep", action="store_true",
                    help="also compare the full sorted key set by sha256")
    ap.add_argument("--skip-mongo", action="store_true")
    ap.add_argument("--skip-bq", action="store_true")
    ap.add_argument("--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT"),
                    help="GCP project (default: $GOOGLE_CLOUD_PROJECT)")
    ap.add_argument("--json", dest="json_path", help="write the full report here")
    args = ap.parse_args()

    if not args.skip_bq and not args.project:
        # credentials.env is the documented home for this; load it if present.
        env = REPO_ROOT / "config" / "credentials.env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("GOOGLE_CLOUD_PROJECT="):
                    args.project = line.split("=", 1)[1].strip()
        if not args.project:
            print("error: no GCP project. Set GOOGLE_CLOUD_PROJECT, pass --project, "
                  "or use --skip-bq.", file=sys.stderr)
            return 2

    wanted = args.tables.split(",") if args.tables else list(TABLE_FILES)
    findings: list[dict] = []
    skipped: list[str] = []

    for table in wanted:
        if table not in TABLE_FILES:
            print(f"error: unknown table '{table}'", file=sys.stderr)
            return 2
        if not (REPO_ROOT / "data" / "raw" / TABLE_FILES[table]).exists():
            # The pipeline itself skips absent CSVs, so this is not a failure.
            skipped.append(table)
            continue

        print(f"  reading {table} ...", file=sys.stderr)
        csv = probe_csv(table, args.deep)
        keys = NATURAL_KEYS.get(table)
        layers: dict[str, dict] = {}
        if not args.skip_mongo:
            layers["mongo"] = probe_mongo(table, csv["columns"], csv["numeric_columns"],
                                          keys, args.deep)
        if not args.skip_bq:
            layers["bigquery"] = probe_bigquery(table, csv["columns"], csv["numeric_columns"],
                                                keys, args.deep, args.project)
        findings.extend(compare(table, csv, layers))

    # ---- report ----
    failures = [f for f in findings if not f["ok"]]
    width = max((len(f["table"]) for f in findings), default=10) + 2

    print(f"\n{'TABLE':<{width}}{'LAYER':<11}{'CHECK':<17}{'':<3}DETAIL")
    print("-" * (width + 75))
    for f in findings:
        mark = "ok " if f["ok"] else "FAIL"
        print(f"{f['table']:<{width}}{f['layer']:<11}{f['check']:<17}{mark:<3} {f['detail']}")

    if skipped:
        print(f"\nskipped (CSV not in data/raw): {', '.join(skipped)}")

    checked = len({f["table"] for f in findings})
    print(f"\n{len(findings) - len(failures)}/{len(findings)} checks passed "
          f"across {checked} table(s).")
    if failures:
        by_layer: dict[str, int] = {}
        for f in failures:
            by_layer[f["layer"]] = by_layer.get(f["layer"], 0) + 1
        print("FAILED at: " + ", ".join(f"{k} ({v})" for k, v in sorted(by_layer.items())))
    else:
        print("All layers agree with the source CSVs."
              + ("" if args.deep else "  (run --deep to compare key sets row by row)"))

    if args.json_path:
        Path(args.json_path).write_text(json.dumps(
            {"findings": findings, "skipped": skipped, "deep": args.deep}, indent=2))
        print(f"report written to {args.json_path}")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
