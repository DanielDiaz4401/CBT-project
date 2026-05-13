import os
import logging
import hashlib
from sqlalchemy.orm import Session
from uuid import UUID
from . import models
from app.schemas import migration as schemas

logger = logging.getLogger(__name__)

# --- 1. GESTIÓN DE ARCHIVOS ---

def get_or_create_file(db: Session, filename: str, content: bytes) -> models.SimulationFile:
    content_hash = hashlib.sha256(content).hexdigest()
    db_file = db.query(models.SimulationFile).filter(models.SimulationFile.content_hash == content_hash).first()
    
    if db_file:
        return db_file
    
    db_file = models.SimulationFile(
        filename=filename,
        content=content, # <-- Guardamos los bytes directamente en Postgres
        content_hash=content_hash,
        file_size=len(content)
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    return db_file

def get_file_by_type(db: Session, sim_id: UUID, file_type: str):
    sim = get_simulation(db, sim_id)
    if not sim: return None
    file_attr = f"{file_type}_file"
    return getattr(sim, file_attr, None)

# --- 2. GESTIÓN DE SIMULACIONES ---

def get_simulations(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Simulation).offset(skip).limit(limit).all()

def create_simulation(db: Session, sim_data: schemas.SimulationCreate, nodes_id: int, edges_id: int, paths_id: int, blocked_components_data: list):
    db_sim = models.Simulation(
        **sim_data.model_dump(),
        nodes_file_id=nodes_id,
        edges_file_id=edges_id,
        paths_file_id=paths_id,
        status=models.SimulationStatus.RUNNING  # <-- Nace directamente en estado RUNNING
    )
    db.add(db_sim)
    db.commit()
    db.refresh(db_sim)
    
    # Guardar los blocked_components si existen
    if blocked_components_data:
        comps_to_insert = [
            {
                "simulation_id": db_sim.id,
                "component_name": bc["component_name"],
                "stage_number": bc["stage_number"]
            }
            for bc in blocked_components_data
        ]
        add_blocked_components_bulk(db, comps_to_insert)
        
    return db_sim

def get_simulation(db: Session, sim_id: UUID):
    return db.query(models.Simulation).filter(models.Simulation.id == sim_id).first()

def update_simulation_status(db: Session, sim_id: UUID, status: models.SimulationStatus, error: str = None):
    db_sim = get_simulation(db, sim_id)
    if db_sim:
        db_sim.status = status
        if error:
            db_sim.error_message = error
        db.commit()
        db.refresh(db_sim)
    return db_sim

def delete_simulation(db: Session, sim_id: UUID):
    db_sim = get_simulation(db, sim_id)
    if not db_sim:
        return False
        
    file_ids_to_check = {db_sim.nodes_file_id, db_sim.edges_file_id, db_sim.paths_file_id}
    
    db.delete(db_sim)
    db.commit()

    # Garbage Collection: Limpieza de archivos huérfanos solo en DB
    for f_id in file_ids_to_check:
        if not f_id: continue
        is_used = db.query(models.Simulation).filter(
            (models.Simulation.nodes_file_id == f_id) | 
            (models.Simulation.edges_file_id == f_id) | 
            (models.Simulation.paths_file_id == f_id)
        ).first()
        
        if not is_used:
            db_file = db.query(models.SimulationFile).get(f_id)
            if db_file:
                db.delete(db_file) # <-- ¡Adiós os.remove() y OSError!
    
    db.commit()
    return True

# --- 3. GUARDADO DE RESULTADOS (Versión de Alta Velocidad) ---

def add_simulation_stages_bulk(db: Session, sim_id: UUID, stages_data: list):
    """Inserta todas las etapas de la simulación de golpe."""
    for stage in stages_data:
        stage["simulation_id"] = sim_id
    db.bulk_insert_mappings(models.SimulationStage, stages_data)
    db.commit()

def create_critical_path(db: Session, sim_id: UUID, path_number: int):
    """Crea la cabecera de la ruta crítica."""
    db_path = models.CriticalPath(simulation_id=sim_id, path_number=path_number)
    db.add(db_path)
    db.commit()
    db.refresh(db_path)
    return db_path

def add_path_nodes_bulk(db: Session, path_id: int, nodes_names: list):
    """Inserta nombres de componentes en masa."""
    mappings = [{"path_id": path_id, "component_name": name} for name in nodes_names]
    db.bulk_insert_mappings(models.PathNode, mappings)
    db.commit()

def add_path_edges_bulk(db: Session, path_id: int, edges_data: list):
    """Inserta aristas de la ruta en masa."""
    for edge in edges_data:
        edge["path_id"] = path_id
    db.bulk_insert_mappings(models.PathEdge, edges_data)
    db.commit()

def add_critical_path_stages_bulk(db: Session, path_id: int, stages_data: list):
    """Inserta evolución de la ruta por etapa en masa."""
    for stage in stages_data:
        stage["path_id"] = path_id
    db.bulk_insert_mappings(models.CriticalPathStage, stages_data)
    db.commit()

def add_blocked_components_bulk(db:Session, components_data: list):
    """Inserta componentes bloqueados en masa."""
    db.bulk_insert_mappings(models.BlockedComponents, components_data)
    db.commit()

def get_simulation_stages(db: Session, sim_id: UUID):
    return db.query(models.SimulationStage).filter(
        models.SimulationStage.simulation_id == sim_id
    ).order_by(models.SimulationStage.stage_number).all()

def create_critical_path(db: Session, sim_id: UUID, path_number: int, affected_stages: list):
    db_path = models.CriticalPath(
        simulation_id=sim_id, 
        path_number=path_number,
        affected_stages=affected_stages # Se guarda como JSON/Array en la DB
    )
    db.add(db_path)
    db.commit()
    db.refresh(db_path)
    return db_path