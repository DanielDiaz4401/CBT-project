from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Tuple
from datetime import datetime
from enum import Enum
from uuid import UUID

# --- 1. ENUMS ---
class SimulationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class SimulationFileType(str, Enum):
    nodes = "nodes"
    edges = "edges"
    paths = "paths"

# --- 2. SCHEMAS DE ENTRADA (Requests) ---
class SimulationCreate(BaseModel):
    name: str
    l_extra: float
    c_min: int
    c_max: int
    l_max: float
    threshold: float

# --- 3. SCHEMAS DE RESUMEN (Para /simulations/ y /calculate) ---
class SimulationSummary(BaseModel):
    """El 'punto intermedio' que acordamos para listas y creación"""
    id: UUID
    name: str
    status: SimulationStatus
    error_message: Optional[str] = None
    date: datetime = Field(alias="created_at") # Mapeamos created_at de la DB a 'date' para el front

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

# --- 4. SCHEMAS DE RESULTADOS (Listados rápidos) ---

class StageSummary(BaseModel):
    """Para /get_stages/ - Evolución temporal rápida"""
    migrated_components: List[str]
    worst_critical_time: float
    
    model_config = ConfigDict(from_attributes=True)

class CriticalPathHito(BaseModel):
    """Para /get_critical_paths/ - La 'Tabla de Contenidos'"""
    path_number: int
    affected_stages: List[int]
    
    model_config = ConfigDict(from_attributes=True)

# --- 5. SCHEMAS DE DETALLE (El Visor de Grafo) ---

class CriticalPathSkeleton(BaseModel):
    """
    Paso A: El esqueleto inicial del camino crítico seleccionado.
    Usa diccionarios para búsqueda O(1) en el frontend.
    """
    nodes_mapping: Dict[str, str]  # {"node_001": "Component.method"}
    edge_latencies: Dict[str, float] # {"node_01|node_02": 15.4}
    initial_cloud_nodes: List[str]
    first_stage_worst_path_edges: List[Tuple[str, str]]
    extra_latency_affected_edges: List[Tuple[str, str]]

    model_config = ConfigDict(from_attributes=True)

class CriticalPathStepUpdate(BaseModel):
    """
    Paso B: Actualización de estado al cambiar de etapa.
    """
    stage_number: int
    newly_migrated_nodes: List[str]
    worst_path_edges: List[Tuple[str, str]]
    extra_latency_edges: List[Tuple[str, str]]

    model_config = ConfigDict(from_attributes=True)

# --- 6. ARCHIVOS ---
class SimulationFileSchema(BaseModel):
    id: int
    filename: str
    file_size: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)