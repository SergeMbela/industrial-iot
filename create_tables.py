import os
from pathlib import Path

try:
    import psycopg2
    from psycopg2 import OperationalError
except ImportError:
    raise SystemExit(
        "Le module psycopg2 est requis. Installez-le avec : pip install psycopg2-binary"
    )

BASE_DIR = Path(__file__).resolve().parent
SQL_FILE = BASE_DIR / "matrice.sql"

DB_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": int(os.getenv("PGPORT", 5455)),
    "dbname": os.getenv("PGDATABASE", "industrial_iot"),
    "user": os.getenv("PGUSER", "admin"),
    "password": os.getenv("PGPASSWORD", "admin123"),
}


def load_sql_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Fichier SQL introuvable : {path}")
    return path.read_text(encoding="utf-8")


def create_tables():
    sql_code = load_sql_file(SQL_FILE)

    print("Connexion à PostgreSQL avec :")
    print(f"  hôte={DB_CONFIG['host']} port={DB_CONFIG['port']} dbname={DB_CONFIG['dbname']} user={DB_CONFIG['user']}")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
    except OperationalError as exc:
        raise SystemExit(f"Impossible de se connecter à PostgreSQL : {exc}")

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql_code)
        print("Tables créées avec succès.")
    except Exception as exc:
        raise SystemExit(f"Erreur lors de l'exécution du script SQL : {exc}")
    finally:
        conn.close()


if __name__ == "__main__":
    create_tables()
