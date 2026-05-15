import os
from pathlib import Path

# pyrefly: ignore [missing-import]
from flask import Flask, jsonify, request, send_from_directory
import psycopg2
import subprocess
import sys

try:
    from create_tables import create_tables, DB_CONFIG
except ImportError as exc:
    raise SystemExit(f"Impossible d'importer create_tables: {exc}")

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__, static_folder='static')

# Gestionnaires de processus en arrière-plan
processes = {
    "producer": None,
    "consumer": None
}

def get_process_status(name):
    proc = processes.get(name)
    if proc is None:
        return "stopped"
    if proc.poll() is None:
        return "running"
    return "stopped"


@app.route("/", methods=["GET"])
def index():
    # Envoi de l'index.html qui est à la racine
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/create-tables", methods=["POST"])
def create_tables_route():
    try:
        create_tables()
        return jsonify({"status": "success", "message": "Tables créées avec succès."})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/add-brand", methods=["POST"])
def add_brand():
    data = request.json
    name = data.get("name")
    country = data.get("country")
    support_contact = data.get("support_contact")

    if not name:
        return jsonify({"status": "error", "message": "Le nom de la marque est requis."}), 400

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO brands (name, country, support_contact) VALUES (%s, %s, %s) RETURNING brand_id",
                (name, country, support_contact)
            )
            brand_id = cursor.fetchone()[0]
            conn.commit()
        return jsonify({"status": "success", "message": f"Marque '{name}' ajoutée avec l'ID {brand_id}."})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route("/get-brands", methods=["GET"])
