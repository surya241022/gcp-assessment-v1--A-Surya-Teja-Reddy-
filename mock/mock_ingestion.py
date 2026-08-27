"""
NorthStar Retail - Mock Ingestion Simulator
Runs the complete ingestion pipeline locally without live GCP credentials.
"""

import os
import sys
import csv
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mock.mock_policy_tools import _load_mock_documents

DATA_DIR = PROJECT_ROOT / "data"
SALES_PATH = DATA_DIR / "sales.csv"
DOCS_DIR = DATA_DIR / "product_docs"


def run_mock_gcs_provisioning(bucket_name: str = "northstar-retail-bucket", region: str = "asia-south1"):
    print("=" * 60)
    print("MOCK GCP PROVISIONING: GCS Bucket")
    print("=" * 60)
    print(f"[MOCK] Simulated Bucket Provisioning: gs://{bucket_name}")
    print(f"[MOCK] Location: {region}")
    print("[MOCK] Provisioning status: SUCCESS (Simulated)\n")


def run_mock_gcs_upload(bucket_name: str = "northstar-retail-bucket"):
    print("=" * 60)
    print("MOCK GCP INGESTION: Local to GCS Staging")
    print("=" * 60)
    count = 0
    for file_path in DATA_DIR.rglob("*"):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(DATA_DIR)
        gcs_dest = f"gs://{bucket_name}/raw/{rel.as_posix()}"
        print(f"  [MOCK UPLOAD] {file_path.name} -> {gcs_dest}")
        count += 1
    print(f"[MOCK] Total files staged to GCS: {count}\n")


def run_mock_bigquery_sales_load(project_id: str = "gcp-assessment-v1-surya"):
    print("=" * 60)
    print("MOCK BIGQUERY INGESTION: Sales Raw Table")
    print("=" * 60)
    target_table = f"{project_id}.bronze.sales_raw"
    with open(SALES_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        rows = sum(1 for _ in reader)
    print(f"[MOCK] Target Table: {target_table}")
    print(f"[MOCK] Schema: {header}")
    print(f"[MOCK] Rows Loaded: {rows} records\n")


def run_mock_bigquery_docs_load(project_id: str = "gcp-assessment-v1-surya"):
    print("=" * 60)
    print("MOCK BIGQUERY INGESTION: Product Documents Store")
    print("=" * 60)
    target_table = f"{project_id}.gold.product_documents"
    docs = _load_mock_documents()
    for d in docs:
        print(f"  [MOCK EXTRACT & INDEX] {d['source_name']} ({d['document_type']}) - {len(d['content'])} characters")
    print(f"[MOCK] Total Documents Indexed into {target_table}: {len(docs)}\n")


def main():
    print("######################################################################")
    print("  NORTHSTAR RETAIL - END-TO-END MOCK PIPELINE EXECUTION")
    print("######################################################################\n")
    run_mock_gcs_provisioning()
    run_mock_gcs_upload()
    run_mock_bigquery_sales_load()
    run_mock_bigquery_docs_load()
    print("All mock ingestion steps executed successfully without live GCP credentials.")


if __name__ == "__main__":
    main()
