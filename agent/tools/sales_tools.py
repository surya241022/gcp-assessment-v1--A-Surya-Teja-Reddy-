import csv
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from agent.config import (
    PROJECT_ID,
    GOLD_DATASET,
    FACT_SALES_TABLE,
    DIM_PRODUCT_TABLE,
    SALES_CSV_PATH,
    USE_MOCK,
)

_bq_client = None
_client_initialized = False


def get_bigquery_client():
    """Lazily and safely initialize BigQuery client with mock fallback."""
    global _bq_client, _client_initialized
    if _client_initialized:
        return _bq_client

    _client_initialized = True
    if USE_MOCK:
        _bq_client = None
        return None

    try:
        from google.cloud import bigquery
        client = bigquery.Client(project=PROJECT_ID)
        _bq_client = client
        return _bq_client
    except Exception:
        _bq_client = None
        return None


def _table(table_name: str) -> str:
    return f"`{PROJECT_ID}.{GOLD_DATASET}.{table_name}`"


# ============================================================
# MOCK SALES DATA ENGINE (Local Fallback)
# ============================================================

def _load_mock_sales() -> List[Dict[str, Any]]:
    """Load and parse local sales CSV as mock fact table data."""
    if not SALES_CSV_PATH.exists():
        return []

    records = []
    with open(SALES_CSV_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                qty = float(row.get("quantity", 0) or 0)
                price = float(row.get("unit_price", 0) or 0)
                revenue = qty * price
                order_date = datetime.strptime(row.get("order_date", "").strip(), "%Y-%m-%d").date()
                records.append({
                    "order_id": row.get("order_id", "").strip(),
                    "order_date": order_date,
                    "store_id": row.get("store_id", "").strip(),
                    "product_id": row.get("product_id", "").strip(),
                    "product_name": row.get("product_name", "").strip(),
                    "category": row.get("category", "").strip().title(),
                    "quantity": int(qty),
                    "unit_price": price,
                    "region": row.get("region", "").strip().title(),
                    "revenue": revenue,
                })
            except Exception:
                continue
    return records


# ============================================================
# SALES TOOLS (Live GCP BigQuery with Mock Fallback)
# ============================================================

def get_top_products(limit: int = 5) -> dict:
    """
    Return the top products ranked by total revenue.

    Use this tool when the user asks about:
    top products, highest revenue products,
    best products by revenue, or product ranking.
    """
    client = get_bigquery_client()
    if client:
        try:
            from google.cloud import bigquery

            query = f"""
                SELECT
                    p.product_id,
                    p.product_name,
                    SUM(f.revenue) AS total_revenue
                FROM {_table(FACT_SALES_TABLE)} AS f
                JOIN {_table(DIM_PRODUCT_TABLE)} AS p
                  ON f.product_id = p.product_id
                GROUP BY
                    p.product_id,
                    p.product_name
                ORDER BY total_revenue DESC
                LIMIT @limit
            """

            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter(
                        "limit",
                        "INT64",
                        limit,
                    )
                ]
            )

            rows = client.query(
                query,
                job_config=job_config,
            ).result()

            results = []
            for row in rows:
                results.append(
                    {
                        "product_id": row.product_id,
                        "product_name": row.product_name,
                        "total_revenue": round(float(row.total_revenue), 2),
                    }
                )

            return {
                "source": "BigQuery Gold",
                "table": f"{GOLD_DATASET}.{FACT_SALES_TABLE}",
                "data": results,
            }
        except Exception:
            pass

    # --- Working Mock Implementation ---
    records = _load_mock_sales()
    product_rev: Dict[str, Dict[str, Any]] = {}
    for r in records:
        pid = r["product_id"]
        if pid not in product_rev:
            product_rev[pid] = {
                "product_id": pid,
                "product_name": r["product_name"],
                "total_revenue": 0.0,
            }
        product_rev[pid]["total_revenue"] += r["revenue"]

    sorted_products = sorted(
        product_rev.values(),
        key=lambda x: x["total_revenue"],
        reverse=True
    )[:limit]

    for p in sorted_products:
        p["total_revenue"] = round(p["total_revenue"], 2)

    return {
        "source": "Mock BigQuery Gold (Local Fallback)",
        "table": f"{GOLD_DATASET}.{FACT_SALES_TABLE}",
        "data": sorted_products,
    }


