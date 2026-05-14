import pika
import json
import random
import time
import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
DB_CONFIG = {
    "host": os.getenv("PGHOST", "localhost"),
    "port": os.getenv("PGPORT", "5455"),
    "database": os.getenv("PGDATABASE", "industrial_iot"),
    "user": os.getenv("PGUSER", "admin"),
    "password": os.getenv("PGPASSWORD", "admin123")
}

RABBITMQ_CONFIG = {
    "host": os.getenv("RABBITMQ_HOST", "localhost"),
    "port": int(os.getenv("RABBITMQ_PORT", 5673)),
    "user": os.getenv("RABBITMQ_DEFAULT_USER", "guest"),
    "pass": os.getenv("RABBITMQ_DEFAULT_PASS", "guest")
}

def get_machines():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT m.machine_id, t.name FROM machines m JOIN machine_types t ON m.type_id = t.type_id")
    machines = cur.fetchall()
    conn.close()
    return machines

def generate_telemetry(machine_id, type_name):
    # Valeurs de base (Normal)
    data = {
        "machine_id": machine_id,
        "timestamp": datetime.now().isoformat(),
        "alert_label": "Normal",
        
        # 1. Performance
        "fuel_consumption_lh": float(random.uniform(15, 35)) if type_name in ['Camion', 'Excavatrice'] else 0.0,
        "amperage": float(random.uniform(40, 120)) if type_name in ['Broyeur', 'Pompe', 'Foreuse'] else 0.0,
        "idle_time_pct": float(random.uniform(2, 12)),
        
        # 2. Mécanique
        "vibration_rms_mm_s": float(random.uniform(1.2, 3.5)),
        "vibration_accel_g": float(random.uniform(0.3, 1.2)),
        "hours_hmr": float(random.uniform(1000, 10000)), # Heures machine réelles
        "cycle_speed_s": float(random.uniform(22, 28)) if type_name == 'Excavatrice' else 0.0,
        
        # 3. Fluides
        "oil_viscosity_cst": float(random.uniform(90, 110)),
        "silicon_ppm": float(random.uniform(5, 15)),
        "water_ppm": float(random.uniform(50, 200)),
        "tbn_value": float(random.uniform(8, 10)),
        
        # 4. Thermique / Pression
        "oil_temp_c": float(random.uniform(65, 82)),
        "oil_pressure_bar": float(random.uniform(3.8, 5.2)),
        "exhaust_temp_c": float(random.uniform(400, 550)) if type_name in ['Camion', 'Excavatrice'] else 0.0,
        "turbo_boost_bar": float(random.uniform(1.2, 1.8)) if type_name == 'Camion' else 0.0,
        "filter_diff_pressure_bar": float(random.uniform(0.5, 1.2)),
        
        "ambient_temp": float(random.uniform(22, 38)),
        "humidity_percent": float(random.uniform(40, 65))
    }

    # Simulation d'anomalies (5% de chance)
    if random.random() < 0.05:
        anomaly_type = random.choice([
            "Vibration Excessive", "Surchauffe Moteur", "Basse Pression Huile", 
            "Filtre Colmaté", "Contamination Fluide", "Surcharge Électrique"
        ])
        
        data["alert_label"] = anomaly_type
        
        if anomaly_type == "Vibration Excessive":
            data["vibration_rms_mm_s"] = float(random.uniform(8.5, 14.0))
            data["vibration_accel_g"] = float(random.uniform(2.5, 4.5))
        elif anomaly_type == "Surchauffe Moteur":
            data["oil_temp_c"] = float(random.uniform(98, 115))
            if type_name in ['Camion', 'Excavatrice']:
                data["exhaust_temp_c"] = float(random.uniform(750, 850))
        elif anomaly_type == "Basse Pression Huile":
            data["oil_pressure_bar"] = float(random.uniform(0.8, 2.2))
        elif anomaly_type == "Filtre Colmaté":
            data["filter_diff_pressure_bar"] = float(random.uniform(2.5, 4.0))
        elif anomaly_type == "Contamination Fluide":
            data["water_ppm"] = float(random.uniform(1500, 4000))
            data["silicon_ppm"] = float(random.uniform(60, 150))
        elif anomaly_type == "Surcharge Électrique" and type_name in ['Broyeur', 'Pompe', 'Foreuse']:
            data["amperage"] = float(random.uniform(200, 320))
        else:
            # Cas par défaut si le type de machine ne correspond pas à l'anomalie choisie
            data["alert_label"] = "Anomalie Générique"
            data["vibration_rms_mm_s"] *= 3

    return data

def main():
    print("Démarrage du Producteur de télémétrie...")
    
    # Connexion RabbitMQ
    credentials = pika.PlainCredentials(RABBITMQ_CONFIG["user"], RABBITMQ_CONFIG["pass"])
    parameters = pika.ConnectionParameters(RABBITMQ_CONFIG["host"], RABBITMQ_CONFIG["port"], '/', credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    
    channel.queue_declare(queue='telemetry_queue', durable=True)
    
    machines = get_machines()
    print(f"Surveillance de {len(machines)} machines.")
    
    try:
        while True:
            for m_id, t_name in machines:
                payload = generate_telemetry(m_id, t_name)
                channel.basic_publish(
                    exchange='',
                    routing_key='telemetry_queue',
                    body=json.dumps(payload),
                    properties=pika.BasicProperties(delivery_mode=2) # Message persistant
                )
                print(f" [x] Sent data for {m_id}")
            
            print("--- Cycle terminé, attente de 10 secondes ---")
            time.sleep(10)
    except KeyboardInterrupt:
        print("Arrêt du producteur.")
    finally:
        connection.close()

if __name__ == "__main__":
    main()
