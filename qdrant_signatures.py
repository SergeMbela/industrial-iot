import os
import psycopg2
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from dotenv import load_dotenv

load_dotenv()

# Configuration DB
DB_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": os.getenv("PGPORT", "5455"),
    "database": os.getenv("PGDATABASE", "industrial_iot"),
    "user": os.getenv("PGUSER", "admin"),
    "password": os.getenv("PGPASSWORD", "admin123")
}

# Configuration Qdrant
QDRANT_HOST = "localhost"
QDRANT_PORT = 6338
COLLECTION_NAME = "anomaly_signatures"

# Définition des features qu'on utilise pour créer notre "Vecteur"
# Ordre strict : [vibration, amperage, oil_temp, cycle_speed, fuel]
VECTOR_SIZE = 5

def create_vector_from_row(row):
    """
    Crée un vecteur mathématique à partir des valeurs brutes.
    Pour une vraie mise en production, il faudrait normaliser (MinMaxScaler ou StandardScaler) 
    pour que les différences d'échelles (ex: température à 100 vs vibration à 2) ne faussent pas la similarité.
    Ici on fait une normalisation manuelle basique.
    """
    vib = (float(row.get('vibration_rms_mm_s', 0)) or 0) / 10.0
    amp = (float(row.get('amperage', 0)) or 0) / 300.0
    temp = (float(row.get('oil_temp_c', 0)) or 0) / 150.0
    speed = (float(row.get('cycle_speed_s', 0)) or 0) / 50.0
    fuel = (float(row.get('fuel_consumption_lh', 0)) or 0) / 100.0
    
    return [vib, amp, temp, speed, fuel]

def init_qdrant():
    print("Connexion à Qdrant...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    # Recréer la collection
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
        
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    print(f"Collection '{COLLECTION_NAME}' créée.")
    return client

def populate_qdrant_with_anomalies(client):
    print("Récupération des anomalies historiques depuis PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, machine_id, alert_label, timestamp, 
               vibration_rms_mm_s, amperage, oil_temp_c, cycle_speed_s, fuel_consumption_lh
        FROM sensor_data
        WHERE alert_label != 'Normal'
        LIMIT 500
    """)
    
    rows = cur.fetchall()
    if not rows:
        print("Aucune anomalie trouvée dans l'historique pour créer des signatures.")
        return
        
    points = []
    for r in rows:
        # Transformation en dictionnaire
        data = {
            'vibration_rms_mm_s': r[4],
            'amperage': r[5],
            'oil_temp_c': r[6],
            'cycle_speed_s': r[7],
            'fuel_consumption_lh': r[8]
        }
        
        vector = create_vector_from_row(data)
        
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                "machine_id": r[1],
                "alert_label": r[2],
                "timestamp": r[3].isoformat() if r[3] else None
            }
        ))
        
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    print(f"{len(points)} signatures d'anomalies injectées dans Qdrant.")
    cur.close()
    conn.close()

def search_similar_anomaly(client, telemetry_data):
    """
    Vérifie si une nouvelle télémétrie ressemble à une anomalie connue.
    """
    vector = create_vector_from_row(telemetry_data)
    
    search_result = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=1,
        score_threshold=0.98
    )
    
    if search_result.points:
        match = search_result.points[0]
        print(f"🚨 ALERTE SIMILARITÉ 🚨: La machine {telemetry_data['machine_id']} a une signature mathématique "
              f"similaire à {match.score:.2%} à une panne passée de type '{match.payload['alert_label']}' "
              f"(Survenue sur la machine {match.payload['machine_id']} le {match.payload['timestamp'][:10]}).")
        return True
    else:
        print(f"✅ Machine {telemetry_data['machine_id']}: Aucune signature de panne similaire détectée.")
        return False

if __name__ == "__main__":
    # 1. Initialiser Qdrant et charger l'historique
    client = init_qdrant()
    populate_qdrant_with_anomalies(client)
    
    print("\n--- TEST DE RECHERCHE PAR SIMILARITÉ ---")
    # 2. Test avec une fausse télémétrie "saine"
    test_healthy = {
        "machine_id": "TEST-01",
        "vibration_rms_mm_s": 2.1,
        "amperage": 50,
        "oil_temp_c": 60,
        "cycle_speed_s": 30,
        "fuel_consumption_lh": 15
    }
    search_similar_anomaly(client, test_healthy)
    
    # 3. Test avec une télémétrie qui mime un moteur en surchauffe/surcharge
    test_danger = {
        "machine_id": "TEST-02",
        "vibration_rms_mm_s": 15.0,  # Forte vibration
        "amperage": 300,             # Surcharge
        "oil_temp_c": 120,           # Surchauffe
        "cycle_speed_s": 10,
        "fuel_consumption_lh": 55
    }
    search_similar_anomaly(client, test_danger)
