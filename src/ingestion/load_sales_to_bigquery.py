import os
from dotenv import load_dotenv
from google.cloud import bigquery

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "gcp-assessment-v1-surya")
DATASET_ID = os.getenv("BQ_DATASET_ID", "bronze")
TABLE_ID = "sales_raw"

BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
LOCATION = os.getenv("BQ_LOCATION", os.getenv("GCP_REGION", "asia-south1"))
GCS_URI = f"gs://{BUCKET_NAME}/raw/sales.csv"


def create_dataset_if_not_exists(client: bigquery.Client, dataset_id: str, location: str):
    dataset_ref = bigquery.DatasetReference(client.project, dataset_id)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = location
    client.create_dataset(dataset, exists_ok=True)
    print(f"Dataset ready: {client.project}.{dataset_id} (location: {location})")


def main():
    client = bigquery.Client(project=PROJECT_ID)

    create_dataset_if_not_exists(client, DATASET_ID, LOCATION)

    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    print(f"Loading:")
    print(f"  {GCS_URI}")
    print(f"Into:")
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


if __name__ == "__main__":
    main()