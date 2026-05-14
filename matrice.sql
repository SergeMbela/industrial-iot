-- ==========================================================
-- 0. NETTOYAGE (POUR MISE À JOUR DU SCHÉMA)
-- ==========================================================
DROP TABLE IF EXISTS sensor_data CASCADE;
DROP TABLE IF EXISTS machine_configurations CASCADE;
DROP TABLE IF EXISTS maintenance_plan CASCADE;
DROP TABLE IF EXISTS maintenance_log CASCADE;
DROP TABLE IF EXISTS ventilation_log CASCADE;
DROP TABLE IF EXISTS machines CASCADE;
DROP TABLE IF EXISTS ventilation_fans CASCADE;
DROP TABLE IF EXISTS localisations CASCADE;
DROP TABLE IF EXISTS machine_types CASCADE;
DROP TABLE IF EXISTS brands CASCADE;

-- ==========================================================
-- 1. TABLES DE RÉFÉRENCE (LES BASES)
-- ==========================================================

-- Table des marques/constructeurs
CREATE TABLE IF NOT EXISTS brands (
    brand_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    country VARCHAR(50),
    support_contact VARCHAR(100)
);

-- Table des types de machines (Catégories)
CREATE TABLE IF NOT EXISTS machine_types (
    type_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    icon_name VARCHAR(50) -- Pour l'UI
);

-- Insertion des types de base
INSERT INTO machine_types (name, description, icon_name) VALUES 
('Broyeur', 'Concassage et réduction de minerai', 'shredder'),
('Foreuse', 'Forage vertical et horizontal', 'drill'),
('Pompe', 'Exhaure et pompage hydraulique', 'pump'),
('Excavatrice', 'Extraction et chargement', 'excavator'),
('Camion', 'Transport de charges lourdes', 'truck')
ON CONFLICT (name) DO NOTHING;

-- Table des localisations (Zones de travail)
CREATE TABLE IF NOT EXISTS localisations (
    localisation_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    type VARCHAR(20) CHECK (type IN ('Surface', 'Souterrain')),
    elevation_base INTEGER, -- Altitude/Profondeur de référence pour cette zone
    description TEXT
);

-- Insertion de quelques localisations par défaut
INSERT INTO localisations (name, type, elevation_base, description) VALUES 
('Surface - Zone Nord', 'Surface', 1250, 'Zone d''extraction principale à ciel ouvert'),
('Surface - Zone Sud', 'Surface', 1280, 'Ateliers et maintenance'),
('Niveau -100', 'Souterrain', -100, 'Premier niveau de galeries'),
('Niveau -450', 'Souterrain', -450, 'Zone de forage profond'),
('Niveau -800', 'Souterrain', -800, 'Fond de mine et pompage principal')
ON CONFLICT (name) DO NOTHING;

