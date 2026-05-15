import io
import logging
import traceback
import numpy as np
from sqlalchemy.orm import Session
from uuid import UUID

from app.db import crud, models

# 1. Importamos las funciones de cada algoritmo con alias
from app.services.guangorithm import generate_migration_plan as run_guangorithm
from app.services.robergorithm2 import generate_migration_plan as run_robergorithm_v2
from app.services.robergorithm3 import generate_migration_plan as run_robergorithm_v3

logger = logging.getLogger(__name__)

# 2. PATRÓN STRATEGY: Diccionario que mapea el tipo de algoritmo a su función
ALGORITHM_STRATEGIES = {
    "guangorithm": run_guangorithm,
    "robergorithm_v2": run_robergorithm_v2,
    "robergorithm_v3": run_robergorithm_v3
}

def to_serializable(obj):
    if isinstance(obj, (np.integer, int)): return int(obj)
    if isinstance(obj, (np.floating, float)): return float(obj)
    if isinstance(obj, list): return [to_serializable(item) for item in obj]
    if isinstance(obj, dict): return {k: to_serializable(v) for k, v in obj.items()}
    return obj

def validate_and_prepare_data(buffer_nodos, buffer_aristas, buffer_paths):
    """
    1. Valida que los CSVs tengan las cabeceras correctas.
    2. Usa Pandas para limpiar duplicados, NaN y percentiles.
    3. Devuelve estructuras nativas de Python (diccionarios) para que los algoritmos no dependan de Pandas.
    """
    # ── VALIDACIÓN ──
    try:
        df_n = pd.read_csv(buffer_nodos, nrows=0)
        df_a = pd.read_csv(buffer_aristas, nrows=0)
        df_p = pd.read_csv(buffer_paths, nrows=0)
        
        if 'component' not in df_n.columns: raise ValueError(f"Falta 'component' en NODOS. Cabeceras: {list(df_n.columns)}")
        if not all(c in df_a.columns for c in ['invoker', 'invoked', 'avg_time']): raise ValueError("Aristas inválidas.")
        if not all(c in df_p.columns for c in ['path_number', 'node']): raise ValueError("Rutas inválidas.")
    except pd.errors.EmptyDataError:
        raise ValueError("Uno de los archivos CSV está completamente vacío.")
    
    # Devolvemos el cursor a 0 para leer los datos reales
    buffer_nodos.seek(0)
    buffer_aristas.seek(0)
    buffer_paths.seek(0)

    # ── LECTURA Y LIMPIEZA ──
    nodes_df = pd.read_csv(buffer_nodos)
    edges_df = pd.read_csv(buffer_aristas)
    paths_df = pd.read_csv(buffer_paths)

    # 1. Nodos -> dict {component_id: architecture}
    nodes_dict = nodes_df.drop_duplicates(subset=['component']).set_index('component')['architecture'].to_dict()

    # 2. Aristas -> dict {(invoker, invoked): avg_time}
    # Aseguramos compatibilidad si la columna viene como 'base_latency' o 'avg_time'
    lat_col = 'avg_time' if 'avg_time' in edges_df.columns else 'base_latency'
    edges_df[lat_col] = edges_df[lat_col].abs()
    edges_df = edges_df.dropna(subset=[lat_col])
    cap_val = edges_df[lat_col].quantile(0.95)
    edges_df[lat_col] = edges_df[lat_col].clip(upper=cap_val)
    edges_dict = edges_df.set_index(['invoker', 'invoked'])[lat_col].to_dict()

    # 3. Rutas -> dict {path_number: [nodo1, nodo2, ...]}
    paths_dict = paths_df.groupby('path_number')['node'].apply(list).to_dict()

    # 4. Mapa Método-Componente -> dict {node: component}
    # (Asumiendo que paths_df tiene la columna 'component' pre-calculada, si no, se saca de nodes_df)
    method_to_component = paths_df.drop_duplicates(subset=['node']).set_index('node')['component'].to_dict() if 'component' in paths_df.columns else {}

    return nodes_dict, edges_dict, paths_dict, method_to_component

def run_simulation_process(db: Session, sim_id: UUID):
    sim = crud.get_simulation(db, sim_id)
    if not sim: return

    try:
        # Recuperamos archivos desde PostgreSQL en memoria (Fase 1)
        buffer_nodos = io.BytesIO(sim.nodes_file.content)
        buffer_aristas = io.BytesIO(sim.edges_file.content)
        buffer_paths = io.BytesIO(sim.paths_file.content)
        
        c_min = sim.c_min
        c_max = sim.c_max
        l_max = sim.l_max
        l_extra = sim.l_extra
        threshold = sim.threshold

        # 3. Extraemos el algoritmo seleccionado (por defecto guangorithm)
        algo_type = getattr(sim, "algorithm_type", "guangorithm")
        
        # 4. Seleccionamos la estrategia (función) a ejecutar
        algorithm_func = ALGORITHM_STRATEGIES.get(algo_type, run_guangorithm)
        
        logger.info(f"Ejecutando simulación {sim_id} con la estrategia: {algo_type}")

        bloqueos_db = db.query(models.BlockedComponents).filter_by(simulation_id=sim_id).all()
        bloqueos_lista = [{"component_name": b.component_name, "stage_number": b.stage_number} for b in bloqueos_db]

        # 5. Ejecutamos la función dinámica
        migration_plan = algorithm_func(
            ruta_nodos=buffer_nodos,
            ruta_aristas=buffer_aristas,
            ruta_paths=buffer_paths,
            c_min=c_min, c_max=c_max,
            l_max=l_max, l_extra=l_extra,
            umbral=threshold,
            lista_bloqueos=bloqueos_lista
        )
        
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