def get_revenue_by_region() -> dict:
    """
    Return total revenue grouped by region.

    Use this tool when the user asks about:
    revenue by region, regional sales,
    regional performance, or sales by geography.
    """
    client = get_bigquery_client()
    if client:
        try:
            query = f"""
                SELECT
                    region,
                    SUM(revenue) AS total_revenue
                FROM {_table(FACT_SALES_TABLE)}
                GROUP BY region
                ORDER BY total_revenue DESC
            """

            rows = client.query(query).result()
            results = []
            for row in rows:
                results.append(
                    {
                        "region": row.region,
                        "total_revenue": round(float(row.total_revenue), 2),
                    }
                )

            return {
                "source": "BigQuery Gold",
                "table": f"{GOLD_DATASET}.{FACT_SALES_TABLE}",
                "data": results,
            }
        except Exception:
            pass

    # --- Working Mock Implementation ---
    records = _load_mock_sales()
    region_rev: Dict[str, float] = {}
    for r in records:
        reg = r["region"]
        region_rev[reg] = region_rev.get(reg, 0.0) + r["revenue"]

    sorted_regions = [
        {"region": reg, "total_revenue": round(rev, 2)}
        for reg, rev in sorted(region_rev.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "source": "Mock BigQuery Gold (Local Fallback)",
        "table": f"{GOLD_DATASET}.{FACT_SALES_TABLE}",
        "data": sorted_regions,
    }


def get_recent_best_category() -> dict:
    """
    Return the category with the highest revenue in the
    seven days immediately before the latest order date
    present in the dataset.

    Use this tool when the user asks for:
    recent category performance, best-selling category,
    highest category revenue in the last seven days,
    or the category immediately before the latest order date.

    IMPORTANT:
    The seven-day window is relative to the latest date
    in the dataset, not today's date.
    """
    client = get_bigquery_client()
    if client:
        try:
            query = f"""
                WITH latest_date AS (
                    SELECT
                        MAX(date_key) AS latest_order_date
                    FROM {_table(FACT_SALES_TABLE)}
                ),

                category_revenue AS (
                    SELECT
                        f.category,
                        SUM(f.revenue) AS total_revenue
                    FROM {_table(FACT_SALES_TABLE)} AS f
                    CROSS JOIN latest_date
                    WHERE f.date_key >= DATE_SUB(
                        latest_date.latest_order_date,
                        INTERVAL 7 DAY
                    )
                    AND f.date_key < latest_date.latest_order_date
                    GROUP BY f.category
                )

                SELECT
                    category,
                    total_revenue
                FROM category_revenue
                ORDER BY total_revenue DESC
                LIMIT 1
            """

            rows = client.query(query).result()
            results = []
            for row in rows:
                results.append(
                    {
                        "category": row.category,
                        "total_revenue": round(float(row.total_revenue), 2),
                    }
                )

            return {
                "source": "BigQuery Gold",
                "table": f"{GOLD_DATASET}.{FACT_SALES_TABLE}",
                "data": results,
            }
        except Exception:
            pass

    # --- Working Mock Implementation ---
    records = _load_mock_sales()
    if not records:
        return {
            "source": "Mock BigQuery Gold (Local Fallback)",
            "table": f"{GOLD_DATASET}.{FACT_SALES_TABLE}",
            "data": [],
        }

    latest_date = max(r["order_date"] for r in records)
    start_date = latest_date - timedelta(days=7)

    cat_rev: Dict[str, float] = {}
    for r in records:
        if start_date <= r["order_date"] < latest_date:
            cat = r["category"]
            cat_rev[cat] = cat_rev.get(cat, 0.0) + r["revenue"]

    if not cat_rev:
        return {
            "source": "Mock BigQuery Gold (Local Fallback)",
            "table": f"{GOLD_DATASET}.{FACT_SALES_TABLE}",
            "data": [],
        }

    top_cat, rev = max(cat_rev.items(), key=lambda x: x[1])
    return {
        "source": "Mock BigQuery Gold (Local Fallback)",
        "table": f"{GOLD_DATASET}.{FACT_SALES_TABLE}",
        "data": [{"category": top_cat, "total_revenue": round(rev, 2)}],
    }