-- Table des configurations/seuils par Type + Marque
CREATE TABLE IF NOT EXISTS machine_configurations (
    config_id SERIAL PRIMARY KEY,
    type_id INTEGER REFERENCES machine_types(type_id),
    brand_id INTEGER REFERENCES brands(brand_id),
    
    -- 1. Performance Énergétique
    fuel_consumption_max_lh DECIMAL(10, 2),
    amperage_max_a DECIMAL(10, 2),
    idle_time_max_pct DECIMAL(5, 2) DEFAULT 15.0,
    
    -- 2. Santé Mécanique
    temp_threshold_max DECIMAL(10, 2) DEFAULT 85.0,
    vibration_threshold_mm_s DECIMAL(10, 2) DEFAULT 5.0,
    vibration_acceleration_g_max DECIMAL(10, 2) DEFAULT 2.0,
    cycle_time_nominal_s DECIMAL(10, 2),
    
    -- 3. Fluides et Lubrification (Seuils d'alerte)
    oil_viscosity_min_cst DECIMAL(10, 2),
    oil_viscosity_max_cst DECIMAL(10, 2),
    silicon_ppm_max DECIMAL(10, 2) DEFAULT 20.0,
    water_ppm_max DECIMAL(10, 2) DEFAULT 500.0,
    tbn_min DECIMAL(10, 2) DEFAULT 6.0,
    
    -- 4. Thermique et Pression
    oil_pressure_min_bar DECIMAL(10, 2) DEFAULT 3.5,
    pressure_nominal_bar DECIMAL(10, 2) DEFAULT 100.0,
    exhaust_temp_max_c DECIMAL(10, 2) DEFAULT 650.0,
    turbo_pressure_max_bar DECIMAL(10, 2) DEFAULT 2.5,
    filter_diff_pressure_max_bar DECIMAL(10, 2) DEFAULT 1.5,
    
    avg_consumption_kwh DECIMAL(10, 2) DEFAULT 20.0,
    UNIQUE(type_id, brand_id)
);

-- Insertion de quelques configurations de base
INSERT INTO machine_configurations (type_id, brand_id, temp_threshold_max, pressure_nominal_bar, avg_consumption_kwh)
SELECT t.type_id, b.brand_id, 90, 150, 35
FROM machine_types t, brands b
WHERE t.name = 'Broyeur' AND b.name = 'Metso Outotec'
ON CONFLICT DO NOTHING;

INSERT INTO machine_configurations (type_id, brand_id, temp_threshold_max, pressure_nominal_bar, avg_consumption_kwh)
SELECT t.type_id, b.brand_id, 95, 30, 45
FROM machine_types t, brands b
WHERE t.name = 'Camion' AND b.name = 'Caterpillar'
ON CONFLICT DO NOTHING;

-- Table des zones de ventilation (Infrastructures fixes)
CREATE TABLE IF NOT EXISTS ventilation_fans (
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
CREATE TABLE IF NOT EXISTS machines (
    machine_id VARCHAR(50) PRIMARY KEY,
    type_id INTEGER REFERENCES machine_types(type_id), -- Référence au type
    brand_id INTEGER REFERENCES brands(brand_id),
    localisation_id INTEGER REFERENCES localisations(localisation_id), -- Changé de localisation_type
    niveau_elevation_machine INTEGER, -- Altitude ou profondeur spécifique (peut différer de la base zone)
    date_achat DATE,
    heures_service_initiales INTEGER DEFAULT 0,
    heures_fonctionnement_totales DECIMAL(12, 2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'Actif'
);

-- Planning de maintenance constructeur
CREATE TABLE IF NOT EXISTS maintenance_plan (
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

-- Données des capteurs machines (Télémesure avancée)
CREATE TABLE IF NOT EXISTS sensor_data (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    machine_id VARCHAR(50) REFERENCES machines(machine_id),
    
    -- 1. Performance Énergétique
    fuel_consumption_lh DECIMAL(10, 2),
    amperage DECIMAL(10, 4),
    idle_time_pct DECIMAL(5, 2),
    
    -- 2. Santé Mécanique
    vibration_rms_mm_s DECIMAL(10, 4),
    vibration_accel_g DECIMAL(10, 4),
    hours_hmr DECIMAL(12, 2),
    cycle_speed_s DECIMAL(10, 2),
    
    -- 3. Fluides et Lubrification
    oil_viscosity_cst DECIMAL(10, 2),
    silicon_ppm DECIMAL(10, 2),
    wear_metals_ppm JSONB, -- Pour stocker Fe, Cu, Cr...
    water_ppm DECIMAL(10, 2),
    tbn_value DECIMAL(10, 2),
    
    -- 4. Thermique et Pression
    oil_temp_c DECIMAL(10, 2),
    oil_pressure_bar DECIMAL(10, 2),
    exhaust_temp_c DECIMAL(10, 2),
    turbo_boost_bar DECIMAL(10, 2),
    filter_diff_pressure_bar DECIMAL(10, 2),
    
    ambient_temp DECIMAL(5, 2),
    humidity_percent DECIMAL(5, 2)
);

-- Données du système de ventilation
CREATE TABLE IF NOT EXISTS ventilation_log (
    log_id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    fan_id VARCHAR(50) REFERENCES ventilation_fans(fan_id),
    vitesse_rotation_rpm INTEGER,
    amp_consommee DECIMAL(10, 2),
    debit_air_actuel DECIMAL(10, 2)
);

-- Historique réel des interventions de maintenance
CREATE TABLE IF NOT EXISTS maintenance_log (
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
CREATE INDEX IF NOT EXISTS idx_sensor_time_machine ON sensor_data (timestamp DESC, machine_id);
CREATE INDEX IF NOT EXISTS idx_ventilation_time ON ventilation_log (timestamp DESC, fan_id);
-- ==========================================================
-- 5. SCRIPTS UTILITAIRES
-- ==========================================================

-- Pour ajouter 10 camions Caterpillar au Niveau -200
DO $$
DECLARE
    brand_id_val INT;
    type_id_val INT;
    loc_id_val INT;
BEGIN
    INSERT INTO brands (name, country) VALUES ('Caterpillar', 'USA') 
    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING brand_id INTO brand_id_val;

    SELECT type_id INTO type_id_val FROM machine_types WHERE name = 'Camion';

    INSERT INTO localisations (name, type, elevation_base) 
    VALUES ('Niveau -200', 'Souterrain', -200) 
    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING localisation_id INTO loc_id_val;

    FOR i IN 1..10 LOOP
        INSERT INTO machines (machine_id, type_id, brand_id, localisation_id, niveau_elevation_machine, date_achat)
        VALUES ('CAT-TRK-' || LPAD(i::text, 3, '0'), type_id_val, brand_id_val, loc_id_val, -200, '2000-06-01')
        ON CONFLICT (machine_id) DO NOTHING;
    END LOOP;
END $$;

-- Pour ajouter 10 excavatrices Komatsu
DO $$
DECLARE
    brand_id_val INT;
    type_id_val INT;
    loc_id_val INT;
BEGIN
    INSERT INTO brands (name, country) VALUES ('Komatsu', 'Japon') 
    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING brand_id INTO brand_id_val;

    SELECT type_id INTO type_id_val FROM machine_types WHERE name = 'Excavatrice';
    SELECT localisation_id INTO loc_id_val FROM localisations WHERE name = 'Surface - Zone Nord';

    FOR i IN 1..10 LOOP
        INSERT INTO machines (machine_id, type_id, brand_id, localisation_id, niveau_elevation_machine, status)
        VALUES ('KOM-EXC-' || LPAD(i::text, 3, '0'), type_id_val, brand_id_val, loc_id_val, 1250, 'Actif')
        ON CONFLICT (machine_id) DO NOTHING;
    END LOOP;
END $$;

-- Pour ajouter 5 pompes par marque existante
DO $$
DECLARE
    brand_row RECORD;
    type_id_val INT;
    loc_id_val INT;
BEGIN
    SELECT type_id INTO type_id_val FROM machine_types WHERE name = 'Pompe';
    SELECT localisation_id INTO loc_id_val FROM localisations WHERE name = 'Niveau -800';

    FOR brand_row IN SELECT brand_id, name FROM brands LOOP
        FOR i IN 1..5 LOOP
            INSERT INTO machines (machine_id, type_id, brand_id, localisation_id, niveau_elevation_machine, date_achat, status)
            VALUES (
                UPPER(LEFT(brand_row.name, 3)) || '-PMP-' || LPAD(i::text, 3, '0'), 
                type_id_val, 
                brand_row.brand_id, 
                loc_id_val, 
                -800, 
                '2022-06-01',
                'Actif'
            )
            ON CONFLICT (machine_id) DO NOTHING;
        END LOOP;
    END LOOP;
END $$;

-- Ajouter d'autres marques de référence
INSERT INTO brands (name, country) VALUES 
('Siemens', 'Allemagne'),
('Hitachi', 'Japon'),
('Volvo', 'Suède'),
('Liebherr', 'Suisse'),
('Sandvik', 'Suède')
ON CONFLICT (name) DO NOTHING;

-- Pour ajouter 5 pompes par marque existante (sauf Caterpillar et Komatsu)
DO $$
DECLARE
    brand_row RECORD;
    type_id_val INT;
    loc_id_val INT;
BEGIN
    SELECT type_id INTO type_id_val FROM machine_types WHERE name = 'Pompe';
    SELECT localisation_id INTO loc_id_val FROM localisations WHERE name = 'Niveau -800';

    FOR brand_row IN SELECT brand_id, name FROM brands WHERE name NOT IN ('Caterpillar', 'Komatsu') LOOP
        FOR i IN 1..5 LOOP
            INSERT INTO machines (machine_id, type_id, brand_id, localisation_id, niveau_elevation_machine, date_achat, status)
            VALUES (
                UPPER(LEFT(brand_row.name, 3)) || '-PMP-' || LPAD(i::text, 3, '0'), 
                type_id_val, 
                brand_row.brand_id, 
                loc_id_val, 
                -800, 
                '2022-06-01',
                'Actif'
            )
            ON CONFLICT (machine_id) DO NOTHING;
        END LOOP;
    END LOOP;
END $$;

-- Ajouter 10 foreuses Sandvik au Niveau -450
DO $$
DECLARE
    brand_id_val INT;
    type_id_val INT;
    loc_id_val INT;
BEGIN
    SELECT brand_id INTO brand_id_val FROM brands WHERE name = 'Sandvik';
    SELECT type_id INTO type_id_val FROM machine_types WHERE name = 'Foreuse';
    SELECT localisation_id INTO loc_id_val FROM localisations WHERE name = 'Niveau -450';

    FOR i IN 1..10 LOOP
        INSERT INTO machines (machine_id, type_id, brand_id, localisation_id, niveau_elevation_machine, date_achat, status)
        VALUES (
            'SAN-DRL-' || LPAD(i::text, 3, '0'), 
            type_id_val, 
            brand_id_val, 
            loc_id_val, 
            -450, 
            '2000-06-01',
            'Actif'
        )
        ON CONFLICT (machine_id) DO NOTHING;
    END LOOP;
END $$;

-- Ajouter 5 broyeurs Metso à la Surface
DO $$
DECLARE
    brand_id_val INT;
    type_id_val INT;
    loc_id_val INT;
BEGIN
    INSERT INTO brands (name, country) VALUES ('Metso Outotec', 'Finlande') 
    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING brand_id INTO brand_id_val;

    SELECT type_id INTO type_id_val FROM machine_types WHERE name = 'Broyeur';
    SELECT localisation_id INTO loc_id_val FROM localisations WHERE name = 'Surface - Zone Sud';

    FOR i IN 1..5 LOOP
        INSERT INTO machines (machine_id, type_id, brand_id, localisation_id, niveau_elevation_machine, date_achat, status)
        VALUES (
            'MET-BRY-' || LPAD(i::text, 3, '0'), 
            type_id_val, 
            brand_id_val, 
            loc_id_val, 
            1280, 
            '2018-03-15',
            'Actif'
        )
        ON CONFLICT (machine_id) DO NOTHING;
    END LOOP;
END $$;

-- Générer des configurations par défaut pour toutes les combinaisons Type/Marque existantes
DO $$
DECLARE
    row RECORD;
    t_name TEXT;
BEGIN
    FOR row IN SELECT DISTINCT type_id, brand_id FROM machines LOOP
        SELECT name INTO t_name FROM machine_types WHERE type_id = row.type_id;
        
        IF NOT EXISTS (SELECT 1 FROM machine_configurations WHERE type_id = row.type_id AND brand_id = row.brand_id) THEN
            INSERT INTO machine_configurations (type_id, brand_id, temp_threshold_max, pressure_nominal_bar, avg_consumption_kwh)
            VALUES (
                row.type_id, 
                row.brand_id, 
                CASE 
                    WHEN t_name = 'Broyeur' THEN 90
                    WHEN t_name = 'Foreuse' THEN 88
                    WHEN t_name = 'Pompe' THEN 75
                    WHEN t_name = 'Excavatrice' THEN 92
                    WHEN t_name = 'Camion' THEN 95
                    ELSE 85
                END,
                CASE 
                    WHEN t_name = 'Pompe' THEN 12
                    WHEN t_name = 'Foreuse' THEN 210
                    WHEN t_name = 'Broyeur' THEN 160
                    WHEN t_name = 'Excavatrice' THEN 320
                    WHEN t_name = 'Camion' THEN 35
                    ELSE 100
                END,
                CASE 
                    WHEN t_name = 'Camion' THEN 48
                    WHEN t_name = 'Broyeur' THEN 38
                    WHEN t_name = 'Foreuse' THEN 15
                    WHEN t_name = 'Excavatrice' THEN 28
                    ELSE 22
                END
            );
        END IF;
    END LOOP;
END $$;

-- Générer une première série de données de capteurs pour chaque machine
DO $$
DECLARE
    m_row RECORD;
    t_name TEXT;
BEGIN
    FOR m_row IN SELECT machine_id, type_id FROM machines LOOP
        SELECT name INTO t_name FROM machine_types WHERE type_id = m_row.type_id;
        
        INSERT INTO sensor_data (
            machine_id,
            fuel_consumption_lh,
            amperage,
            idle_time_pct,
            vibration_rms_mm_s,
            vibration_accel_g,
            hours_hmr,
            cycle_speed_s,
            oil_viscosity_cst,
            silicon_ppm,
            water_ppm,
            tbn_value,
            oil_temp_c,
            oil_pressure_bar,
            exhaust_temp_c,
            turbo_boost_bar,
            filter_diff_pressure_bar,
            ambient_temp,
            humidity_percent
        )
        VALUES (
            m_row.machine_id,
            -- Performance Énergétique
            CASE WHEN t_name IN ('Camion', 'Excavatrice') THEN (random() * 45 + 5)::DECIMAL(10,2) ELSE 0 END,
            CASE WHEN t_name IN ('Broyeur', 'Pompe', 'Foreuse') THEN (random() * 180 + 20)::DECIMAL(10,4) ELSE 0 END,
            (random() * 25)::DECIMAL(5,2),
            
            -- Santé Mécanique
            (random() * 8)::DECIMAL(10,4),
            (random() * 2.5)::DECIMAL(10,4),
            (random() * 5000 + 500)::DECIMAL(12,2),
            CASE WHEN t_name = 'Excavatrice' THEN (random() * 15 + 20)::DECIMAL(10,2) ELSE 0 END,
            
            -- Fluides
            (random() * 30 + 80)::DECIMAL(10,2),
            (random() * 25)::DECIMAL(10,2),
            (random() * 600)::DECIMAL(10,2),
            (random() * 5 + 6)::DECIMAL(10,2),
            
            -- Thermique / Pression
            (random() * 50 + 40)::DECIMAL(10,2),
            (random() * 4 + 2)::DECIMAL(10,2),
            CASE WHEN t_name IN ('Camion', 'Excavatrice') THEN (random() * 300 + 350)::DECIMAL(10,2) ELSE 0 END,
            CASE WHEN t_name = 'Camion' THEN (random() * 2.0 + 0.5)::DECIMAL(10,2) ELSE 0 END,
            (random() * 1.8)::DECIMAL(10,2),
            
            (20 + random() * 15)::DECIMAL(5,2),
            (30 + random() * 40)::DECIMAL(5,2)
        );
    END LOOP;
END $$;
