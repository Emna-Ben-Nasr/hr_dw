from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DB_URL = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:"
    f"{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

print(f"Tentative de connexion à : {os.getenv('DB_NAME')}...")

try:
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database(), version()"))
        row = result.fetchone()
        print(f"Connexion OK !")
        print(f"  Base active  : {row[0]}")
        print(f"  Version PG   : {row[1][:40]}")
except Exception as e:
    print(f"Echec de connexion : {e}")