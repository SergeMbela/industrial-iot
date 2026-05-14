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
ENV_FILE = BASE_DIR / ".env"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("export "):
                line = line[len("export "):]

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def get_env(keys, default=None):
    for key in keys:
        value = os.getenv(key)
        if value is not None:
            return value
    return default


load_dotenv(ENV_FILE)

SQL_FILE = BASE_DIR / get_env(["SQL_FILE", "MATRICE_SQL_FILE"], "matrice.sql")

DB_CONFIG = {
    "host": get_env(["PGHOST", "POSTGRES_HOST"], "localhost"),
    "port": int(get_env(["PGPORT", "POSTGRES_PORT"], "5455")),
    "dbname": get_env(["PGDATABASE", "POSTGRES_DB"], "industrial_iot"),
    "user": get_env(["PGUSER", "POSTGRES_USER"], "admin"),
    "password": get_env(["PGPASSWORD", "POSTGRES_PASSWORD"], "admin123"),
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
        raise RuntimeError(f"Impossible de se connecter à PostgreSQL : {exc}")

    try:
        with conn.cursor() as cursor:
            cursor.execute(sql_code)
        print("Tables créées avec succès.")
    except Exception as exc:
        raise RuntimeError(f"Erreur lors de l'exécution du script SQL : {exc}")
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        create_tables()
    except Exception as e:
        print(f"FATAL: {e}")
        exit(1)
