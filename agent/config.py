import os
from dotenv import load_dotenv

load_dotenv()

PROJECT_ID = os.getenv(
    "GCP_PROJECT_ID",
    "gcp-assessment-v1-surya"
)

LOCATION = os.getenv(
    "GCP_LOCATION",
    "asia-south1"
)

GOLD_DATASET = os.getenv(
    "GOLD_DATASET",
    "gold"
)

FACT_SALES_TABLE = os.getenv(
    "FACT_SALES_TABLE",
    "fact_sales"
)

DIM_PRODUCT_TABLE = os.getenv(
    "DIM_PRODUCT_TABLE",
    "dim_product"
)

DIM_DATE_TABLE = os.getenv(
    "DIM_DATE_TABLE",
    "dim_date"
)

DOCUMENT_TABLE = os.getenv(
    "DOCUMENT_TABLE",
    "product_documents"
)