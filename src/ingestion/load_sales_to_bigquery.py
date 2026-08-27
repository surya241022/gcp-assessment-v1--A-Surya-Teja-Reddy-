import os
import csv
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "gcp-assessment-v1-surya")
DATASET_ID = os.getenv("BQ_DATASET_ID", "bronze")
TABLE_ID = "sales_raw"

BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "northstar-retail-bucket")
LOCATION = os.getenv("BQ_LOCATION", os.getenv("GCP_REGION", "asia-south1"))
GCS_URI = f"gs://{BUCKET_NAME}/raw/sales.csv"
LOCAL_SALES_PATH = Path("data/sales.csv")
USE_MOCK = os.getenv("USE_MOCK", "").lower() in ("true", "1", "yes")


def create_dataset_if_not_exists(client, dataset_id: str, location: str):
    from google.cloud import bigquery
    dataset_ref = bigquery.DatasetReference(client.project, dataset_id)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = location
    client.create_dataset(dataset, exists_ok=True)
    print(f"Dataset ready: {client.project}.{dataset_id} (location: {location})")


def run_mock_sales_load():
    """Run local mock BigQuery load when GCP is unavailable."""
    print("=" * 60)
    print("NorthStar Retail - Bronze Sales Load [MOCK MODE]")
    print("=" * 60)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    if not LOCAL_SALES_PATH.exists():
        print(f"Error: {LOCAL_SALES_PATH} not found.")
        return

    with open(LOCAL_SALES_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        row_count = sum(1 for _ in reader)

    print(f"Mock Source: {LOCAL_SALES_PATH}")
    print(f"Destination: {table_ref}")
    print(f"Schema columns detected: {header}")
    print(f"\n[MOCK] Load completed successfully.")
    print(f"Table: {table_ref}")
    print(f"Rows loaded: {row_count}")


def main():
    if USE_MOCK:
        run_mock_sales_load()
        return

    try:
        from google.cloud import bigquery

        client = bigquery.Client(project=PROJECT_ID)
        create_dataset_if_not_exists(client, DATASET_ID, LOCATION)

        table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            autodetect=True,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )

        print("Loading:")
        print(f"  {GCS_URI}")
        print("Into:")
        print(f"  {table_ref}")

        load_job = client.load_table_from_uri(
            GCS_URI,
            table_ref,
            job_config=job_config,
        )

        load_job.result()

        table = client.get_table(table_ref)

        print("\nLoad completed successfully.")
        print(f"Table: {table_ref}")
        print(f"Rows: {table.num_rows}")

    except Exception as e:
        print(f"\n[Notice] Live BigQuery load unavailable: {e}")
        run_mock_sales_load()


if __name__ == "__main__":
    main()