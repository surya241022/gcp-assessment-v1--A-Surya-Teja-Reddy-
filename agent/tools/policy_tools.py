import csv
import io
import json
from pathlib import Path
from typing import List, Dict, Any

from agent.config import (
    PROJECT_ID,
    GOLD_DATASET,
    DOCUMENT_TABLE,
    DOCS_DIR,
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


# ============================================================
# MOCK POLICY DOCUMENT ENGINE (Local Fallback)
# ============================================================

def _extract_mock_file(path: Path) -> str:
    """Extract readable text from a local document."""
    ext = path.suffix.lower().lstrip(".")
    try:
        if ext == "pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(str(path))
                pages = [p.extract_text() for p in reader.pages if p.extract_text()]
                return "\n".join(pages)
            except Exception:
                return f"[PDF Document: {path.name}]"
        elif ext == "json":
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return json.dumps(data, indent=2, ensure_ascii=False)
        elif ext == "txt":
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        elif ext == "csv":
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                return "\n".join(" | ".join(row) for row in reader)
    except Exception:
        pass
    return ""


def _load_mock_documents() -> List[Dict[str, str]]:
    """Load all local policy documents."""
    if not DOCS_DIR.exists():
        return []

    docs = []
    for f in DOCS_DIR.iterdir():
        if not f.is_file():
            continue
        text = _extract_mock_file(f)
        if text.strip():
            docs.append({
                "source_name": f.name,
                "gcs_uri": f"gs://northstar-retail-bucket/raw/product_docs/{f.name}",
                "document_type": f.suffix.lower().lstrip("."),
                "content": text,
            })
    return docs


# ============================================================
# POLICY TOOLS (Live GCP BigQuery with Mock Fallback)
# ============================================================

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
    client = get_bigquery_client()
    if client:
        try:
            from google.cloud import bigquery

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

            if results:
                return {
                    "source": "NorthStar product documents (BigQuery)",
                    "results": results,
                }
        except Exception:
            pass

    # --- Working Mock Implementation ---
    docs = _load_mock_documents()
    query_lower = search_query.lower().strip()
    matching_docs = []

    for d in docs:
        if query_lower in d["content"].lower() or query_lower in d["source_name"].lower():
            matching_docs.append(d)

    matching_docs = matching_docs[:5]

    if not matching_docs:
        # Fallback to returning relevant top docs if query is generic
        for d in docs:
            matching_docs.append(d)
            if len(matching_docs) >= 3:
                break

    return {
        "source": "NorthStar product documents (Mock / Local Fallback)",
        "results": matching_docs,
        "message": "Results served via local document store fallback." if matching_docs else "No matching document content found.",
    }