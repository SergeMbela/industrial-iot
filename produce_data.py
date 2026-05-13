import pika
import json
import time
import random
from datetime import datetime
from faker import Faker

fake = Faker()

# Configuration RabbitMQ
RABBITMQ_HOST = 'localhost'
QUEUE_NAME = 'sensor_telemetry'

# Configuration des machines minières
MACHINES = [
    {"id": "PMP-101", "name": "Pompe d'Exhaure Nord"},
    {"id": "PMP-102", "name": "Pompe d'Exhaure Sud"},
    {"id": "CRUSH-01", "name": "Concasseur Primaire"},
    {"id": "CONV-04", "name": "Convoyeur de Minerai"},
    {"id": "DRILL-07", "name": "Foreuse Hydraulique"}
]
print("Machines minières configurées :")
for machine in MACHINES:
    print(f" - {machine['id']}: {machine['name']}")