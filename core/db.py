import psycopg
from psycopg.rows import dict_row

from core.config import PG_DSN
from utils.dbConn import test_db_connection


def run_query(sql: str, params: list):
    if not test_db_connection(PG_DSN):
        raise RuntimeError("Banco indisponível")

    with psycopg.connect(PG_DSN, row_factory=dict_row) as conn:  # type: ignore
        with conn.cursor() as cur:
            cur.execute(sql, params)  # type: ignore
            return cur.fetchall()
