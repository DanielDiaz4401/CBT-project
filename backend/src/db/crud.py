import os
import hashlib
from sqlalchemy.orm import Session
from uuid import UUID
from . import models
from app.schemas import migration as schemas

# --- 1. GESTIÓN DE ARCHIVOS ---

def get_or_create_file(db: Session, filename: str, content: bytes) -> models.SimulationFile:
    content_hash = hashlib.sha256(content).hexdigest()
    db_file = db.query(models.SimulationFile).filter(models.SimulationFile.content_hash == content_hash).first()
    
    if db_file and os.path.exists(db_file.path):
        return db_file
    
    os.makedirs("storage/files", exist_ok=True)
    extension = filename.split(".")[-1] if "." in filename else "csv"
    file_path = f"storage/files/{content_hash}.{extension}"
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    db_file = models.SimulationFile(
        filename=filename,
        path=file_path,
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

def create_simulation(db: Session, sim_data: schemas.SimulationCreate, nodes_id: int, edges_id: int, paths_id: int):
    db_sim = models.Simulation(
        **sim_data.model_dump(),
        nodes_file_id=nodes_id,
        edges_file_id=edges_id,
        paths_file_id=paths_id,
        status=models.SimulationStatus.PENDING
    )
    db.add(db_sim)
    db.commit()
    db.refresh(db_sim)
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
    if db_sim:
        db.delete(db_sim)
        db.commit()
        return True
    return False

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