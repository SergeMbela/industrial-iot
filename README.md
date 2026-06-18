🏭 Système de Supervision et d'Analyse Prédictive - Industrial IoT
Bienvenue dans le projet Industrial IoT. Ce projet est une plateforme complète développée pour répondre au besoin de simulation réaliste avant l'intégration de données de production réelles. Il permet la simulation, l'ingestion, le traitement, la visualisation et l'analyse prédictive de données télémétriques provenant de machines industrielles lourdes (broyeurs, pompes, foreuses, excavatrices, camions).

📖 **[Consulter le Wiki Développeur (WIKI.md)](WIKI.md)** pour une description détaillée de l'architecture, du schéma de la base de données et des commandes de développement.


Note sur le contexte opérationnel : Le système est conçu pour modéliser des environnements de travail exigeants. Les capteurs simulés prennent en compte l'impact direct de conditions sévères (humidité, poussière, chaleur intense) qui altèrent la précision des mesures et accélèrent l'usure des composants. De plus, le simulateur intègre des contraintes réseau réelles (latence, gigue, pertes de paquets) propres aux infrastructures On-premise, Starlink ou Wi-Fi industriel, testant ainsi la résilience du système d'ingestion.

🌟 Fonctionnalités Principales
Simulation de Parc Machine : Génération de données capteurs réalistes (Vibrations, Température, Consommation, Ampérage) intégrant des variables exogènes et des paramètres de connectivité.

Ingestion Hautes Performances : Utilisation de RabbitMQ pour la gestion de la file de messages asynchrone, robuste face aux coupures réseau.

Stockage Structuré : Base de données PostgreSQL modélisant le parc (marques, types, localisations, configurations, maintenance) et les séries temporelles.

Tableau de Bord interactif : Interface web (Flask) pour la supervision, la configuration des seuils d'alertes et la gestion des services d'arrière-plan.

Analyse Distribuée (Big Data) : Cluster Apache Spark intégré pour les statistiques descriptives à grande échelle.

Intelligence Artificielle (Maintenance Prédictive) : Modèle Random Forest (PySpark MLlib) corrélant indicateurs physiques, environnementaux et qualité de transmission réseau.

Détection par Similarité (Vector Database) : Utilisation de Qdrant pour comparer les signatures mathématiques des pannes passées avec la télémétrie temps réel.

🏗️ Architecture du Projet
Plaintext
[ producteur.py ] --(Reseau: Starlink/Wifi/On-prem)--> (RabbitMQ) ---> [ consumer.py ] ---> (PostgreSQL)
        |                                                                                    |
  Générateur                                                                                 +---> [ Qdrant ] (Vector DB)
 de données                                                                                   |       ^
                                                                                              v       |
                                                                                  [ cluster Apache Spark ]
                                                                                  - spark_job.py (Stats)
                                                                                  - predictive_job.py (IA)
                                                                                             |
                                                                                             v
[ Tableau de bord Web ] <--- (API REST Flask) <---------- (PostgreSQL)
Stack Technique
Backend / API : Python, Flask

Message Broker : RabbitMQ

Base de Données : PostgreSQL (Relationnelle), Qdrant (Vectorielle)

Big Data / IA : Apache Spark (PySpark), Spark MLlib

Observabilité : Grafana

Déploiement : Docker & Docker-compose

🚀 Guide de Démarrage Rapide
1. Infrastructure
Lancez les services en arrière-plan :

Bash
docker-compose up -d
2. Interface Web (Flask)
Installez les dépendances et lancez le serveur :

Bash
pip install -r requirements.txt
python app.py
Accès : http://localhost:5000

3. Initialisation
Accédez à l'onglet Configuration via l'interface.

Cliquez sur Créer les tables pour initialiser PostgreSQL.

Configurez le mode réseau et cliquez sur ▶ Démarrer les services de télémétrie.

🧠 Analyse Prédictive & Recherche de Signatures
Prédiction (IA) : Une fois 100+ relevés générés, utilisez l'onglet Analyse Prédictive pour entraîner le modèle Random Forest. Il corrélera automatiquement les pannes avec les conditions d'humidité, poussière et réseau.

Similarité (Qdrant) : Exécutez python qdrant_signatures.py pour vectoriser les pannes historiques. Le système comparera en temps réel les nouveaux flux avec ces signatures (similarité > 98%).

🛣️ Roadmap : Vers la Mise en Production
Audit de Sécurité : Implémentation TLS pour RabbitMQ et sécurisation stricte des accès bases de données.

Adaptateurs MQTT : Remplacement du producteur.py par des connecteurs réels (MQTT) pour interfaçage avec les PLC/SCADA industriels.

Spark Streaming : Transition du traitement "batch" vers Spark Structured Streaming pour une analyse à latence ultra-faible.

Orchestration Cloud/K8s : Déploiement sur cluster Kubernetes pour la haute disponibilité et la scalabilité horizontale.

Monitoring Avancé : Intégration de la stack Prometheus/Grafana pour un suivi proactif de la santé infrastructurelle.

Recettage (UAT) : Tests d'acceptation utilisateur sur site pour valider les seuils d'alerte et minimiser les faux positifs.

📁 Structure des fichiers
docker-compose.yml : Orchestration des conteneurs.

app.py : Serveur Flask & API.

producer.py : Simulation des machines (données + contexte réseau/environnement).

consumer.py : Ingestion des données.

spark_job.py : Job Spark (Stats).

predictive_job.py : Job Spark ML (Maintenance prédictive).

qdrant_signatures.py : Moteur de recherche vectorielle.

SERVICES_SETUP.md : Guide technique de dépannage.