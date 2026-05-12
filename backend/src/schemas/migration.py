from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

# ==========================================
# 1. ENUMERACIONES
# ==========================================

class SimulationStatus(str, Enum):
    """Estados posibles por los que pasa una simulación en su ciclo de vida."""
    PENDING = "pending"
    RUNNING = "running"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class SimulationFileType(str, Enum):
    """Tipos de archivos CSV soportados por el sistema."""
    NODES = "nodes"
    EDGES = "edges"
    PATHS = "paths"

# ==========================================
# 2. MODELOS BASE Y DE CONFIGURACIÓN
# ==========================================

class BlockedComponents(BaseModel):
    """Restricción temporal para un componente específico."""
    component_name: str = Field(..., description="ID del componente que tiene restringida su migración", examples=["C001234"])
    stage_number: int = Field(..., description="Número de etapa hasta la cual el componente no puede ser migrado", examples=[10])
    
    model_config = ConfigDict(from_attributes=True)

class SimulationBase(BaseModel):
    """Parámetros técnicos base de una simulación."""
    name: str = Field(..., description="Nombre único asignado a este escenario de simulación", examples=["Migration_Batch_A_Q3"])
    l_extra: float = Field(..., description="Latencia adicional (ms) penalizada en aristas híbridas (on-prem a cloud)", examples=[30.0])
    c_min: int = Field(..., description="Cantidad mínima de componentes que el algoritmo intentará migrar por etapa", examples=[1])
    c_max: int = Field(..., description="Capacidad máxima de migración de componentes por etapa", examples=[5])
    l_max: float = Field(..., description="Límite superior de latencia total permitida para considerar válida una ruta", examples=[150.0])
    threshold: float = Field(..., description="Umbral de tolerancia (%) para el cálculo heurístico del algoritmo", examples=[15.0])

class SimulationCreate(SimulationBase):
    """Esquema interno usado para crear registros en la Base de Datos."""
    pass

class SimulationSummary(SimulationBase):
    """Esquema de respuesta principal con el resumen de la simulación."""
    id: UUID = Field(..., description="Identificador único global (UUID) generado por el sistema")
    status: SimulationStatus = Field(..., description="Estado de ejecución del proceso")
    error_message: Optional[str] = Field(None, description="Información detallada en caso de fallo")
    date: datetime = Field(..., alias="created_at", description="Timestamp de creación")
    blocked_components: List[BlockedComponents] = Field(default=[], description="Restricciones aplicadas")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Scenario_High_Capacity",
                "status": "completed",
                "l_extra": 30.0,
                "c_min": 1,
                "c_max": 10,
                "l_max": 200.0,
                "threshold": 5.0,
                "created_at": "2026-05-12T17:42:00Z",
                "blocked_components": [{"component_name": "Core_DB_Proxy", "stage_number": 5}]
            }
        }
    )

# ==========================================
# 3. MODELOS DE RESULTADOS Y ANÁLISIS
# ==========================================

class StageSummary(BaseModel):
    """Resumen de impacto por cada etapa individual de la migración."""
    stage_number: int = Field(..., description="Índice secuencial de la etapa de migración", examples=[1])
    migrated_components: List[str] = Field(..., description="IDs de los componentes migrados al cloud en esta iteración")
    worst_critical_time: float = Field(..., description="Latencia máxima registrada entre todas las rutas tras esta etapa", examples=[132.45])

    model_config = ConfigDict(from_attributes=True)

class CriticalPathHito(BaseModel):
    """Identificación de rutas críticas afectadas durante el proceso."""
    path_number: int = Field(..., description="ID interno de la ruta crítica", examples=[14])
    affected_stages: List[int] = Field(..., description="Lista de etapas (stages) donde esta ruta superó los umbrales de latencia", examples=[[2, 3, 4, 10]])

    model_config = ConfigDict(from_attributes=True)

class EdgeDetail(BaseModel):
    """Detalle de una conexión individual entre dos componentes."""
    invoker: str = Field(..., description="ID del componente que inicia la petición")
    invoked: str = Field(..., description="ID del componente que recibe la petición")
    base_latency: float = Field(..., description="Latencia base original de la conexión en milisegundos")

    model_config = ConfigDict(from_attributes=True)

class CriticalPathStepUpdate(BaseModel):
    """Información dinámica de una ruta en una etapa específica para visualización en grafos."""
    stage_number: int = Field(..., description="Etapa analizada")
    newly_migrated_nodes: List[str] = Field(..., description="Nodos de esta ruta específica que migraron en esta etapa")
    worst_path_edges: List[EdgeDetail] = Field(default=[], description="Aristas que conforman el peor subcamino en este instante temporal")
    extra_latency_edges: List[EdgeDetail] = Field(default=[], description="Aristas que están sufriendo penalización l_extra en este instante (híbridas)")

    model_config = ConfigDict(from_attributes=True)