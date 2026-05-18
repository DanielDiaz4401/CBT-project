import io
import logging
import sys
import traceback
import numpy as np
from sqlalchemy.orm import Session
from uuid import UUID
import pandas as pd
import ast

from app.db import crud, models

# 🔥 1. FORZAR LOGS EN DOCKER 🔥
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Importamos las funciones de cada algoritmo con alias
from app.services.guangorithm import generate_migration_plan as run_guangorithm
from app.services.robergorithm2 import generate_migration_plan as run_robergorithm_v2
from app.services.robergorithm3 import generate_migration_plan as run_robergorithm_v3

ALGORITHM_STRATEGIES = {
    "guangorithm": run_guangorithm,
    "robergorithm_v2": run_robergorithm_v2,
    "robergorithm_v3": run_robergorithm_v3
}

def validate_and_prepare_data(buffer_nodos, buffer_aristas, buffer_paths, l_extra):
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

    nodes_df = pd.read_csv(buffer_nodos)
    edges_df = pd.read_csv(buffer_aristas)
    paths_df = pd.read_csv(buffer_paths)

    # 🛡️ FIX CRÍTICO: Forzar todos los identificadores a String para evitar colisiones de tipo (int vs str)
    nodes_df['component'] = nodes_df['component'].astype(str)
    nodes_df['node'] = nodes_df['node'].astype(str)
    edges_df['invoker'] = edges_df['invoker'].astype(str)
    edges_df['invoked'] = edges_df['invoked'].astype(str)

    method_to_component = {}
    for _, row in nodes_df.iterrows():
        method_to_component[row['node']] = row['component']

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
        edges_dict[(row['invoker'], row['invoked'])] = float(row['avg_time'])

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
            inv_str, invd_str = str(invoker), str(invoked) # Convertimos la ruta a strings
            if inv_str == '-1' or invd_str == '-1':
                continue
            current_tuple = (inv_str, invd_str)
            if current_tuple in seen:
                continue
            seen.add(current_tuple)
            cleaned_edges.append(current_tuple)

        if not cleaned_edges:
            continue
        if tuple(cleaned_edges) in seen_paths:
            continue
        seen_paths.add(tuple(cleaned_edges))

        edges_data = [(inv, invd, edges_dict.get((inv, invd), 0.0)) for inv, invd in cleaned_edges]
        paths_dict[f"path_{index}"] = {
            "edges": cleaned_edges,
            "edges_data": edges_data,
            "current_total": 0
        }

    for path_id, path_info in paths_dict.items():
        path_info["current_total"] = calculate_path_latency(path_info, pending_components, method_to_component, l_extra)

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

    return nodes_dict, edges_dict, paths_dict, method_to_component, component_to_paths, component_adjacency, pending_components, component_to_cluster