def get_brands():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("SELECT brand_id, name FROM brands ORDER BY name")
            brands = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
        return jsonify(brands)
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route("/get-machine-types", methods=["GET"])
def get_machine_types():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("SELECT type_id, name FROM machine_types ORDER BY name")
            types = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
        return jsonify(types)
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route("/get-localisations", methods=["GET"])
def get_localisations():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("SELECT localisation_id, name, type FROM localisations ORDER BY name")
            locs = [{"id": row[0], "name": row[1], "type": row[2]} for row in cursor.fetchall()]
        return jsonify(locs)
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route("/get-machines", methods=["GET"])
def get_machines():
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 10))
        offset = (page - 1) * per_page

        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # Récupérer le total pour la pagination
            cursor.execute("SELECT COUNT(*) FROM machines")
            total_count = cursor.fetchone()[0]

            # Récupérer les données paginées
            cursor.execute("""
                SELECT 
                    m.machine_id, 
                    t.name as type_name, 
                    b.name as brand_name, 
                    l.name as loc_name, 
                    m.niveau_elevation_machine, 
                    m.date_achat, 
                    m.status
                FROM machines m
                LEFT JOIN machine_types t ON m.type_id = t.type_id
                LEFT JOIN brands b ON m.brand_id = b.brand_id
                LEFT JOIN localisations l ON m.localisation_id = l.localisation_id
                ORDER BY m.machine_id
                LIMIT %s OFFSET %s
            """, (per_page, offset))
            
            machines = [
                {
                    "id": row[0],
                    "type": row[1],
                    "brand": row[2],
                    "localisation": row[3],
                    "elevation": row[4],
                    "date_achat": row[5].strftime("%Y-%m-%d") if row[5] else None,
                    "status": row[6]
                }
                for row in cursor.fetchall()
            ]
        return jsonify({
            "machines": machines,
            "total": total_count,
            "page": page,
            "per_page": per_page,
            "total_pages": (total_count + per_page - 1) // per_page
        })
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route("/get-machine-configs", methods=["GET"])
def get_machine_configs():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    c.config_id, 
                    t.name as type_name, 
                    b.name as brand_name, 
                    c.fuel_consumption_max_lh, c.amperage_max_a, c.idle_time_max_pct,
                    c.temp_threshold_max, c.vibration_threshold_mm_s, c.vibration_acceleration_g_max, c.cycle_time_nominal_s,
                    c.oil_viscosity_min_cst, c.oil_viscosity_max_cst, c.silicon_ppm_max, c.water_ppm_max, c.tbn_min,
                    c.oil_pressure_min_bar, c.pressure_nominal_bar, c.exhaust_temp_max_c, c.turbo_pressure_max_bar, c.filter_diff_pressure_max_bar
                FROM machine_configurations c
                JOIN machine_types t ON c.type_id = t.type_id
                JOIN brands b ON c.brand_id = b.brand_id
                ORDER BY t.name, b.name
            """)
            configs = []
            for row in cursor.fetchall():
                configs.append({
                    "id": row[0], "type": row[1], "brand": row[2],
                    "perf": {"fuel": float(row[3] or 0), "amp": float(row[4] or 0), "idle": float(row[5] or 0)},
                    "mech": {"temp": float(row[6] or 0), "vib_v": float(row[7] or 0), "vib_a": float(row[8] or 0), "cycle": float(row[9] or 0)},
                    "fluid": {"visc_min": float(row[10] or 0), "visc_max": float(row[11] or 0), "si": float(row[12] or 0), "water": float(row[13] or 0), "tbn": float(row[14] or 0)},
                    "thermal": {"oil_p": float(row[15] or 0), "sys_p": float(row[16] or 0), "exhaust": float(row[17] or 0), "turbo": float(row[18] or 0), "filter": float(row[19] or 0)}
                })
        return jsonify(configs)
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route("/update-machine-config", methods=["POST"])
def update_machine_config():
    data = request.json
    c_id = data.get("id")
    # On peut recevoir les champs à plat ou groupés, ici on va simplifier pour le form
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # Update partiel ou complet selon ce qui est envoyé
            # Ici on fait un update complet pour la démonstration
            cursor.execute(
                """UPDATE machine_configurations SET 
                   fuel_consumption_max_lh = %s, amperage_max_a = %s, idle_time_max_pct = %s,
                   temp_threshold_max = %s, vibration_threshold_mm_s = %s, vibration_acceleration_g_max = %s,
                   oil_pressure_min_bar = %s, pressure_nominal_bar = %s, exhaust_temp_max_c = %s
                   WHERE config_id = %s""",
                (data.get("fuel"), data.get("amp"), data.get("idle"), 
                 data.get("temp"), data.get("vib_v"), data.get("vib_a"),
                 data.get("oil_p"), data.get("sys_p"), data.get("exhaust"), c_id)
            )
            conn.commit()
        return jsonify({"status": "success", "message": "Configuration mise à jour."})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route("/add-machine", methods=["POST"])
def add_machine():
    data = request.json
    m_id = data.get("machine_id")
    type_id = data.get("type_id")
    brand_id = data.get("brand_id")
    loc_id = data.get("localisation_id")
    elevation = data.get("niveau_elevation_machine")
    date_achat = data.get("date_achat")

    if not m_id or not type_id:
        return jsonify({"status": "error", "message": "ID et Type de machine sont requis."}), 400

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO machines 
                   (machine_id, type_id, brand_id, localisation_id, niveau_elevation_machine, date_achat) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (m_id, type_id, brand_id, loc_id, elevation, date_achat)
            )
            conn.commit()
        return jsonify({"status": "success", "message": f"Machine '{m_id}' ajoutée avec succès."})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route("/api/processes/status", methods=["GET"])
def process_status():
    return jsonify({
        "producer": get_process_status("producer"),
        "consumer": get_process_status("consumer")
    })


@app.route("/api/processes/<action>/<name>", methods=["POST"])
def manage_process(action, name):
    if name not in processes:
        return jsonify({"status": "error", "message": "Processus inconnu"}), 400
        
    current_status = get_process_status(name)
    
    if action == "start":
        if current_status == "running":
            return jsonify({"status": "success", "message": f"{name} est déjà en cours."})
            
        script_path = os.path.join(BASE_DIR, f"{name}.py")
        try:
            # Lancer le script en arrière-plan
            proc = subprocess.Popen([sys.executable, script_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            processes[name] = proc
            return jsonify({"status": "success", "message": f"{name} démarré avec succès."})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
            
    elif action == "stop":
        if current_status == "stopped":
            return jsonify({"status": "success", "message": f"{name} est déjà arrêté."})
            
        proc = processes[name]
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            
        processes[name] = None
        return jsonify({"status": "success", "message": f"{name} arrêté avec succès."})
        
    return jsonify({"status": "error", "message": "Action invalide"}), 400


@app.route("/get-latest-telemetry", methods=["GET"])
def get_latest_telemetry():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # Récupère la dernière ligne de télémétrie, le statut, et les seuils de configuration
            cursor.execute("""
                SELECT DISTINCT ON (s.machine_id) 
                    s.machine_id, 
                    s.timestamp, 
                    s.oil_temp_c, 
                    s.cycle_speed_s,
                    m.status,
                    s.alert_label,
                    c.temp_threshold_max
                FROM sensor_data s
                JOIN machines m ON s.machine_id = m.machine_id
                LEFT JOIN machine_configurations c ON m.type_id = c.type_id AND m.brand_id = c.brand_id
                ORDER BY s.machine_id, s.timestamp DESC;
            """)
            
            telemetry = []
            for row in cursor.fetchall():
                telemetry.append({
                    "machine_id": row[0],
                    "timestamp": row[1].isoformat() if row[1] else None,
                    "temp": float(row[2] or 0),
                    "speed": float(row[3] or 0),
                    "status": row[4],
                    "alert_label": row[5] if row[5] else "Normal",
                    "temp_max": float(row[6]) if row[6] is not None else 85.0
                })
        return jsonify(telemetry)
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route("/api/machine-stats/<machine_id>", methods=["GET"])
def get_machine_stats(machine_id):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # On prend les stats sur les dernières 24h ou tout l'historique récent
            cursor.execute("""
                SELECT 
                    COUNT(*),
                    ROUND(AVG(oil_temp_c), 2), MAX(oil_temp_c),
                    ROUND(AVG(vibration_rms_mm_s), 2), MAX(vibration_rms_mm_s),
                    ROUND(AVG(fuel_consumption_lh), 2),
                    COUNT(*) FILTER (WHERE alert_label != 'Normal')
                FROM sensor_data
                WHERE machine_id = %s
            """, (machine_id,))
            
            row = cursor.fetchone()
            
            if not row or row[0] == 0:
                return jsonify({"status": "error", "message": "Aucune donnée trouvée"}), 404
                
            stats = {
                "total_records": row[0],
                "avg_temp": float(row[1] or 0),
                "max_temp": float(row[2] or 0),
                "avg_vib": float(row[3] or 0),
                "max_vib": float(row[4] or 0),
                "avg_fuel": float(row[5] or 0),
                "alerts_count": row[6] or 0
            }
            
            # Récupération des 5 dernières alertes
            cursor.execute("""
                SELECT timestamp, alert_label 
                FROM sensor_data 
                WHERE machine_id = %s AND alert_label != 'Normal'
                ORDER BY timestamp DESC LIMIT 5
            """, (machine_id,))
            
            recent_alerts = [{"time": r[0].isoformat() if r[0] else None, "label": r[1]} for r in cursor.fetchall()]
            stats["recent_alerts"] = recent_alerts

        return jsonify(stats)
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@app.route("/api/global-monitoring", methods=["GET"])
def get_global_monitoring():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        with conn.cursor() as cursor:
            # 1. Total des enregistrements et dernière MAJ
            cursor.execute("SELECT COUNT(*), MAX(timestamp) FROM sensor_data")
            row_count = cursor.fetchone()
            total_records = row_count[0]
            last_update = row_count[1]
            
            # 2. Alertes sur la dernière heure
            cursor.execute("""
                SELECT COUNT(*) 
                FROM sensor_data 
                WHERE alert_label != 'Normal' 
                AND timestamp >= NOW() - INTERVAL '1 hour'
            """)
            recent_alerts = cursor.fetchone()[0]
            
            # 3. Machines actives
            cursor.execute("SELECT COUNT(DISTINCT machine_id) FROM machines")
            total_machines = cursor.fetchone()[0]
            
            # Considéré en ligne si données dans les 2 dernières minutes
            cursor.execute("""
                SELECT COUNT(DISTINCT machine_id) 
                FROM sensor_data 
                WHERE timestamp >= NOW() - INTERVAL '2 minutes'
            """)
            online_machines = cursor.fetchone()[0]

        return jsonify({
            "total_records": total_records,
            "last_update": last_update.isoformat() if last_update else None,
            "recent_alerts": recent_alerts,
            "total_machines": total_machines,
            "online_machines": online_machines
        })
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
    finally:
        if 'conn' in locals():
            conn.close()


if __name__ == "__main__":

    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
