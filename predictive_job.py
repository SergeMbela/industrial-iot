from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when
from pyspark.ml.feature import VectorAssembler, StringIndexer
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

IN_DOCKER = os.getenv("IN_DOCKER", "false").lower() == "true"
PG_HOST = os.getenv("PGHOST", "postgres" if IN_DOCKER else "localhost")
PG_PORT = os.getenv("PGPORT", "5432" if IN_DOCKER else "5455")
PG_DB = os.getenv("PGDATABASE", "industrial_iot")
PG_USER = os.getenv("PGUSER", "admin")
PG_PASSWORD = os.getenv("PGPASSWORD", "admin123")
SPARK_MASTER = os.getenv("SPARK_MASTER", "spark://spark-master:7077" if IN_DOCKER else "local[*]")

JDBC_URL = f"jdbc:postgresql://{PG_HOST}:{PG_PORT}/{PG_DB}"

def main():
    print("Initialisation de la session Spark pour l'Analyse Prédictive...")
    spark = SparkSession.builder \
        .appName("IndustrialIoT_PredictiveMaintenance") \
        .master(SPARK_MASTER) \
        .config("spark.jars.packages", "org.postgresql:postgresql:42.6.0") \
        .getOrCreate()
        
    spark.sparkContext.setLogLevel("WARN")
    
    print("\n--- Lecture des données depuis PostgreSQL ---")
    try:
        sensor_df = spark.read \
            .format("jdbc") \
            .option("url", JDBC_URL) \
            .option("dbtable", "sensor_data") \
            .option("user", PG_USER) \
            .option("password", PG_PASSWORD) \
            .option("driver", "org.postgresql.Driver") \
            .load()
            
        machines_df = spark.read \
            .format("jdbc") \
            .option("url", JDBC_URL) \
            .option("dbtable", "machines") \
            .option("user", PG_USER) \
            .option("password", PG_PASSWORD) \
            .option("driver", "org.postgresql.Driver") \
            .load()
            
        # Jointure pour récupérer l'élévation
        sensor_df = sensor_df.join(machines_df.select("machine_id", "niveau_elevation_machine"), "machine_id", "left")
    except Exception as e:
        print(f"Erreur de lecture de la DB: {e}")
        spark.stop()
        return

    if sensor_df.count() < 100:
        print("Pas assez de données pour l'entraînement (min 100). Veuillez générer plus de données.")
        spark.stop()
        return

    print("\n--- Préparation des données (Feature Engineering) ---")
    # Création du label: 0.0 si 'Normal', 1.0 si 'Anomalie'
    df_prepared = sensor_df.withColumn(
        "label", 
        when(col("alert_label") == "Normal", 0.0).otherwise(1.0)
    )
    
    # Remplacer les valeurs nulles par 0
    df_prepared = df_prepared.fillna(0)

    # Assembler les features
    assembler = VectorAssembler(
        inputCols=["vibration_rms_mm_s", "amperage", "oil_temp_c", "cycle_speed_s", "fuel_consumption_lh", "niveau_elevation_machine"],
        outputCol="features"
    )
    
    data = assembler.transform(df_prepared)

    print("\n--- Entraînement du Modèle Random Forest ---")
    # Séparation train/test
    train_data, test_data = data.randomSplit([0.8, 0.2], seed=42)
    
    rf = RandomForestClassifier(featuresCol="features", labelCol="label", numTrees=20)
    model = rf.fit(train_data)
    
    print("\n--- Évaluation du Modèle ---")
    predictions = model.transform(test_data)
    
    evaluator = MulticlassClassificationEvaluator(
        labelCol="label", predictionCol="prediction", metricName="accuracy"
    )
    accuracy = evaluator.evaluate(predictions)
    print(f"Précision du modèle (Accuracy) : {accuracy:.2%}")
    
    # Afficher quelques prédictions
    print("\nÉchantillon des prédictions (0=Normal, 1=Anomalie) :")
    predictions.select("machine_id", "alert_label", "prediction", "probability").show(10, truncate=False)

    print("\n--- Sauvegarde des prédictions dans PostgreSQL ---")
    # On sauvegarde les prédictions sur les données récentes (par exemple les 500 dernières lignes)
    recent_preds = model.transform(data).orderBy(col("timestamp").desc()).limit(500)
    
    # On prépare le format pour PostgreSQL
    final_df = recent_preds.select(
        col("machine_id"), 
        col("timestamp"), 
        col("alert_label").alias("actual_label"), 
        col("prediction").alias("predicted_anomaly_flag")
    )
    
    final_df.write \
        .format("jdbc") \
        .option("url", JDBC_URL) \
        .option("dbtable", "predictive_alerts") \
        .option("user", PG_USER) \
        .option("password", PG_PASSWORD) \
        .option("driver", "org.postgresql.Driver") \
        .mode("overwrite") \
        .save()
        
    print("Table 'predictive_alerts' mise à jour avec succès.")
    spark.stop()

if __name__ == "__main__":
    main()