def run_simulation_process(db: Session, sim_id: UUID):
    sim = crud.get_simulation(db, sim_id)
    if not sim: return

    try:
        logger.info(f"🟢 [SIM {sim_id}] Iniciando preparación de datos (Lectura CSV)...")
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
        
        bloqueos_db = db.query(models.BlockedComponents).filter_by(simulation_id=sim_id).all()
        bloqueos_lista = [{"component_name": b.component_name, "stage_number": b.stage_number} for b in bloqueos_db]

        logger.info(f"⚙️ [SIM {sim_id}] Ejecutando motor matemático: {algo_type}")
        
        plan = algorithm_func(
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
        
        logger.info(f"✅ [SIM {sim_id}] Algoritmo finalizado. Comenzando guardado en Base de Datos...")

        # 1. Recuperamos los nodos que YA ESTABAN en el Cloud en el CSV inicial
        initial_cloud_nodes = [comp for comp, info in nodes_dict.items() if info["migrated"]]
        
        # Calculamos la latencia máxima inicial (Etapa 0) por si el Frontend la necesita
        initial_time = 0.0
        if plan.get("rutas_criticas"):
            for r in plan["rutas_criticas"]:
                for evo in r.get("evolucion_por_etapa", []):
                    if evo["stage_number"] == 0 and evo["critical_time"] > initial_time:
                        initial_time = evo["critical_time"]

        # 2. Inyectamos la "Etapa 0" en la Base de Datos para que React la lea
        stages_data = [{
            "stage_number": 0,
            "migrated_components": initial_cloud_nodes,
            "worst_critical_time": float(initial_time)
        }]
        
        # 3. Añadimos el resto de etapas reales de migración
        for etapa in plan["etapas"]:
            stages_data.append({
                "stage_number": etapa["stage_number"], 
                "migrated_components": etapa["migrated_components"],
                "worst_critical_time": float(etapa["worst_critical_time"])
            })
            
        crud.add_simulation_stages_bulk(db, sim_id, stages_data)
        
        total_rutas = len(plan["rutas_criticas"])
        logger.info(f"💾 [SIM {sim_id}] Preparando inserción masiva de {total_rutas} rutas críticas...")
        
        db_paths = []
        for path_data in plan["rutas_criticas"]:
            path_nodes = set(path_data["nodos"]) 
            hitos = [0] 
            for etapa in plan["etapas"]:
                if path_nodes.intersection(set(etapa["migrated_components"])):
                    hitos.append(etapa["stage_number"])

            
            db_path = models.CriticalPath(
                simulation_id=sim_id,
                path_number=path_data["path_number"],
                affected_stages=sorted(list(set(hitos)))
            )
            db_paths.append(db_path)
            
        # Obtenemos los IDs pre-generados de las rutas
        db.add_all(db_paths)
        db.flush() 
        
        all_nodes = []
        all_edges = []
        
        # 1. Inyectamos nodos y aristas base primero (Ocupan megabytes, no hay problema)
        for db_path, path_data in zip(db_paths, plan["rutas_criticas"]):
            for node in path_data["nodos"]:
                all_nodes.append({"path_id": db_path.id, "component_name": node})
            for edge in path_data["aristas"]:
                all_edges.append({
                    "path_id": db_path.id,
                    "invoker": edge["invoker"],
                    "invoked": edge["invoked"],
                    "base_latency": float(edge["base_latency"])
                })
                
        if all_nodes: db.bulk_insert_mappings(models.PathNode, all_nodes)
        if all_edges: db.bulk_insert_mappings(models.PathEdge, all_edges)
            
        logger.info(f"🚀 [SIM {sim_id}] Inyectando historial temporal ruta por ruta para salvar RAM...")
        
        # 2. 🔥 INSERCIÓN "STREAMING" (El salvavidas de la memoria) 🔥
        for db_path, path_data in zip(db_paths, plan["rutas_criticas"]):
            path_stages = [] # <--- Nace vacío SOLO para esta ruta
            
            for evo in path_data.get("evolucion_por_etapa", []):
                path_stages.append({
                    "path_id": db_path.id,
                    "stage_number": evo["stage_number"],
                    "critical_time": float(evo["critical_time"]),
                    "migrated_components": evo["migrated_components"],
                    "worst_path_edges": evo.get("worst_path_edges", []),
                    "extra_latency_edges": evo.get("extra_latency_edges", [])
                })
            
            # Insertamos solo las etapas de esta ruta (aprox 2.000 diccionarios) directamente a BD
            if path_stages:
                db.bulk_insert_mappings(models.CriticalPathStage, path_stages)
                
            # Al terminar el bucle, Python destruye 'path_stages', liberando la RAM inmediatamente

        # 3. El único COMMIT al disco de todo el proceso
        if plan["meets_requirements"]:
            crud.update_simulation_status(db, sim_id, models.SimulationStatus.COMPLETED)
            logger.info(f"🎉 [SIMULATION {sim_id}] Completada con Éxito.")
        else:
            crud.update_simulation_status(db, sim_id, models.SimulationStatus.FAILED)
            logger.warning(f"⚠️ [SIMULATION {sim_id}] Completada pero falló los requisitos (Fallback forzado).")
            
        db.commit()

    except Exception as e:
        db.rollback()
        error_details = traceback.format_exc()
        logger.error(f"💥 FALLO CRÍTICO en simulación {sim_id}:\n{error_details}")
        crud.update_simulation_status(db, sim_id, models.SimulationStatus.ERROR, error=str(e))
        db.commit()
