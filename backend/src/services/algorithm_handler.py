import io
import logging
import traceback
import numpy as np
from sqlalchemy.orm import Session
from uuid import UUID
import pandas as pd
import ast

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

import ast
import pandas as pd

def validate_and_prepare_data(buffer_nodos, buffer_aristas, buffer_paths, l_extra):
    """
    Lee los CSVs, valida las cabeceras reales y aplica el parsing
    original de guangorithm.py (ast.literal_eval, percentiles y diccionarios).
    """
    # ── 1. VALIDACIÓN ESTRICTA DE CABECERAS REALES ──
    try:
        df_n = pd.read_csv(buffer_nodos, nrows=0)
        df_a = pd.read_csv(buffer_aristas, nrows=0)
        df_p = pd.read_csv(buffer_paths, nrows=0)
        
        if not all(c in df_n.columns for c in ['node', 'architecture', 'component']): 
            raise ValueError(f"Archivo de NODOS inválido. Cabeceras detectadas: {list(df_n.columns)}")
        if not all(c in df_a.columns for c in ['invoker', 'invoked', 'avg_time']): 
            raise ValueError(f"Archivo de ARISTAS inválido. Cabeceras detectadas: {list(df_a.columns)}")
        if 'full_path' not in df_p.columns: 
            raise ValueError(f"Archivo de RUTAS inválido. Cabeceras detectadas: {list(df_p.columns)}")
    except pd.errors.EmptyDataError:
        raise ValueError("Uno de los archivos CSV está completamente vacío.")
    
    buffer_nodos.seek(0)
    buffer_aristas.seek(0)
    buffer_paths.seek(0)

    # ── 2. LECTURA ──
    nodes_df = pd.read_csv(buffer_nodos)
    edges_df = pd.read_csv(buffer_aristas)
    paths_df = pd.read_csv(buffer_paths)

    # ── 3. EXTRACCIÓN Y LIMPIEZA ──

    # A) method_to_component (desde nodes_df)
    method_to_component = {}
    for _, row in nodes_df.iterrows():
        method_to_component[row['node']] = row['component']

    # B) Procesamiento de Nodos
    def resolve_arch(archs):
        return 'on-prem' if 'on-prem' in archs.values else 'cloud'

    comp_arch = nodes_df.groupby('component')['architecture'].apply(resolve_arch).reset_index()
    comp_arch.columns = ['component', 'architecture']
    comp_nodes = nodes_df.groupby('component')['node'].apply(list).reset_index()
    grouped = comp_arch.merge(comp_nodes, on='component')

    nodes_dict = {}
    for _, row in grouped.iterrows():
        nodes_dict[row['component']] = {
            "nodes": row['node'],
            "migrated": row['architecture'] == "cloud"
        }
        
    pending_components = {comp_id for comp_id, info in nodes_dict.items() if not info["migrated"]}

    # C) Procesamiento de Aristas
    edges_df = edges_df.copy()
    mask_neg = edges_df['avg_time'] < 0
    if mask_neg.sum():
        edges_df.loc[mask_neg, 'avg_time'] = edges_df.loc[mask_neg, 'avg_time'].abs()
        
    if edges_df['avg_time'].isna().sum():
        edges_df = edges_df.dropna(subset=['avg_time'])
        
    cap_val = float(edges_df['avg_time'].quantile(0.95))
    mask_out = edges_df['avg_time'] > cap_val
    if mask_out.sum():
        edges_df.loc[mask_out, 'avg_time'] = cap_val
        
    edges_dict = {}
    for _, row in edges_df.iterrows():
        edges_dict[(row['invoker'], row['invoked'])] = row['avg_time']

    # D) Función auxiliar de latencia inicial
    def calculate_path_latency(path_info, pending, m2c, l_ext):
        acc_latency = {}
        for invoker, invoked, edge_latency in path_info['edges_data']:
            comp_invoker = m2c.get(invoker)
            comp_invoked = m2c.get(invoked)
            crossing = 0
            if comp_invoker and comp_invoked:
                if (comp_invoker in pending) != (comp_invoked in pending):
                    crossing = 1
            if invoker not in acc_latency:
                acc_latency[invoker] = 0
            new_latency = acc_latency[invoker] + edge_latency + (crossing * l_ext)
            if invoked not in acc_latency:
                acc_latency[invoked] = new_latency
            else:
                acc_latency[invoked] = max(acc_latency[invoked], new_latency)
        return max(acc_latency.values()) if acc_latency else 0

    # E) Procesamiento de Rutas (parse_path real)
    paths_dict = {}
    seen_paths = set()
    for index, row in paths_df.iterrows():
        path_str = row['full_path']
        try:
            raw_tuples = ast.literal_eval(path_str)
        except (ValueError, SyntaxError):
            raw_tuples = []
            
        cleaned_edges = []
        seen = set()
        for invoker, invoked in raw_tuples:
            if invoker == -1 or invoked == -1:
                continue
            current_tuple = (invoker, invoked)
            if current_tuple in seen:
                continue
            seen.add(current_tuple)
            cleaned_edges.append(current_tuple)

        if not cleaned_edges:
            continue
        if tuple(cleaned_edges) in seen_paths:
            continue
        seen_paths.add(tuple(cleaned_edges))

        edges_data = [(inv, invd, edges_dict.get((inv, invd), 0)) for inv, invd in cleaned_edges]
        paths_dict[f"path_{index}"] = {
            "edges": cleaned_edges,
            "edges_data": edges_data,
            "current_total": 0
        }

    # Asignar latencias iniciales
    for path_id, path_info in paths_dict.items():
        path_info["current_total"] = calculate_path_latency(path_info, pending_components, method_to_component, l_extra)

    # F) Mapas de adyacencia y cruce
    component_to_paths = {}
    component_adjacency = {}
    for comp in nodes_dict.keys():
        component_to_paths[comp] = set()
        component_adjacency[comp] = {'invokes': set(), 'invoked_by': set()}

    for path_id, path_info in paths_dict.items():
        for invoker, invoked in path_info['edges']:
            comp_invoker = method_to_component.get(invoker)
            comp_invoked = method_to_component.get(invoked)
            if comp_invoker: component_to_paths[comp_invoker].add(path_id)
            if comp_invoked: component_to_paths[comp_invoked].add(path_id)
            if comp_invoker and comp_invoked and comp_invoker != comp_invoked:
                component_adjacency[comp_invoker]['invokes'].add(comp_invoked)
                component_adjacency[comp_invoked]['invoked_by'].add(comp_invoker)

    # G) Clustering Leiden
    try:
        import igraph as ig
        import leidenalg
        all_components = nodes_df['component'].unique().tolist()
        comp_to_idx = {c: i for i, c in enumerate(all_components)}
        edge_weights = {}
        for _, row in edges_df.iterrows():
            avg_time = row['avg_time']
            if pd.isna(avg_time): continue
            comp_inv = method_to_component.get(row['invoker'])
            comp_invd = method_to_component.get(row['invoked'])
            if not comp_inv or not comp_invd or comp_inv == comp_invd: continue
            key = (min(comp_inv, comp_invd), max(comp_inv, comp_invd))
            edge_weights[key] = edge_weights.get(key, 0) + avg_time
            
        g = ig.Graph(n=len(all_components), edges=[(comp_to_idx[a], comp_to_idx[b]) for a, b in edge_weights], directed=False)
        g.es['weight'] = list(edge_weights.values())
        partition = leidenalg.find_partition(g, leidenalg.CPMVertexPartition, weights='weight', resolution_parameter=10.0, n_iterations=10, seed=42)
        component_to_cluster = {all_components[node_idx]: cluster_id for cluster_id, members in enumerate(partition) for node_idx in members}
    except ImportError:
        all_components = nodes_df['component'].unique().tolist()
        component_to_cluster = {c: i for i, c in enumerate(all_components)}

    return edges_dict, nodes_dict, paths_dict, method_to_component, component_to_paths, component_adjacency, pending_components, component_to_cluster

