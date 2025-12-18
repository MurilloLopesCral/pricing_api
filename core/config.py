import os
from dotenv import load_dotenv

load_dotenv()

PG_DSN = os.getenv("PG_DSN", "").strip()
TABLE = os.getenv("TABLE_NAME", "pedido_item").strip()
API_KEY = os.getenv("API_KEY", "").strip()

if not PG_DSN:
    raise RuntimeError("Defina PG_DSN no .env")
