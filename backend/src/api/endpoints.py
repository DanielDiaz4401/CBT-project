import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile, status, BackgroundTasks, Request
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db import crud, session
from app.schemas import migration as schemas
from app.services.algorithm_handler import run_simulation_process
from app.db.session import SessionLocal

router = APIRouter(
    prefix="/simulations",
    tags=["Simulations"]
)

# Seguimiento de tareas para SSE
pending_tasks = set()

def run_simulation_process_bg(sim_id: UUID):
    db = SessionLocal()
    try:
        run_simulation_process(db, str(sim_id))
    finally:
        db.close()

# --- 1. GESTIÓN BÁSICA ---

@router.get("/", response_model=List[schemas.SimulationSummary])
def list_simulations(skip: int = 0, limit: int = 100, db: Session = Depends(session.get_db)):
    """Lista todas las simulaciones (Metadatos básicos)."""
    return crud.get_simulations(db, skip=skip, limit=limit)

@router.post("/calculate", response_model=schemas.SimulationSummary)
async def create_simulation(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    l_extra: float = Form(...),
    c_min: int = Form(...),
    c_max: int = Form(...),
    l_max: float = Form(...),
    threshold: float = Form(...),
    nodes_file: UploadFile = File(...),
    edges_file: UploadFile = File(...),
    paths_file: UploadFile = File(...),
    db: Session = Depends(session.get_db)
):
    """Crea la simulación, procesa archivos y lanza el algoritmo en background."""
    # Leer archivos
    n_content = await nodes_file.read()
    e_content = await edges_file.read()
    p_content = await paths_file.read()

    # Deduplicación y guardado
    f_nodes = crud.get_or_create_file(db, nodes_file.filename, n_content)
    f_edges = crud.get_or_create_file(db, edges_file.filename, e_content)
    f_paths = crud.get_or_create_file(db, paths_file.filename, p_content)

    sim_data = schemas.SimulationCreate(
        name=name,
        l_extra=l_extra, c_min=c_min, c_max=c_max, l_max=l_max, threshold=threshold
    )

    new_sim = crud.create_simulation(db, sim_data, f_nodes.id, f_edges.id, f_paths.id)
    
    # Lanzar proceso
    pending_tasks.add(new_sim.id)
    background_tasks.add_task(run_simulation_process_bg, new_sim.id)

    return new_sim

@router.delete("/{sim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_simulation(sim_id: UUID, db: Session = Depends(session.get_db)):
    """Borra una simulación y detiene su seguimiento."""
    if not crud.delete_simulation(db, sim_id):
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    pending_tasks.discard(sim_id)
    return None

@router.patch("/{sim_id}", response_model=schemas.SimulationSummary)
def update_simulation_metadata(sim_id: UUID, name: str = None, db: Session = Depends(session.get_db)):
    """Edita nombre o descripción de una simulación."""
    sim = crud.get_simulation(db, sim_id)
    if not sim: raise HTTPException(status_code=404)
    if name: sim.name = name
    db.commit()
    return sim

# --- 2. MONITOREO (SSE) ---

@router.get("/stream")
async def stream_status(request: Request):
    """Canal de eventos para actualizar el estado en el frontend en tiempo real."""
    async def event_generator():
        while True:
            if await request.is_disconnected(): break
            if not pending_tasks:
                await asyncio.sleep(2)
                continue

            db = SessionLocal()
            try:
                for sim_id in list(pending_tasks):
                    sim = crud.get_simulation(db, sim_id)
                    if not sim: continue
                    
                    yield f"data: {json.dumps({'id': str(sim_id), 'status': sim.status.value})}\n\n"
                    
                    if sim.status in [schemas.SimulationStatus.COMPLETED, schemas.SimulationStatus.FAILED]:
                        pending_tasks.discard(sim_id)
            finally:
                db.close()
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- 3. RESULTADOS (Estrategia de Hitos) ---

@router.get("/get_stages/{sim_id}", response_model=List[schemas.StageSummary])
def get_stages_evolution(sim_id: UUID, db: Session = Depends(session.get_db)):
    """Evolución temporal del tiempo crítico para gráficas."""
    return crud.get_simulation_stages(db, sim_id)

@router.get("/get_critical_paths/{sim_id}", response_model=List[schemas.CriticalPathHito])
def get_critical_paths_hitos(sim_id: UUID, db: Session = Depends(session.get_db)):
    """Devuelve los hitos reales calculados por el handler."""
    paths = db.query(crud.models.CriticalPath).filter(crud.models.CriticalPath.simulation_id == sim_id).all()
    if not paths:
        raise HTTPException(status_code=404, detail="No se encontraron caminos")
    
    return [
        {
            "path_number": p.path_number,
            "affected_stages": p.affected_stages # Ya filtrado: [0, 14, 55...]
        } for p in paths
    ]

@router.get("/get_critical_path_skeleton/{sim_id}/{path_num}")
def get_skeleton(sim_id: UUID, path_num: int, db: Session = Depends(session.get_db)):
    # Buscamos la cabecera de la ruta
    path = db.query(crud.models.CriticalPath).filter(
        crud.models.CriticalPath.simulation_id == sim_id,
        crud.models.CriticalPath.path_number == path_num
    ).first()
    
    if not path: raise HTTPException(status_code=404)

    # Nodos iniciales en cloud (según el archivo de nodos original)
    sim = db.query(crud.models.Simulation).get(sim_id)
    # Aquí deberías tener una lógica para saber qué nodos eran cloud al inicio
    # Por ahora enviamos los nombres de los componentes y las aristas
    
    nodes_mapping = {n.component_name: n.component_name for n in path.nodes}
    edge_latencies = {f"{e.invoker}|{e.invoked}": e.base_latency for e in path.edges}
    
    return {
        "nodes_mapping": nodes_mapping,
        "edge_latencies": edge_latencies,
        "initial_cloud_nodes": [] # Lista de nombres de componentes que ya eran cloud
    }

@router.get("/get_critical_path_step/{sim_id}/{stage_number}", response_model=schemas.CriticalPathStepUpdate)
def get_path_step_update(sim_id: UUID, stage_number: int, db: Session = Depends(session.get_db)):
    """Actualización de estado para una etapa concreta (Nodos migrados y nuevo camino)."""
    # Buscar qué ocurrió en esta simulación en este stage específico
    stage_info = db.query(crud.models.SimulationStage).filter(
        crud.models.SimulationStage.simulation_id == sim_id,
        crud.models.SimulationStage.stage_number == stage_number
    ).first()
    
    if not stage_info: raise HTTPException(status_code=404)

    return schemas.CriticalPathStepUpdate(
        stage_number=stage_number,
        newly_migrated_nodes=stage_info.migrated_components,
        worst_path_edges=[], # Sacar del algoritmo
        extra_latency_edges=[]
    )

# --- 4. UTILIDADES ---

@router.get("/{sim_id}/files/{file_type}")
def download_input_file(sim_id: UUID, file_type: schemas.SimulationFileType, db: Session = Depends(session.get_db)):
    """Permite descargar los CSV originales usados en la simulación."""
    file_record = crud.get_file_by_type(db, sim_id, file_type.value)
    if not file_record or not os.path.exists(file_record.path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    
    return FileResponse(
        path=file_record.path, 
        filename=f"{file_type.value}_{sim_id}.csv",
        media_type='text/csv'
    )