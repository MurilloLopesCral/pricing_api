import psycopg


def test_db_connection(dsn: str) -> bool:
    try:
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return True
    except Exception as e:
        print("Erro ao conectar no banco:", e)
        return False
