import os
import csv
import io
import json
from dotenv import load_dotenv
from google.cloud import storage
from google.cloud import bigquery
from pypdf import PdfReader

load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "gcp-assessment-v1-surya")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
LOCATION = os.getenv("BQ_LOCATION", os.getenv("GCP_REGION", "asia-south1"))

GCS_PREFIX = "raw/product_docs/"

BQ_DATASET = "gold"
BQ_TABLE = "product_documents"


# ============================================================
# GCP CLIENTS
# ============================================================

storage_client = storage.Client(project=PROJECT_ID)

bigquery_client = bigquery.Client(project=PROJECT_ID)


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

    return json.dumps(
        data,
        indent=2,
        ensure_ascii=False
    )


def extract_txt(content: bytes) -> str:
    """Extract text from TXT."""

    return content.decode(
        "utf-8",
        errors="replace"
    )


def extract_csv(content: bytes) -> str:
    """Convert CSV content into searchable text."""

    text = content.decode(
        "utf-8",
        errors="replace"
    )

    reader = csv.reader(
        io.StringIO(text)
    )

    rows = []

    for row in reader:
        rows.append(" | ".join(row))

    return "\n".join(rows)


def extract_document(
    file_name: str,
    content: bytes
) -> str:

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
        print(
            f"Skipping unsupported file: {file_name}"
        )

        return ""


# ============================================================
# GCS
# ============================================================

def read_documents_from_gcs():

    bucket = storage_client.bucket(
        BUCKET_NAME
    )

    blobs = bucket.list_blobs(
        prefix=GCS_PREFIX
    )

    documents = []

    for blob in blobs:

        if blob.name.endswith("/"):
            continue

        print(
            f"Reading: gs://{BUCKET_NAME}/{blob.name}"
        )

        content = blob.download_as_bytes()

        text = extract_document(
            blob.name,
            content
        )

        if not text.strip():
            print(
                f"Warning: No text extracted from {blob.name}"
            )

            continue

        file_name = blob.name.split("/")[-1]

        documents.append(
            {
                "source_name": file_name,
                "gcs_uri": (
                    f"gs://{BUCKET_NAME}/{blob.name}"
                ),
                "document_type": (
                    file_name.split(".")[-1].lower()
                ),
                "content": text,
            }
        )

    return documents


# ============================================================
# BIGQUERY
# ============================================================

def create_dataset():

    dataset_id = (
        f"{PROJECT_ID}.{BQ_DATASET}"
    )

    dataset = bigquery.Dataset(
        dataset_id
    )

    dataset.location = LOCATION

    bigquery_client.create_dataset(
        dataset,
        exists_ok=True
    )

    print(
        f"Dataset ready: {dataset_id}"
    )


def create_table():

    table_id = (
        f"{PROJECT_ID}."
        f"{BQ_DATASET}."
        f"{BQ_TABLE}"
    )

    schema = [

        bigquery.SchemaField(
            "source_name",
            "STRING",
            mode="REQUIRED"
        ),

        bigquery.SchemaField(
            "gcs_uri",
            "STRING",
            mode="REQUIRED"
        ),

        bigquery.SchemaField(
            "document_type",
            "STRING",
            mode="REQUIRED"
        ),

        bigquery.SchemaField(
            "content",
            "STRING",
            mode="REQUIRED"
        ),

    ]

    table = bigquery.Table(
        table_id,
        schema=schema
    )

    table.description = (
        "Extracted NorthStar Retail product "
        "documents used by the ADK policy agent."
    )

    bigquery_client.create_table(
        table,
        exists_ok=True
    )

    print(
        f"Table ready: {table_id}"
    )


def load_documents(documents):

    table_id = (
        f"{PROJECT_ID}."
        f"{BQ_DATASET}."
        f"{BQ_TABLE}"
    )

    job_config = bigquery.LoadJobConfig(

        schema=[
            bigquery.SchemaField(
                "source_name",
                "STRING"
            ),

            bigquery.SchemaField(
                "gcs_uri",
                "STRING"
            ),

            bigquery.SchemaField(
                "document_type",
                "STRING"
            ),

            bigquery.SchemaField(
                "content",
                "STRING"
            ),
        ],

        write_disposition=(
            bigquery.WriteDisposition.WRITE_TRUNCATE
        )
    )

    job = bigquery_client.load_table_from_json(
        documents,
        table_id,
        job_config=job_config
    )

    job.result()

    print(
        f"Loaded {len(documents)} documents "
        f"into {table_id}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("NorthStar Retail - Product Document Ingestion")
    print("=" * 70)

    create_dataset()

    create_table()

    documents = read_documents_from_gcs()

    if not documents:

        print(
            "No documents found."
        )

        return

    load_documents(documents)

    print("\nDocument ingestion completed.")


if __name__ == "__main__":
    main()