def run_simulation_process(db: Session, sim_id: UUID):
    sim = crud.get_simulation(db, sim_id)
    if not sim: return

    try:
        buffer_nodos = io.BytesIO(sim.nodes_file.content)
        buffer_aristas = io.BytesIO(sim.edges_file.content)
        buffer_paths = io.BytesIO(sim.paths_file.content)
        
        nodes_dict, edges_dict, paths_dict, method_to_component, \
        component_to_paths, component_adjacency, pending_components, \
        component_to_cluster = validate_and_prepare_data(
            buffer_nodos, buffer_aristas, buffer_paths, sim.l_extra
        )
        
        algo_type = getattr(sim, "algorithm_type", "guangorithm")
        algorithm_func = ALGORITHM_STRATEGIES.get(algo_type, run_guangorithm)
        
        logger.info(f"Ejecutando simulación {sim_id} con la estrategia: {algo_type}")

        bloqueos_db = db.query(models.BlockedComponents).filter_by(simulation_id=sim_id).all()
        bloqueos_lista = [{"component_name": b.component_name, "stage_number": b.stage_number} for b in bloqueos_db]

        migration_plan = algorithm_func(
            nodes_dict=nodes_dict,
            edges_dict=edges_dict,
            paths_dict=paths_dict,
            method_to_component=method_to_component,
            component_to_paths=component_to_paths,
            component_adjacency=component_adjacency,
            pending_components=pending_components,
            component_to_cluster=component_to_cluster,
            c_min=sim.c_min, 
            c_max=sim.c_max,
            l_max=sim.l_max, 
            l_extra=sim.l_extra,
            umbral=sim.threshold,
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

        # 3. Cálculo de HITOS (Affected Stages)
        for path_data in plan["rutas_criticas"]:
            path_nodes = set(path_data["nodos"]) 
            hitos = [0] 
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