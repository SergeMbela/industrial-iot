# Configuration des Services - Industrial IoT

Ce fichier `docker-compose.yml` configure tous les services nécessaires pour le projet IoT industriel.

## Services inclus

### 1. **RabbitMQ** (Message Broker)
- Port AMQP: `5672`
- Port Management UI: `15672`
- Accès: http://localhost:15672
- Identifiants: `guest` / `guest`

### 2. **PostgreSQL** (Database)
- Port: `5432`
- Base de données: `industrial_iot`
- Utilisateur: `admin`
- Mot de passe: `admin123`

### 3. **Grafana** (Visualization & Dashboards)
- Port: `3000`
- Accès: http://localhost:3000
- Identifiants: `admin` / `admin123`

### 4. **Twilio** (Communication Service)
- Service cloud (pas de conteneur local)
- Configurer les variables d'environnement dans `.env`:
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_PHONE_NUMBER`

## Installation et Utilisation

### Prérequis
- Docker
- Docker Compose

### Démarrage des services

```bash
# Copier le fichier .env.example en .env et adapter les valeurs
cp .env.example .env

# Démarrer tous les services
docker-compose up -d

# Vérifier le statut
docker-compose ps

# Afficher les logs
docker-compose logs -f
```

### Arrêt des services

```bash
# Arrêter tous les services
docker-compose down

# Arrêter et supprimer les volumes
docker-compose down -v
```

## Configuration PostgreSQL

Pour se connecter à PostgreSQL depuis votre application:

```python
import psycopg2

connection = psycopg2.connect(
    host="localhost",
    database="industrial_iot",
    user="admin",
    password="admin123"
)
```

Ou avec SQLAlchemy:

```python
from sqlalchemy import create_engine

engine = create_engine('postgresql://admin:admin123@localhost:5432/industrial_iot')
```

## Configuration RabbitMQ

Pour se connecter à RabbitMQ depuis votre application:

```python
import pika

credentials = pika.PlainCredentials('guest', 'guest')
parameters = pika.ConnectionParameters('localhost', 5672, '/', credentials)
connection = pika.BlockingConnection(parameters)
channel = connection.channel()
```

## Configuration Grafana

1. Accéder à http://localhost:3000
2. Se connecter avec `admin` / `admin123`
3. Ajouter une source de données PostgreSQL:
   - Host: `postgres:5432`
   - Database: `industrial_iot`
   - User: `admin`
   - Password: `admin123`

## Configuration Twilio

Obtenir les credentials depuis https://www.twilio.com/console et les ajouter au fichier `.env`

```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890
```

Utilisation dans votre code Python:

```python
from twilio.rest import Client

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)

message = client.messages.create(
    body="Your message here",
    from_=os.getenv('TWILIO_PHONE_NUMBER'),
    to="+1234567890"
)
```

## Dépannage

**Les services ne démarrent pas:**
```bash
docker-compose logs
```

**Réinitialiser les données:**
```bash
docker-compose down -v
docker-compose up -d
```

**Accès refusé à PostgreSQL:**
- Vérifier les credentials dans `.env`
- S'assurer que le conteneur est bien en cours d'exécution: `docker-compose ps`

## Notes importantes

- Les données sont sauvegardées dans des volumes Docker
- Pour la production, modifier les mots de passe par défaut
- Certains services dépendent d'autres (ex: Grafana attend PostgreSQL)
