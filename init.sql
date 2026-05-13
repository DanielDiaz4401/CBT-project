-- 1. Extensiones necesarias para UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. ENUM de estado (Sincronizado con models.py)
CREATE TYPE simulation_status AS ENUM (
    'running', 
    'completed', 
    'failed'
    'error'
);

-- 3. TABLA DE ARCHIVOS (Deduplicación)
CREATE TABLE simulation_files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    content BYTEA NOT NULL,
    content_hash VARCHAR(64) NOT NULL UNIQUE, -- SHA-256
    file_size INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. TABLA DE SIMULACIONES (Con UUID y FKs a archivos)
CREATE TABLE simulations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    status simulation_status DEFAULT 'running',
    error_message TEXT,
    
    -- Parámetros técnicos
    l_extra FLOAT,
    c_min INTEGER,
    c_max INTEGER,
    l_max FLOAT,
    threshold FLOAT,
    algorithm_type VARCHAR(50) DEFAULT 'guangorithm',
    
    -- Llaves foráneas a la tabla de archivos
    nodes_file_id INTEGER REFERENCES simulation_files(id) ON DELETE SET NULL,
    edges_file_id INTEGER REFERENCES simulation_files(id) ON DELETE SET NULL,
    paths_file_id INTEGER REFERENCES simulation_files(id) ON DELETE SET NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. TABLAS DE RESULTADOS (Todas con simulation_id UUID)

CREATE TABLE components_to_methods (
    id VARCHAR PRIMARY KEY,
    simulation_id UUID REFERENCES simulations(id) ON DELETE CASCADE,
    component_id VARCHAR(255),
    methods_id TEXT[] -- Array de strings
);

CREATE TABLE simulation_stages (
    id SERIAL PRIMARY KEY,
    simulation_id UUID REFERENCES simulations(id) ON DELETE CASCADE,
    stage_number INTEGER NOT NULL,
    migrated_components TEXT[],
    worst_critical_time NUMERIC(10, 4)
);

CREATE TABLE critical_paths (
    id SERIAL PRIMARY KEY,
    simulation_id UUID REFERENCES simulations(id) ON DELETE CASCADE,
    path_number INTEGER NOT NULL,
    affected_stages INTEGER[] DEFAULT '{}'
);

CREATE TABLE path_nodes (
    id SERIAL PRIMARY KEY,
    path_id INTEGER REFERENCES critical_paths(id) ON DELETE CASCADE,
    component_name VARCHAR(255) NOT NULL
);

CREATE TABLE path_edges (
    id SERIAL PRIMARY KEY,
    path_id INTEGER REFERENCES critical_paths(id) ON DELETE CASCADE,
    invoker VARCHAR(255) NOT NULL,
    invoked VARCHAR(255) NOT NULL,
    base_latency NUMERIC(10, 4)
);

CREATE TABLE critical_path_stages (
    id SERIAL PRIMARY KEY,
    path_id INTEGER REFERENCES critical_paths(id) ON DELETE CASCADE,
    stage_number INTEGER NOT NULL,
    critical_time NUMERIC(10, 4),
    migrated_components TEXT[]
);

CREATE TABLE blocked_components (
    id SERIAL PRIMARY KEY,
    simulation_id UUID REFERENCES simulations(id) ON DELETE CASCADE,
    component_name VARCHAR(255) NOT NULL,
    stage_number INTEGER
);