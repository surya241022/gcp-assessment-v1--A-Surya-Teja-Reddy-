from google.cloud import bigquery

from agent.config import (
    PROJECT_ID,
    GOLD_DATASET,
    FACT_SALES_TABLE,
    DIM_PRODUCT_TABLE,
    DIM_DATE_TABLE,
)


client = bigquery.Client(
    project=PROJECT_ID
)


def _table(table_name: str) -> str:
    return f"`{PROJECT_ID}.{GOLD_DATASET}.{table_name}`"


def get_top_products(limit: int = 5) -> dict:
    """
    Return the top products ranked by total revenue.

    Use this tool when the user asks about:
    top products, highest revenue products,
    best products by revenue, or product ranking.
    """

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
                "total_revenue": float(
                    row.total_revenue
                ),
            }
        )

    return {
        "source": "BigQuery Gold",
        "table": f"{GOLD_DATASET}.{FACT_SALES_TABLE}",
        "data": results,
    }


def get_revenue_by_region() -> dict:
    """
    Return total revenue grouped by region.

    Use this tool when the user asks about:
    revenue by region, regional sales,
    regional performance, or sales by geography.
    """

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
                "total_revenue": float(
                    row.total_revenue
                ),
            }
        )

    return {
        "source": "BigQuery Gold",
        "table": f"{GOLD_DATASET}.{FACT_SALES_TABLE}",
        "data": results,
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
                "total_revenue": float(
                    row.total_revenue
                ),
            }
        )

    return {
        "source": "BigQuery Gold",
        "table": f"{GOLD_DATASET}.{FACT_SALES_TABLE}",
        "data": results,
    }