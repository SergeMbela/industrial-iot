import pika
import json
import psycopg2
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

def callback(ch, method, properties, body):
    data = json.loads(body)
    print(f" [r] Received telemetry for {data['machine_id']}")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        query = """
            INSERT INTO sensor_data (
                machine_id, fuel_consumption_lh, amperage, idle_time_pct,
                vibration_rms_mm_s, vibration_accel_g, hours_hmr, cycle_speed_s,
                oil_viscosity_cst, silicon_ppm, water_ppm, tbn_value,
                oil_temp_c, oil_pressure_bar, exhaust_temp_c, turbo_boost_bar,
                filter_diff_pressure_bar, ambient_temp, humidity_percent, alert_label
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            data['machine_id'], data['fuel_consumption_lh'], data['amperage'], data['idle_time_pct'],
            data['vibration_rms_mm_s'], data['vibration_accel_g'], data['hours_hmr'], data['cycle_speed_s'],
            data['oil_viscosity_cst'], data['silicon_ppm'], data['water_ppm'], data['tbn_value'],
            data['oil_temp_c'], data['oil_pressure_bar'], data['exhaust_temp_c'], data['turbo_boost_bar'],
            data['filter_diff_pressure_bar'], data['ambient_temp'], data['humidity_percent'],
            data.get('alert_label', 'Normal')
        )
        
        cur.execute(query, values)
        conn.commit()
        cur.close()
        conn.close()
        
        # Ack message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        print(f"Error processing message: {e}")
        # En cas d'erreur, on ne rejette pas forcément avec requeue=True pour éviter les boucles infinies
        # selon la criticité. Ici on n'acquitte juste pas.

def main():
    print("Démarrage du Consommateur de télémétrie...")
    
    credentials = pika.PlainCredentials(RABBITMQ_CONFIG["user"], RABBITMQ_CONFIG["pass"])
    parameters = pika.ConnectionParameters(RABBITMQ_CONFIG["host"], RABBITMQ_CONFIG["port"], '/', credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    
    channel.queue_declare(queue='telemetry_queue', durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='telemetry_queue', on_message_callback=callback)
    
    print(' [*] En attente de messages. Appuyez sur CTRL+C pour arrêter.')
    channel.start_consuming()

if __name__ == "__main__":
    main()
