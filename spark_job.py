from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, count, desc
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Si dotenv n'est pas installé (ex: dans le conteneur Docker natif), on ignore
    pass

# Détecter si on tourne à l'intérieur de Docker
IN_DOCKER = os.getenv("IN_DOCKER", "false").lower() == "true"

# Configuration PostgreSQL adaptative (hôte local vs réseau Docker interne)
PG_HOST = os.getenv("PGHOST", "postgres" if IN_DOCKER else "localhost")
PG_PORT = os.getenv("PGPORT", "5432" if IN_DOCKER else "5455")
PG_DB = os.getenv("PGDATABASE", "industrial_iot")
PG_USER = os.getenv("PGUSER", "admin")
PG_PASSWORD = os.getenv("PGPASSWORD", "admin123")

SPARK_MASTER = os.getenv("SPARK_MASTER", "spark://spark-master:7077" if IN_DOCKER else "spark://localhost:7077")

JDBC_URL = f"jdbc:postgresql://{PG_HOST}:{PG_PORT}/{PG_DB}"

def main():
    print("Initialisation de la session Spark...")
    
    # Création de la session Spark
    spark = SparkSession.builder \
        .appName("IndustrialIoT_Analysis") \
        .master(SPARK_MASTER) \
        .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
        .getOrCreate()
        
    # Réduire le niveau de log pour y voir plus clair dans le terminal
    spark.sparkContext.setLogLevel("WARN")
    
    print(f"Connecté au Master Spark: {spark.conf.get('spark.master')}")
    print("\n--- Lecture des données depuis PostgreSQL ---")
    
    # 1. Lecture de la table sensor_data
    sensor_df = spark.read \
        .format("jdbc") \
        .option("url", JDBC_URL) \
        .option("dbtable", "sensor_data") \
        .option("user", PG_USER) \
        .option("password", PG_PASSWORD) \
        .option("driver", "org.postgresql.Driver") \
        .load()
        
    # 2. Lecture de la table machines
    machines_df = spark.read \
        .format("jdbc") \
        .option("url", JDBC_URL) \
        .option("dbtable", "machines") \
        .option("user", PG_USER) \
        .option("password", PG_PASSWORD) \
        .option("driver", "org.postgresql.Driver") \
        .load()
        
    # Forcer l'évaluation pour compter le nombre de lignes (Action Spark)
    total_records = sensor_df.count()
    print(f"Total des relevés de télémétrie récupérés : {total_records}")
    
    if total_records == 0:
        print("Aucune donnée à analyser. Terminé.")
        spark.stop()
        return

    print("\n--- Analyse 1 : Statistiques des anomalies (Top 10) ---")
    # Filtrer les données anormales, grouper par machine et compter
    anomalies_df = sensor_df.filter(col("alert_label") != "Normal") \
        .groupBy("machine_id", "alert_label") \
        .agg(count("*").alias("nombre_alertes")) \
        .orderBy(desc("nombre_alertes"))
        
    anomalies_df.show(10, truncate=False)
    
    print("\n--- Analyse 2 : Température et Vibration Moyennes par Modèle ---")
    # Jointure distribuée entre capteurs et machines
    joined_df = sensor_df.join(machines_df, "machine_id")
    
    stats_df = joined_df.groupBy("type_id", "brand_id") \
        .agg(
            avg("oil_temp_c").alias("temp_moyenne"),
            avg("vibration_rms_mm_s").alias("vibration_moyenne"),
            count("*").alias("total_releves")
        ).orderBy(desc("temp_moyenne"))
        
    stats_df.show()
    
    print("\nAnalyse distribuée terminée avec succès !")
    
    # Fermeture propre de la session
    spark.stop()

if __name__ == "__main__":
    main()
