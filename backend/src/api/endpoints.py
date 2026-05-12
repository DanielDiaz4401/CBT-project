import os
import json
import asyncio
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter, Depends, HTTPException, Form, File,
    UploadFile, status, BackgroundTasks, Request
)
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session

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

# ==========================================
# RECURSO: /simulations
# ==========================================

@router.get(
    "", 
    response_model=List[schemas.SimulationSummary],
    summary="Listar todas las simulaciones"
)
def list_simulations(skip: int = 0, limit: int = 100, db: Session = Depends(session.get_db)):
    return crud.get_simulations(db, skip=skip, limit=limit)


@router.post(
    "", 
    response_model=schemas.SimulationSummary, 
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva simulación"
)
async def create_simulation(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    l_extra: float = Form(...),
    c_min: int = Form(...),
    c_max: int = Form(...),
    l_max: float = Form(...),
    threshold: float = Form(...),
    blocked_components: str = Form("[]"),
    nodes_file: Optional[UploadFile] = File(None),
    edges_file: Optional[UploadFile] = File(None),
    paths_file: Optional[UploadFile] = File(None),
    base_sim_id: Optional[str] = Form(None),
    db: Session = Depends(session.get_db)
):
    if base_sim_id:
        base_sim = crud.get_simulation(db, UUID(base_sim_id))
        if not base_sim:
            raise HTTPException(status_code=404, detail="Simulación base no encontrada")
        nodes_id = base_sim.nodes_file_id
        edges_id = base_sim.edges_file_id
        paths_id = base_sim.paths_file_id
    else:
        if not nodes_file or not edges_file or not paths_file:
            raise HTTPException(status_code=400, detail="Faltan archivos para la creación")
        
        n_content = await nodes_file.read()
        e_content = await edges_file.read()
        p_content = await paths_file.read()

        nodes_id = crud.get_or_create_file(db, nodes_file.filename, n_content).id
        edges_id = crud.get_or_create_file(db, edges_file.filename, e_content).id
        paths_id = crud.get_or_create_file(db, paths_file.filename, p_content).id

    try:
        blocked_comps_list = json.loads(blocked_components)
    except json.JSONDecodeError:
        blocked_comps_list = []

    sim_data = schemas.SimulationCreate(
        name=name, l_extra=l_extra, c_min=c_min, c_max=c_max, l_max=l_max, threshold=threshold
    )

    new_sim = crud.create_simulation(db, sim_data, nodes_id, edges_id, paths_id, blocked_comps_list)
    
    pending_tasks.add(new_sim.id)
    background_tasks.add_task(run_simulation_process_bg, new_sim.id)

    return new_sim


@router.get("/{sim_id}", response_model=schemas.SimulationSummary)
def get_simulation(sim_id: UUID, db: Session = Depends(session.get_db)):
    sim = crud.get_simulation(db, sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulación no encontrada")
    return sim


@router.patch("/{sim_id}", response_model=schemas.SimulationSummary)
def update_simulation(sim_id: UUID, name: str = None, db: Session = Depends(session.get_db)):
    sim = crud.get_simulation(db, sim_id)
    if not sim:
        raise HTTPException(status_code=404)
    if name:
        sim.name = name
    db.commit()
    return sim


@router.delete("/{sim_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_simulation(sim_id: UUID, db: Session = Depends(session.get_db)):
    if not crud.delete_simulation(db, sim_id):
        raise HTTPException(status_code=404)
    pending_tasks.discard(sim_id)
    return None

# ==========================================
# SUB-RECURSO: /simulations/{id}/stages
# ==========================================

@router.get("/{sim_id}/stages", response_model=List[schemas.StageSummary])
def get_simulation_stages(sim_id: UUID, db: Session = Depends(session.get_db)):
    return crud.get_simulation_stages(db, sim_id)


@router.get("/{sim_id}/stages/{stage_number}/critical-path-update", response_model=schemas.CriticalPathStepUpdate)
def get_stage_path_update(sim_id: UUID, stage_number: int, db: Session = Depends(session.get_db)):
    stage_info = db.query(crud.models.SimulationStage).filter(
        crud.models.SimulationStage.simulation_id == sim_id,
        crud.models.SimulationStage.stage_number == stage_number
    ).first()
    
    if not stage_info:
        raise HTTPException(status_code=404)

    return schemas.CriticalPathStepUpdate(
        stage_number=stage_number,
        newly_migrated_nodes=stage_info.migrated_components,
        worst_path_edges=[],
        extra_latency_edges=[]
    )

# ==========================================
# SUB-RECURSO: /simulations/{id}/critical-paths
# ==========================================

@router.get("/{sim_id}/critical-paths", response_model=List[schemas.CriticalPathHito])
def get_simulation_critical_paths(sim_id: UUID, db: Session = Depends(session.get_db)):
    paths = db.query(crud.models.CriticalPath).filter(crud.models.CriticalPath.simulation_id == sim_id).all()
    if not paths:
        raise HTTPException(status_code=404)
    
    return [{"path_number": p.path_number, "affected_stages": p.affected_stages} for p in paths]


@router.get("/{sim_id}/critical-paths/{path_num}/topology")
def get_path_topology(sim_id: UUID, path_num: int, db: Session = Depends(session.get_db)):
    path = db.query(crud.models.CriticalPath).filter(
        crud.models.CriticalPath.simulation_id == sim_id,
        crud.models.CriticalPath.path_number == path_num
    ).first()
    
    if not path:
        raise HTTPException(status_code=404)

    nodes_mapping = {n.component_name: n.component_name for n in path.nodes}
    edge_latencies = {f"{e.invoker}|{e.invoked}": e.base_latency for e in path.edges}
    
    return {
        "nodes_mapping": nodes_mapping,
        "edge_latencies": edge_latencies,
        "initial_cloud_nodes": []
    }

# ==========================================
# RECURSOS TÉCNICOS Y EVENTOS
# ==========================================

@router.get("/events/stream")
async def stream_status(request: Request):
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


@router.get("/{sim_id}/artifacts/{file_type}")
def get_simulation_artifact(sim_id: UUID, file_type: schemas.SimulationFileType, db: Session = Depends(session.get_db)):
    file_record = crud.get_file_by_type(db, sim_id, file_type.value)
    if not file_record or not os.path.exists(file_record.path):
        raise HTTPException(status_code=404)
    
    return FileResponse(
        path=file_record.path, 
        filename=f"{file_type.value}_{sim_id}.csv",
        media_type='text/csv'
    )