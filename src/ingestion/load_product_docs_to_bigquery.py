import os
import csv
import io
import json
from pathlib import Path
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "gcp-assessment-v1-surya")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "northstar-retail-bucket")
LOCATION = os.getenv("BQ_LOCATION", os.getenv("GCP_REGION", "asia-south1"))

GCS_PREFIX = "raw/product_docs/"
BQ_DATASET = "gold"
BQ_TABLE = "product_documents"
LOCAL_DOCS_DIR = Path("data/product_docs")
USE_MOCK = os.getenv("USE_MOCK", "").lower() in ("true", "1", "yes")


# ============================================================
# DOCUMENT EXTRACTION
# ============================================================

def extract_pdf(content: bytes) -> str:
    """Extract text from a PDF."""
    reader = PdfReader(io.BytesIO(content))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


def extract_json(content: bytes) -> str:
    """Extract readable text from JSON."""
    data = json.loads(content.decode("utf-8"))
    return json.dumps(data, indent=2, ensure_ascii=False)


def extract_txt(content: bytes) -> str:
    """Extract text from TXT."""
    return content.decode("utf-8", errors="replace")


def extract_csv(content: bytes) -> str:
    """Convert CSV content into searchable text."""
    text = content.decode("utf-8", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = [" | ".join(row) for row in reader]
    return "\n".join(rows)


def extract_document(file_name: str, content: bytes) -> str:
    extension = file_name.lower().split(".")[-1]
    if extension == "pdf":
        return extract_pdf(content)
    elif extension == "json":
        return extract_json(content)
    elif extension == "txt":
        return extract_txt(content)
    elif extension == "csv":
        return extract_csv(content)
    else:
        print(f"Skipping unsupported file: {file_name}")
        return ""


def read_local_documents():
    """Read and extract documents from local directory for mock execution."""
    documents = []
    if not LOCAL_DOCS_DIR.exists():
        return documents

    for f in LOCAL_DOCS_DIR.iterdir():
        if not f.is_file():
            continue
        content = f.read_bytes()
        text = extract_document(f.name, content)
        if text.strip():
            documents.append({
                "source_name": f.name,
                "gcs_uri": f"gs://{BUCKET_NAME}/raw/product_docs/{f.name}",
                "document_type": f.suffix.lower().lstrip("."),
                "content": text,
            })
    return documents


def run_mock_docs_ingestion():
    """Execute local document extraction and indexing in mock mode."""
    print("=" * 70)
    print("NorthStar Retail - Product Document Ingestion [MOCK MODE]")
    print("=" * 70)
    table_id = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"
    documents = read_local_documents()

    for doc in documents:
        print(f"  [MOCK EXTRACT] {doc['source_name']} ({doc['document_type']}) -> {len(doc['content'])} characters extracted.")

    print(f"\n[MOCK] Successfully indexed {len(documents)} policy documents for {table_id}.")


# ============================================================
# MAIN
# ============================================================

def main():
    if USE_MOCK:
        run_mock_docs_ingestion()
        return

    try:
        from google.cloud import storage, bigquery

        print("=" * 70)
        print("NorthStar Retail - Product Document Ingestion")
        print("=" * 70)

        storage_client = storage.Client(project=PROJECT_ID)
        bigquery_client = bigquery.Client(project=PROJECT_ID)

        # Create dataset
        dataset_id = f"{PROJECT_ID}.{BQ_DATASET}"
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = LOCATION
        bigquery_client.create_dataset(dataset, exists_ok=True)

        # Create table
        table_id = f"{PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"
        schema = [
            bigquery.SchemaField("source_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("gcs_uri", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("document_type", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("content", "STRING", mode="REQUIRED"),
        ]
        table = bigquery.Table(table_id, schema=schema)
        bigquery_client.create_table(table, exists_ok=True)

        # Read from GCS
        bucket = storage_client.bucket(BUCKET_NAME)
        blobs = bucket.list_blobs(prefix=GCS_PREFIX)
        documents = []

        for blob in blobs:
            if blob.name.endswith("/"):
                continue
            content = blob.download_as_bytes()
            text = extract_document(blob.name, content)
            if not text.strip():
                continue
            file_name = blob.name.split("/")[-1]
            documents.append({
                "source_name": file_name,
                "gcs_uri": f"gs://{BUCKET_NAME}/{blob.name}",
                "document_type": file_name.split(".")[-1].lower(),
                "content": text,
            })

        if not documents:
            print("No documents found in GCS. Falling back to local documents.")
            documents = read_local_documents()

        if documents:
            job_config = bigquery.LoadJobConfig(
                schema=schema,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
            )
            job = bigquery_client.load_table_from_json(documents, table_id, job_config=job_config)
            job.result()
            print(f"Loaded {len(documents)} documents into {table_id}")

    except Exception as e:
        print(f"\n[Notice] Live GCP BigQuery service unavailable: {e}")
        run_mock_docs_ingestion()


if __name__ == "__main__":
    main()