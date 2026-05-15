# 🏭 Système de Supervision et d'Analyse Prédictive - Industrial IoT

Bienvenue dans le projet **Industrial IoT**. Ce projet est une plateforme complète pour la simulation, l'ingestion, le traitement, la visualisation et l'analyse prédictive de données télémétriques provenant de machines industrielles lourdes (broyeurs, pompes, foreuses, excavatrices, camions).

## 🌟 Fonctionnalités Principales

1. **Simulation de Parc Machine** : Génération de données capteurs réalistes (Vibrations, Température, Consommation, Ampérage) via un script producteur.
2. **Ingestion Hautes Performances** : Utilisation de **RabbitMQ** pour la gestion de la file de messages asynchrone.
3. **Stockage Structuré** : Base de données **PostgreSQL** modélisant le parc (marques, types, localisations, configurations, historique de maintenance) et les séries temporelles.
4. **Tableau de Bord interactif** : Interface web (HTML/CSS/JS + Flask) permettant de :
   - Superviser l'état du parc en temps réel.
   - Configurer les seuils d'alertes par modèle de machine.
   - Gérer les services d'arrière-plan (Démarrage/Arrêt de la simulation).
5. **Analyse Distribuée (Big Data)** : Un cluster **Apache Spark** intégré pour réaliser des statistiques descriptives sur de grands volumes de données.
6. **Intelligence Artificielle (Maintenance Prédictive)** : Entraînement d'un modèle **Random Forest** (PySpark MLlib) capable de prédire le risque d'anomalie d'une machine en se basant sur ses indicateurs physiques (vibration, température, vitesse, consommation) et environnementaux (élévation/profondeur).
7. **Détection par Similarité (Vector Database)** : Utilisation de **Qdrant** pour stocker et comparer les "signatures" mathématiques des pannes passées avec les données en temps réel.

---

## 🏗️ Architecture du Projet

```text
[ producteur.py ] ---> (RabbitMQ) ---> [ consumer.py ] ---> (PostgreSQL)
       |                                                         |
  Générateur                                                     +---> [ Qdrant ] (Vector DB)
 de données                                                      |       ^
                                                                 v       |
                                                     [ cluster Apache Spark ]
                                                     - spark_job.py (Stats)
                                                     - predictive_job.py (IA)
                                                                 |
                                                                 v
[ Tableau de bord Web ] <--- (API REST Flask) <---------- (PostgreSQL)
```

### Stack Technique
- **Backend / API** : Python, Flask
- **Message Broker** : RabbitMQ
- **Base de Données Relationnelle** : PostgreSQL
- **Base de Données Vectorielle** : Qdrant
- **Big Data & Machine Learning** : Apache Spark (PySpark), Spark MLlib
- **Observabilité** : Grafana
- **Frontend** : Vanilla JS, HTML, CSS natif
- **Déploiement** : Docker & Docker-compose

---

## 🚀 Guide de Démarrage Rapide

### 1. Démarrer l'infrastructure
Assurez-vous d'avoir Docker et Docker-compose installés, puis lancez les services en arrière-plan :
```bash
docker-compose up -d
```
*(Pour plus de détails sur les ports et les services, consultez le fichier `SERVICES_SETUP.md`)*.

### 2. Démarrer l'interface web (Flask)
Dans votre environnement virtuel Python, installez les dépendances et lancez le serveur :
```bash
pip install -r requirements.txt
python app.py
```
Accédez ensuite au tableau de bord via : **http://localhost:5000**

### 3. Initialiser le système via le Tableau de Bord
1. Allez dans l'onglet **Configuration** de l'interface.
2. Cliquez sur le bouton **Créer les tables** pour initialiser la base de données PostgreSQL avec le schéma défini dans `matrice.sql` (cela ajoute les machines de base et configure les relations).
3. Dans la section *Services de Télémétrie*, cliquez sur **▶ Démarrer** pour le *Consommateur* puis pour le *Producteur*.
4. Allez dans l'onglet **Machines > Etat du parc** pour voir les données arriver en temps réel !

---

## 🧠 Utiliser l'Analyse Prédictive (IA)

Pour exploiter le système de maintenance prédictive :

1. Laissez le *Producteur* tourner suffisamment longtemps pour générer au moins **100 relevés** de capteurs.
2. Naviguez vers l'onglet **Machines > Analyse Prédictive (IA)**.
3. Cliquez sur **▶ Entraîner & Prédire**. Le backend va soumettre un job au cluster Spark en utilisant `predictive_job.py`.
4. Le modèle *Random Forest* va :
   - Lire l'historique complet des capteurs.
   - S'enrichir de l'**élévation de la machine** (qui impacte la pression et la température).
   - S'entraîner à différencier un fonctionnement normal d'une anomalie.
   - Appliquer ce modèle aux données récentes.
5. Cliquez sur **Actualiser** après 20 secondes : le tableau affichera le niveau de risque pour chaque machine (Faible, Modéré, Critique).

---

## 🔍 Recherche de Signatures d'Anomalies (Qdrant)

Une autre approche de maintenance prédictive implémentée repose sur la similarité vectorielle :

1. Exécutez le script dédié : `python qdrant_signatures.py`
2. Ce script va analyser toutes les pannes enregistrées dans PostgreSQL.
3. Il convertit chaque état critique en un **vecteur mathématique** et le stocke dans la base de données **Qdrant**.
4. Vous pouvez ensuite utiliser cette base pour comparer une télémétrie en temps réel avec des milliers de signatures de pannes historiques pour voir si la situation correspond (à plus de 98% de similarité) à un événement passé connu.

---

## 📁 Structure des fichiers

- `docker-compose.yml` : Infrastructure des conteneurs (Postgres, RabbitMQ, Spark, Grafana, Qdrant).
- `app.py` : Serveur Flask, sert l'interface web et les API REST.
- `index.html` : L'interface utilisateur.
- `matrice.sql` : Script de création et de remplissage initial (seed) de la base de données.
- `create_tables.py` : Exécuteur Python pour le script SQL.
- `producer.py` : Script simulant les machines industrielles, insère les anomalies, et publie sur RabbitMQ.
- `consumer.py` : Script écoutant RabbitMQ et sauvegardant les données brutes dans PostgreSQL.
- `spark_job.py` : Job Spark pour le calcul asynchrone des statistiques récurrentes (Big Data).
- `predictive_job.py` : Job Spark ML (Machine Learning) pour l'entraînement du modèle prédictif et l'inférence.
- `qdrant_signatures.py` : Script d'extraction des pannes historiques, vectorisation et moteur de recherche par similarité via Qdrant.
- `grafana_observability_dashboard.json` : Tableau de bord prêt à l'emploi pour superviser les capteurs dans Grafana.
- `SERVICES_SETUP.md` : Guide de dépannage spécifique à Docker et aux identifiants.
