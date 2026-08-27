import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# GCP Project Settings
PROJECT_ID = os.getenv(
    "GCP_PROJECT_ID",
    "gcp-assessment-v1-surya"
)

LOCATION = os.getenv(
    "GCP_LOCATION",
    "asia-south1"
)

# BigQuery Datasets & Tables
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

# Data Directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "product_docs"
SALES_CSV_PATH = DATA_DIR / "sales.csv"

# Mock Mode Configuration
USE_MOCK = os.getenv("USE_MOCK", "").lower() in ("true", "1", "yes")