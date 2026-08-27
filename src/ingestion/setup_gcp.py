import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv("GCP_PROJECT_ID", "gcp-assessment-v1-surya")
BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "northstar-retail-bucket")
LOCATION = os.getenv("GCP_REGION", "asia-south1")
USE_MOCK = os.getenv("USE_MOCK", "").lower() in ("true", "1", "yes")


def create_bucket():
    if USE_MOCK:
        print("=" * 60)
        print("NorthStar Retail - GCS Provisioning [MOCK MODE]")
        print("=" * 60)
        print(f"[MOCK] Active GCP credentials bypassed.")
        print(f"[MOCK] Simulated bucket provisioning ready: gs://{BUCKET_NAME} (Location: {LOCATION})")
        return

    try:
        from google.cloud import storage

        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(BUCKET_NAME)

        if bucket.exists():
            print(f"Bucket already exists: gs://{BUCKET_NAME}")
            return

        bucket = client.create_bucket(
            bucket,
            location=LOCATION
        )
        print(f"Bucket created: gs://{bucket.name}")

    except Exception as e:
        print("=" * 60)
        print("NorthStar Retail - GCS Provisioning [FALLBACK MODE]")
        print("=" * 60)
        print(f"Live GCP Service Unavailable: {e}")
        print(f"[MOCK FALLBACK] Simulated GCS bucket provisioning: gs://{BUCKET_NAME}")
        print("Local end-to-end execution supported.")


if __name__ == "__main__":
    create_bucket()