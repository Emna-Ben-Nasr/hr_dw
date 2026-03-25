import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST', 'localhost')}:"
    f"{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME')}"
)

CSV_PATH         = os.getenv('CSV_PATH', 'data/raw/HRDataset_v14.csv')
DATE_RANGE_START = os.getenv('DATE_RANGE_START', '1960-01-01')
DATE_RANGE_END   = os.getenv('DATE_RANGE_END',   '2030-12-31')
