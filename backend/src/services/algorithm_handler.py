import logging
from sqlalchemy.orm import Session
from uuid import UUID
import traceback
import numpy as np

from app.db import crud, models
from app.services.guangorithm import generate_migration_plan

logger=logging.getLogger(__name__)

def to_serializable(obj):
    if isinstance(obj, (np.integer, int)): return int(obj)
    if isinstance(obj, (np.floating, float)): return float(obj)
    if isinstance(obj, list): return [to_serializable(item) for item in obj]
    if isinstance(obj, dict): return {k: to_serializable(v) for k, v in obj.items()}
    return obj

def run_simulation_process(db: Session, sim_id: UUID):
    sim = crud.get_simulation(db, sim_id)
    if not sim: return

    try:
        ruta_nodos = sim.nodes_file.path
        ruta_aristas = sim.edges_file.path
        ruta_paths = sim.paths_file.path
        
        c_min = sim.c_min
        c_max = sim.c_max
        l_max = sim.l_max
        l_extra = sim.l_extra
        threshold = sim.threshold
        crud.update_simulation_status(db, sim_id, models.SimulationStatus.RUNNING)

        bloqueos_db = db.query(models.BlockedComponents).filter_by(simulation_id=sim_id).all()
        bloqueos_lista = [{"component_name": b.component_name, "stage_number": b.stage_number} for b in bloqueos_db]

        # 1. Ejecutar Algoritmo
        migration_plan = generate_migration_plan(
            ruta_nodos=ruta_nodos,
            ruta_aristas=ruta_aristas,
            ruta_paths=ruta_paths,
            c_min=c_min, c_max=c_max,
            l_max=l_max, l_extra=l_extra,
            umbral=threshold,
            lista_bloqueos=bloqueos_lista
        )

        if not crud.update_simulation_status(db, sim_id, models.SimulationStatus.RUNNING):
            logger.error(f"La simulación {sim_id} fue eliminada por el usuario. Abortando guardado.")
            return
        
        plan = to_serializable(migration_plan)

        # 2. Guardar Etapas Globales
        stages_data = [
            {
                "stage_number": i,
                "migrated_components": etapa["migrated_components"],
                "worst_critical_time": etapa["worst_critical_time"]
            } 
            for i, etapa in enumerate(plan["etapas"])
        ]
        crud.add_simulation_stages_bulk(db, sim_id, stages_data)

        # 3. Cálculo de HITOS (Affected Stages) por Camino Crítico
        # Esto es lo que soluciona el "salto a la derecha"
        for path_data in plan["rutas_criticas"]:
            path_nodes = set(path_data["nodos"]) # Componentes en este camino
            
            # Buscamos en qué etapas se movió algún componente de este set
            hitos = [0] # Siempre incluir la etapa inicial
            for i, etapa in enumerate(plan["etapas"]):
                componentes_etapa = set(etapa["migrated_components"])
                # Si hay intersección, esta etapa AFECTA al camino
                if path_nodes.intersection(componentes_etapa):
                    hitos.append(i)
            
            # Guardamos la cabecera del camino con sus HITOS reales
            db_path = crud.create_critical_path(
                db, 
                sim_id, 
                path_data["path_number"], 
                affected_stages=sorted(list(set(hitos))) # Guardamos los índices
            )
            
            # Guardamos el resto de la estructura (nodos/aristas)
            crud.add_path_nodes_bulk(db, db_path.id, path_data["nodos"])
            crud.add_path_edges_bulk(db, db_path.id, path_data["aristas"])

        if plan["meets_requirements"]:
            crud.update_simulation_status(db, sim_id, models.SimulationStatus.COMPLETED)
        else:
            crud.update_simulation_status(db, sim_id, models.SimulationStatus.FAILED)

    except Exception as e:
        db.rollback()
        error_details = traceback.format_exc()
        logger.error(f"FALLO CRÍTICO en simulación {sim_id}:\n{error_details}")
        crud.update_simulation_status(db, sim_id, models.SimulationStatus.ERROR, error=str(e))