import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# =========================
# Configuration
# =========================

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "gcp-assessment-v1-surya")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "northstar-retail-bucket")
LOCATION = os.getenv("GCP_REGION", "asia-south1")
USE_MOCK = os.getenv("USE_MOCK", "").lower() in ("true", "1", "yes")

DATA_DIR = Path("data/raw") if Path("data/raw").exists() else Path("data")


# =========================
# GCS Upload Functions
# =========================

def create_bucket_if_not_exists(client, bucket_name):
    """Create the GCS bucket if it does not already exist."""
    bucket = client.bucket(bucket_name)

    if bucket.exists():
        print(f"Bucket already exists: gs://{bucket_name}")
        return bucket

    bucket = client.create_bucket(
        bucket,
        location=LOCATION
    )

    print(f"Created bucket: gs://{bucket_name}")
    return bucket


def upload_file(bucket, local_file, gcs_path):
    """Upload one local file to GCS."""
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(str(local_file))

    print(f"Uploaded: {local_file}")
    print(f"       -> gs://{bucket.name}/{gcs_path}")


def upload_all_data(bucket):
    """Upload all files from data to the raw folder in GCS."""
    for file_path in DATA_DIR.rglob("*"):
        if not file_path.is_file():
            continue

        relative_path = file_path.relative_to(DATA_DIR)
        gcs_path = f"raw/{relative_path.as_posix()}"

        upload_file(
            bucket=bucket,
            local_file=file_path,
            gcs_path=gcs_path
        )


def run_mock_upload():
    """Run local mock upload when live GCP credentials are unavailable."""
    print("=" * 60)
    print("NorthStar Retail - GCS Data Upload [MOCK MODE]")
    print("=" * 60)
    print(f"Target Bucket: gs://{BUCKET_NAME}")
    print("Verifying local source files:")

    count = 0
    for file_path in DATA_DIR.rglob("*"):
        if not file_path.is_file():
            continue
        relative_path = file_path.relative_to(DATA_DIR)
        gcs_path = f"raw/{relative_path.as_posix()}"
        print(f"  [MOCK UPLOAD] {file_path} -> gs://{BUCKET_NAME}/{gcs_path}")
        count += 1

    print(f"\n[MOCK] Successfully staged {count} files for GCS simulation.")


# =========================
# Main
# =========================

def main():
    if USE_MOCK:
        run_mock_upload()
        return

    try:
        from google.cloud import storage

        print("=" * 60)
        print("NorthStar Retail - GCS Data Upload")
        print("=" * 60)

        client = storage.Client(project=PROJECT_ID)

        bucket = create_bucket_if_not_exists(
            client,
            BUCKET_NAME
        )

        upload_all_data(bucket)

        print("\nUpload completed successfully.")
        print(f"Bucket: gs://{BUCKET_NAME}")

    except Exception as e:
        print(f"\n[Notice] Live GCP storage unavailable: {e}")
        run_mock_upload()


if __name__ == "__main__":
    main()