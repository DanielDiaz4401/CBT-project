import enum
import uuid
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, LargeBinary
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, UUID as PG_UUID

Base = declarative_base()

# --- ENUMS ---
class SimulationStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"

class SimulationFileType(str, enum.Enum):
    nodes = "nodes"
    edges = "edges"
    paths = "paths"

class AlgorithmType(str, enum.Enum):
    GUANGORITHM = "guangorithm"
    ROBERGORITHM_V2 = "robergorithm_v2"
    ROBERGORITHM_V3 = "robergorithm_v3"

# --- TABLA DE ARCHIVOS (Para Deduplicación) ---
class SimulationFile(Base):
    __tablename__ = "simulation_files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)        
    content = Column(LargeBinary, nullable=False) 
    content_hash = Column(String, nullable=False, unique=True) 
    file_size = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# --- TABLA PRINCIPAL DE SIMULACIONES ---
class Simulation(Base):
    __tablename__ = "simulations"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    status = Column(Enum(SimulationStatus, name="simulation_status", values_callable=lambda obj: [e.value for e in obj]), default=SimulationStatus.RUNNING)
    error_message = Column(String, nullable=True)
    
    # Parámetros de la simulación
    l_extra = Column(Float)
    c_min = Column(Integer)
    c_max = Column(Integer)
    l_max = Column(Float)
    threshold = Column(Float)

    algorithm_type = Column(String, default="guangorithm") # <-- Nueva columna
    
    # IDs de archivos (Relacionados con SimulationFile)
    nodes_file_id = Column(Integer, ForeignKey("simulation_files.id"), nullable=True)
    edges_file_id = Column(Integer, ForeignKey("simulation_files.id"), nullable=True)
    paths_file_id = Column(Integer, ForeignKey("simulation_files.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relaciones de Archivos
    nodes_file = relationship("SimulationFile", foreign_keys=[nodes_file_id])
    edges_file = relationship("SimulationFile", foreign_keys=[edges_file_id])
    paths_file = relationship("SimulationFile", foreign_keys=[paths_file_id])
    
    # Relaciones de Resultados (Con borrado en cascada)
    stages = relationship("SimulationStage", back_populates="simulation", cascade="all, delete-orphan", lazy="select")
    critical_paths = relationship("CriticalPath", back_populates="simulation", cascade="all, delete-orphan", lazy="select")
    component_mappings = relationship("ComponentToMethod", back_populates="simulation", cascade="all, delete-orphan")

    blocked_components = relationship("BlockedComponents", back_populates="simulation", cascade="all, delete-orphan", lazy="select")

# --- TABLAS DE RESULTADOS Y METADATOS ---

class ComponentToMethod(Base):
    __tablename__ = "components_to_methods"
    id = Column(String, primary_key=True) 
    simulation_id = Column(PG_UUID(as_uuid=True), ForeignKey("simulations.id"))
    component_id = Column(String)
    methods_id = Column(PG_ARRAY(String))
    
    simulation = relationship("Simulation", back_populates="component_mappings")

class SimulationStage(Base):
    __tablename__ = "simulation_stages"
    id = Column(Integer, primary_key=True)
    simulation_id = Column(PG_UUID(as_uuid=True), ForeignKey("simulations.id"))
    stage_number = Column(Integer)
    migrated_components = Column(PG_ARRAY(String))
    worst_critical_time = Column(Float)
    
    simulation = relationship("Simulation", back_populates="stages")

# --- ESTRUCTURA DE RUTAS CRÍTICAS ---

class CriticalPath(Base):
    __tablename__ = "critical_paths"
    id = Column(Integer, primary_key=True)
    simulation_id = Column(PG_UUID(as_uuid=True), ForeignKey("simulations.id"))
    path_number = Column(Integer)
    affected_stages = Column(PG_ARRAY(Integer), default=[])
    

    simulation = relationship("Simulation", back_populates="critical_paths")
    nodes = relationship("PathNode", back_populates="path", cascade="all, delete-orphan", lazy="select")
    edges = relationship("PathEdge", back_populates="path", cascade="all, delete-orphan", lazy="select")
    stage_details = relationship("CriticalPathStage", back_populates="path", cascade="all, delete-orphan", lazy="select")

class PathNode(Base):
    __tablename__ = "path_nodes"
    id = Column(Integer, primary_key=True)
    path_id = Column(Integer, ForeignKey("critical_paths.id"))
    component_name = Column(String)
    
    path = relationship("CriticalPath", back_populates="nodes")

class PathEdge(Base):
    __tablename__ = "path_edges"
    id = Column(Integer, primary_key=True)
    path_id = Column(Integer, ForeignKey("critical_paths.id"))
    invoker = Column(String)
    invoked = Column(String)
    base_latency = Column(Float)
    
    path = relationship("CriticalPath", back_populates="edges")

class CriticalPathStage(Base):
    __tablename__ = "critical_path_stages"
    id = Column(Integer, primary_key=True)
    path_id = Column(Integer, ForeignKey("critical_paths.id"))
    stage_number = Column(Integer)
    critical_time = Column(Float)
    migrated_components = Column(PG_ARRAY(String))
    
    path = relationship("CriticalPath", back_populates="stage_details")

class BlockedComponents(Base):
    __tablename__ = "blocked_components"
    id = Column(Integer, primary_key=True)
    simulation_id = Column(PG_UUID(as_uuid=True), ForeignKey("simulations.id", ondelete="CASCADE"))
    component_name = Column(String)
    stage_number = Column(Integer)
    
    simulation = relationship("Simulation", back_populates="blocked_components")