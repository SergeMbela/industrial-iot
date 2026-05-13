-- ==========================================================
-- 1. TABLES DE RÉFÉRENCE (LES BASES)
-- ==========================================================

-- Table des marques/constructeurs
CREATE TABLE brands (
    brand_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    country VARCHAR(50),
    support_contact VARCHAR(100)
);

-- Table des zones de ventilation (Infrastructures fixes)
CREATE TABLE ventilation_fans (
    fan_id VARCHAR(50) PRIMARY KEY,
    zone_name VARCHAR(100), 
    niveau_profondeur INTEGER, -- Profondeur fixe de l'installation
    debit_air_max DECIMAL(10, 2), -- m³/s
    puissance_nominale_kw DECIMAL(10, 2),
    status VARCHAR(20) DEFAULT 'Running'
);

-- ==========================================================
-- 2. TABLES DES ÉQUIPEMENTS (MACHINES)
-- ==========================================================

-- Table principale des machines
CREATE TABLE machines (
    machine_id VARCHAR(50) PRIMARY KEY,
    type_machine VARCHAR(100), -- Broyeur, Foreuse, Pompe
    brand_id INTEGER REFERENCES brands(brand_id),
    localisation_type VARCHAR(20) CHECK (localisation_type IN ('Surface', 'Souterrain')),
    niveau_elevation_base INTEGER, -- Altitude ou profondeur standard
    date_achat DATE,
    heures_service_initiales INTEGER DEFAULT 0,
    heures_fonctionnement_totales DECIMAL(12, 2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'Actif'
);

-- Planning de maintenance constructeur
CREATE TABLE maintenance_plan (
    plan_id SERIAL PRIMARY KEY,
    machine_id VARCHAR(50) REFERENCES machines(machine_id),
    intervalle_jours INTEGER,
    intervalle_heures INTEGER,
    description_tache TEXT,
    est_critique BOOLEAN DEFAULT FALSE
);

-- ==========================================================
-- 3. TABLES DE TÉLÉMÉTRIE (DONNÉES MASSIVES)
-- ==========================================================

-- Données des capteurs machines
CREATE TABLE sensor_data (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    machine_id VARCHAR(50) REFERENCES machines(machine_id),
    amperage DECIMAL(10, 4),
    voltage DECIMAL(10, 4),
    vibration_level DECIMAL(10, 4),
    ambient_temp DECIMAL(5, 2), -- Température environnementale
    humidity_percent DECIMAL(5, 2),
    profondeur_actuelle INTEGER -- Pour les machines mobiles
);

-- Données du système de ventilation
CREATE TABLE ventilation_log (
    log_id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    fan_id VARCHAR(50) REFERENCES ventilation_fans(fan_id),
    vitesse_rotation_rpm INTEGER,
    amp_consommee DECIMAL(10, 2),
    debit_air_actuel DECIMAL(10, 2)
);

-- Historique réel des interventions de maintenance
CREATE TABLE maintenance_log (
    log_id SERIAL PRIMARY KEY,
    machine_id VARCHAR(50) REFERENCES machines(machine_id),
    date_intervention DATE NOT NULL,
    technicien VARCHAR(100),
    cout_pieces DECIMAL(10, 2),
    observations TEXT
);

-- ==========================================================
-- 4. OPTIMISATION (INDEXATION)
-- ==========================================================

-- Index pour accélérer les graphiques Grafana sur le temps et les machines
CREATE INDEX idx_sensor_time_machine ON sensor_data (timestamp DESC, machine_id);
CREATE INDEX idx_ventilation_time ON ventilation_log (timestamp DESC, fan_id);