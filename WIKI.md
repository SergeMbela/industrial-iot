# 📖 Wiki Développeur - Industrial IoT Platform

Bienvenue sur le Wiki Développeur de la plateforme **Industrial IoT (Système de Supervision et d'Analyse Prédictive)**. 

Ce document sert de guide de référence pour comprendre l'architecture, le fonctionnement des composants, le schéma de données et les procédures opérationnelles pour le développement et la maintenance de la plateforme.

---

## 🏗️ 1. Architecture Générale et Flux de Données

Le système est conçu pour simuler et analyser en temps réel les données de télémétrie d'un parc de machines industrielles lourdes opérant dans des conditions extrêmes (mines souterraines ou à ciel ouvert).

### Flux de données de bout en bout

```mermaid
graph TD
    subgraph Simulation & Source
        Prod[producer.py - Simulateur]
    end

    subgraph Message Broker
        RMQ[RabbitMQ - telemetry_queue]
    end

    subgraph Ingestion & Stockage
        Cons[consumer.py - Ingesteur]
        DB[(PostgreSQL)]
    end

    subgraph Intelligence & Recherche
        Qdr[Qdrant - Vector DB]
        Spark[predictive_job.py - Spark MLlib]
    end

    subgraph Supervision & IHM
        Flask[app.py - API Flask]
        UI[index.html - Dashboard Web]
        Graf[Grafana - Observabilité]
    end

    Prod -->|AMQP (JSON)| RMQ
    RMQ -->|Consommation| Cons
    Cons -->|Insertion SQL| DB
    Cons -->|Comparaison Temps Réel| Qdr
    DB -->|Historique| Spark
    Spark -->|Entraînement RF| Spark
    Spark -->|Sauvegarde des Alertes Prédictives| DB
    DB -->|Lecture des données/alertes| Flask
    Flask -->|REST API| UI
    DB -->|Visualisation Temporelle| Graf
```

1. **Génération (`producer.py`)** : Simule 5 types de machines (Broyeur, Foreuse, Pompe, Excavatrice, Camion). Génère des métriques physiques normales et simule 5% d'anomalies spécifiques.
2. **Broker de Messages (`RabbitMQ`)** : Assure la résilience face aux pannes réseau en mettant en file d'attente les relevés télémétriques.
3. **Ingestion (`consumer.py`)** : Dépile les messages de RabbitMQ, les valide, les insère dans PostgreSQL et interroge Qdrant pour la détection de similarité de pannes.
4. **Analyses & IA (`PySpark` & `Qdrant`)** :
   - **Spark MLlib** effectue de la maintenance prédictive (classification via Random Forest) pour détecter la probabilité de panne future.
   - **Qdrant** sert de moteur de recherche de similarités vectorielles à plus de 98% par rapport à des pannes historiques.
5. **Supervision (`Flask` / `Grafana`)** : Offre une IHM complète pour contrôler le système et visualiser l'état du parc et des alertes.

---

## 🗄️ 2. Schéma de la Base de Données (PostgreSQL)

Le schéma est défini dans le fichier [matrice.sql](file:///wsl.localhost/Ubuntu/home/sergembela/projets/industrial_iot/matrice.sql). Il est structuré en plusieurs niveaux :

### Niveaux de Données

```
 📊 Tables de Référence  ──>  🚜 Parc Machines  ──>  📈 Télémétrie & Alertes
   - brands                    - machines               - sensor_data
   - machine_types             - maintenance_plan       - predictive_alerts
   - localisations             - ventilation_fans       - ventilation_log
   - machine_configurations                             - maintenance_log
```

### Description des tables clés

| Table | Rôle / Description | Clé Primaire | Clés Étrangères |
| :--- | :--- | :--- | :--- |
| **`brands`** | Liste des constructeurs (ex: Caterpillar, Metso Outotec, Komatsu). | `brand_id` | - |
| **`machine_types`** | Catégories d'équipements (Broyeur, Foreuse, Pompe, etc.). | `type_id` | - |
| **`localisations`** | Zones de travail de la mine (Surface, Souterrain, Niveau -800). | `localisation_id` | - |
| **`machine_configurations`** | Seuils critiques nominaux (vibration max, ampérage, pression, etc.) par type et marque. | `config_id` | `type_id`, `brand_id` |
| **`machines`** | Liste des actifs du parc, leur localisation et leur altitude/profondeur. | `machine_id` | `type_id`, `brand_id`, `localisation_id` |
| **`sensor_data`** | Table de séries temporelles stockant toutes les mesures télémétriques physiques et environnementales. | `id` (BIGSERIAL) | `machine_id` |
| **`predictive_alerts`** | Alertes et prédictions générées périodiquement par le job d'IA Spark MLlib. | Auto-gérée par Spark | `machine_id` |

---

## 🚜 3. Zoom sur les Composants Logiciels

### A. Le Simulateur de Télémétrie (`producer.py`)
Le fichier [producer.py](file:///wsl.localhost/Ubuntu/home/sergembela/projets/industrial_iot/producer.py) génère des données réalistes toutes les 10 secondes pour chaque machine enregistrée dans la base de données.
- **Paramètres simulés** : Consommation de carburant, ampérage, vibrations (RMS et accélération), température de l'huile, pression de l'huile, température d'échappement, variables environnementales (température ambiante, humidité).
- **Anomalies simulées (5%)** :
  - *Vibration Excessive* (vibrations élevées)
  - *Surchauffe Moteur* (huile + échappement)
  - *Basse Pression Huile* (chute de pression)
  - *Filtre Colmaté* (pression différentielle élevée)
  - *Contamination Fluide* (taux élevé d'eau et de silicium dans l'huile)
  - *Surcharge Électrique* (ampérage élevé pour Broyeur, Pompe, Foreuse)

### B. L'Ingesteur (`consumer.py`)
Le fichier [consumer.py](file:///wsl.localhost/Ubuntu/home/sergembela/projets/industrial_iot/consumer.py) tourne en tâche de fond pour écouter la queue RabbitMQ.
- Il écrit chaque message reçu dans la table `sensor_data`.
- Pour chaque relevé, il appelle Qdrant afin de vérifier si les données actuelles de la machine ressemblent à une signature d'anomalie enregistrée à plus de 98% (similarité cosinus).

### C. Le Moteur de Similarité Vectorielle (`qdrant_signatures.py`)
Le script [qdrant_signatures.py](file:///wsl.localhost/Ubuntu/home/sergembela/projets/industrial_iot/qdrant_signatures.py) permet d'indexer les anomalies passées.
- **Vecteur (taille 5)** : `[Vibration, Ampérage, Température Huile, Vitesse de cycle, Carburant]` normalisé à la volée.
- **Distance** : Cosine (similarité cosinus).
- Il récupère les pannes historiques de `sensor_data` (où `alert_label != 'Normal'`), crée leurs signatures, et les charge dans la collection `anomaly_signatures` sur Qdrant.

### D. Le Job de Maintenance Prédictive (`predictive_job.py`)
Le job [predictive_job.py](file:///wsl.localhost/Ubuntu/home/sergembela/projets/industrial_iot/predictive_job.py) est un script PySpark qui :
1. Se connecte à PostgreSQL via JDBC.
2. Joint les tables de capteurs et de parc pour intégrer les métadonnées (ex: l'élévation).
3. Entraîne un modèle **Random Forest Classifier** (20 arbres) si la base contient au moins 100 enregistrements.
4. Évalue la précision (Accuracy).
5. Calcule les prédictions sur les données récentes et les écrit dans la table `predictive_alerts`.

---

## 🛠️ 4. Guide des Commandes de Développement

### Démarrage des Services Docker
S'assurer que Docker est démarré et lancer les services d'infrastructure (RabbitMQ, Postgres, Qdrant, Spark Master/Worker, Grafana) :
```bash
docker-compose up -d
```

### Démarrage de l'Application Flask
```bash
# Activation de l'environnement virtuel (exemple Windows WSL/Ubuntu)
source .venv/bin/activate
pip install -r requirements.txt

# Lancement de l'application Flask
python app.py
```
L'IHM est accessible sur [http://localhost:5000](http://localhost:5000).

### Initialisation de la Base de Données
Dans l'onglet **Configuration** de l'IHM, cliquer sur **Créer les tables** (ce qui exécute `create_tables.py`) pour structurer la base Postgres.

### Alimenter et Lancer la Recherche Vectorielle (Qdrant)
Pour générer les signatures d'anomalies à partir de l'historique et les charger dans Qdrant :
```bash
python qdrant_signatures.py
```

### Entraîner le Modèle Prédictif (Spark MLlib)
Lorsque vous avez accumulé plus de 100 relevés télémétriques (vous pouvez démarrer les services de télémétrie depuis l'IHM ou lancer `python consumer.py` et `python producer.py` séparément) :
```bash
python predictive_job.py
```
Ce job peut également être déclenché depuis le bouton dédié dans l'onglet **Analyse Prédictive** de l'IHM Flask.

---

## 🧭 5. Structure des Fichiers Clés du Projet

- 🐳 **`docker-compose.yml`** : Orchestre les conteneurs locaux (Postgres, RabbitMQ, Grafana, Qdrant, Apache Spark).
- 📜 **`matrice.sql`** : Schéma SQL relationnel complet avec triggers, index et données de référence initiales.
- ⚙️ **`create_tables.py`** : Script utilitaire Python pour exécuter `matrice.sql` sur PostgreSQL.
- 🌐 **`app.py`** : API Flask et gestion des sous-processus d'ingestion/simulation.
- 🖥️ **`index.html`** : Page de dashboard unique de l'IHM (utilisant Bootstrap et Chart.js).
- 🚜 **`producer.py`** : Simulation réaliste de données physiques de machines avec injection d'anomalies de façon stochastique.
- 📥 **`consumer.py`** : Ingesteur AMQP RabbitMQ avec contrôle de similarité vectorielle Qdrant en temps réel.
- 🧠 **`predictive_job.py`** : Pipeline d'entraînement et d'inférence de maintenance prédictive Spark MLlib.
- 📐 **`qdrant_signatures.py`** : Initialisation de la base vectorielle Qdrant et tests d'ingestion de signatures.
- 📝 **`SERVICES_SETUP.md`** : Guide de démarrage technique et paramètres de configuration des ports/credentials.
