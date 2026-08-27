from google.cloud import bigquery

from agent.config import (
    PROJECT_ID,
    GOLD_DATASET,
    DOCUMENT_TABLE,
)


client = bigquery.Client(
    project=PROJECT_ID
)


def search_policy_documents(
    search_query: str
) -> dict:
    """
    Search the NorthStar Retail product and policy documents.

    Use this tool for questions about:
    returns, refunds, shipping, delivery, warranty,
    loyalty points, promotions, discounts, sizing,
    customer support, stationery FAQs, and other
    product-policy information.

    Never answer policy questions from general knowledge.
    Always use this tool.
    """

    table = (
        f"`{PROJECT_ID}."
        f"{GOLD_DATASET}."
        f"{DOCUMENT_TABLE}`"
    )

    query = f"""
        SELECT
            source_name,
            gcs_uri,
            document_type,
            content
        FROM {table}
        WHERE LOWER(content) LIKE
              CONCAT('%', LOWER(@search_query), '%')
        LIMIT 5
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter(
                "search_query",
                "STRING",
                search_query,
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
                "source_name": row.source_name,
                "gcs_uri": row.gcs_uri,
                "document_type": row.document_type,
                "content": row.content,
            }
        )

    if not results:
        return {
            "source": "NorthStar product documents",
            "results": [],
            "message": (
                "No matching document content was found."
            ),
        }

    return {
        "source": "NorthStar product documents",
        "results": results,
    }