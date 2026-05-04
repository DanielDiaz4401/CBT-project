import pandas as pd
import json
import ast
import logging

logger = logging.getLogger(__name__)

# Parámetros principales (ahora se pasan como argumentos o toman su valor de ahi)
# c_min=1
# c_max=5
# l_extra=30
# l_max=150

# Importar archivos
def import_jsons(edges_path, nodes_path, paths_path):
    try:
        edges_df = pd.read_csv(edges_path)
        nodes_df = pd.read_csv(nodes_path)
        paths_df = pd.read_csv(paths_path)
        return edges_df, nodes_df, paths_df
    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
        raise e

# edges_dict={
#     (invoker,invoked): avg_time
# }
def process_edges(edges_df):
    edges_dict = {}
    for _, row in edges_df.iterrows():
        invoker = row['invoker']
        invoked = row['invoked']
        avg_time = row['avg_time']
        edges_dict[(invoker, invoked)] = avg_time
    return edges_dict

# Exportar json frontend
# Formato:
# nodes_dict={
#     "C000001": {"nodes": [C000002, C123456], "migrated": true},
#     ...
# }
def process_nodes(nodes_df):
    grouped = nodes_df.groupby(['component', 'architecture'])['node'].apply(list).reset_index()
    nodes_dict = {}
    for _, row in grouped.iterrows():
        nodes_dict[row['component']] = {
            "nodes": row['node'],
            "migrated": True if row['architecture']=="cloud" else False
        }
    return nodes_dict

# Crear función auxiliar para limpiar caminos
def parse_path(path_str):
    try:
        raw_tuples=ast.literal_eval(path_str)
    except (ValueError, SyntaxError):
        return []

    cleaned_path = []
    last_tuple = None
    
    for invoker, invoked in raw_tuples:
        if invoker == -1 or invoked == -1:
            continue
            
        if invoker == invoked:
            continue
            
        current_tuple = (invoker, invoked)
        if current_tuple == last_tuple:
            continue
            
        cleaned_path.append(current_tuple)
        last_tuple = current_tuple
        
    return cleaned_path

# Crear estructura path_state
# path_state["id"]={
#     "edges": []
#     "current_total":
# }
def process_paths(paths_df, pending_components, method_to_component, edges_dict, l_extra):
    paths_dict = {}
    seen_paths = set()
    for index, row in paths_df.iterrows():
        path_str=row['full_path']
        cleaned_edges=parse_path(path_str)

        if not cleaned_edges:
            continue

        if tuple(cleaned_edges) in seen_paths:
            continue
        seen_paths.add(tuple(cleaned_edges))
        
        edges_data = [(invoker, invoked, edges_dict.get((invoker, invoked), 0)) for invoker, invoked in cleaned_edges]
        paths_dict[f"path_{index}"]={
            "edges": cleaned_edges,
            "edges_data": edges_data,
            "current_total": 0
        }
        
    
    # Calcular latencias iniciales, teniendo en cuenta que en un mismo camino pueden haber paralelismos
    for path_id, path_info in paths_dict.items():
        path_info["current_total"] = calculate_path_latency(path_info, pending_components, method_to_component, l_extra)
    print(len(paths_dict))
        
    return paths_dict


# Crear estructura method_to_component
# method_to_component = {
#     1: "C000001",
#     2: "C000002",
#     [...]
# }
def process_methods(nodes_df):
    method_to_component = {}
    for _, row in nodes_df.iterrows():
        method_to_component[row['node']]=row['component']
    return method_to_component

# Crear estructura component_to_paths
# component_to_paths = {
#     "C000001": [path_0, path_1, path_2],
#     "C000002": [path_3, path_4, path_5],
#     [...]
# }
def process_components(nodes_df, paths_dict, method_to_component):
    component_to_paths = {}
    component_adjacency = {} # NEW: Precalc adjacency for risk/benefit O(1)
    
    for _, row in nodes_df.iterrows():
        comp = row['component']
        component_to_paths[comp] = set()
        component_adjacency[comp] = {'invokes': set(), 'invoked_by': set()}
        
    for path_id, path_info in paths_dict.items():
        for invoker, invoked in path_info['edges']:
            component_invoker = method_to_component.get(invoker)
            component_invoked = method_to_component.get(invoked)
            
            if component_invoker:
                component_to_paths[component_invoker].add(path_id)
            if component_invoked:
                component_to_paths[component_invoked].add(path_id)
                
            if component_invoker and component_invoked and component_invoker != component_invoked:
                component_adjacency[component_invoker]['invokes'].add(component_invoked)
                component_adjacency[component_invoked]['invoked_by'].add(component_invoker)
                
    return component_to_paths, component_adjacency

# Set de componentes pendientes de migrar (on-prem)
def process_pending_components(nodes_dict):
    return {comp_id for comp_id, info in nodes_dict.items() if not info["migrated"]}


# Funciones auxiliares
# Función que, dado una tupla, devuelve todos los ids de los paths donde se encuentra la tupla
def get_paths(invoker, invoked, paths_dict):
    paths=[]
    for path_id, path_info in paths_dict.items():
        if (invoker,invoked) in path_info['edges']:
            paths.append(path_id)
    return paths

# Funcion que calcula todos los posibles subcaminos y sus tiempos, devolviendo el maximo
def calculate_path_latency(path_info, pending_components, method_to_component, l_extra):
    acc_latency = {}
    for invoker, invoked, edge_latency in path_info['edges_data']:
        comp_invoker = method_to_component.get(invoker)
        comp_invoked = method_to_component.get(invoked)
        
        crossing = 0
        if comp_invoker and comp_invoked:
            if (comp_invoker in pending_components) != (comp_invoked in pending_components):
                crossing = 1
                
        if invoker not in acc_latency:
            acc_latency[invoker] = 0
            
        new_latency = acc_latency[invoker] + edge_latency + (crossing * l_extra)
        
        if invoked not in acc_latency:
            acc_latency[invoked] = new_latency
        else:
            acc_latency[invoked] = max(acc_latency[invoked], new_latency)
            
    return max(acc_latency.values()) if acc_latency else 0

# Funcion para calcular pesos
def calculate_score_component(component, paths_dict, component_to_paths, component_adjacency, pending_components, l_max, l_extra):
    benefit=0
    risk=0
    urgency=0
    
    affected_paths = component_to_paths.get(component, set())

    # 1. Calculamos la Urgencia usando los pre-cálculos en O(K) donde K = n_caminos
    for path_id in affected_paths:
        path = paths_dict[path_id]
        current_latency = path.get("current_total", 0)
        urgency_path = current_latency / l_max
        if urgency_path > urgency:
            urgency = urgency_path

    # 2. Riesgo y Beneficio en O(1) mirando adyacentes directos
    adj = component_adjacency.get(component)
    if not adj:
        return 0
        
    for invoked_comp in adj['invokes']:
        if invoked_comp not in pending_components:
             benefit += l_extra
        else:
             risk += l_extra
             
    for invoker_comp in adj['invoked_by']:
        if invoker_comp not in pending_components:
             benefit += l_extra
        else:
             risk += l_extra

    return (benefit*urgency)-risk

# Algoritmo principal
def get_stages(c_min, c_max, l_max, l_extra, pending_components, paths_dict, component_to_paths, component_adjacency, method_to_component):
    stages = []
    
    # Store the evolution of the maximum critical path latency
    critical_paths_latency = []
    
    # Total de componentes para calcular el progreso
    total_components = len(pending_components)
    
    # 1. Utilizamos Set para O(1) lookups
    components_on_prem = set(pending_components)
    
    # 2. Caché de puntuaciones
    score_cache = {}

    def commit_migration(component, current_stage, components_on_prem_set):
        current_stage.append(component)
        components_on_prem_set.remove(component)
        
        affected_paths = component_to_paths.get(component, set())
        
        for path_id in affected_paths:
            paths_dict[path_id]["current_total"] = calculate_path_latency(paths_dict[path_id], components_on_prem_set, method_to_component, l_extra)
            
            for invoker, invoked in paths_dict[path_id]['edges']:
                c_inv = method_to_component.get(invoker)
                c_invd = method_to_component.get(invoked)
                if c_inv: score_cache.pop(c_inv, None)
                if c_invd: score_cache.pop(c_invd, None)
                    
        score_cache.pop(component, None)
        adj = component_adjacency.get(component, {})
        for comp in adj['invokes'].union(adj['invoked_by']):
             score_cache.pop(comp, None)

    # Registro de la latencia máxima inicial
    initial_max_latency = max((path_info.get("current_total", 0) for path_info in paths_dict.values()), default=0)
    if hasattr(initial_max_latency, 'item'):
        initial_max_latency = initial_max_latency.item()
        
    if initial_max_latency > l_max:
        raise ValueError(f"La latencia máxima inicial de la arquitectura ({initial_max_latency}ms) supera el límite de seguridad l_max ({l_max}ms). La migración es inviable desde el origen.")

    critical_paths_latency.append(initial_max_latency)

    while components_on_prem:
        current_stage = []
        blocked_components = set()
        
        # En cada nueva etapa se puede intentar migrar los bloqueados nuevamente
        candidates_pool = components_on_prem.copy()
        
        while len(current_stage) < c_max and candidates_pool:
            
            # Recalculamos score solo de afectados, o por primera vez
            best_component = None
            best_score = -float('inf')
            
            for component in candidates_pool:
                if component not in score_cache:
                     score_cache[component] = calculate_score_component(
                         component, paths_dict, component_to_paths, component_adjacency, components_on_prem, l_max, l_extra
                     )
                
                score = score_cache[component]
                if score > best_score:
                    best_score = score
                    best_component = component
            
            if not best_component:
                break

            # 2. SIMULACIÓN DE SEGURIDAD ANTES DE MIGRAR
            is_secure = True
            
            # Precalculo los boundaries "como si se hubiera migrado" 1 sola vez por path afectado
            affected_paths = component_to_paths.get(best_component, set())
            
            simulated_components = components_on_prem.copy()
            simulated_components.remove(best_component)
            
            for path_id in affected_paths:
                # O(N) simulación solo en los caminos afectados por este componente
                new_latency = calculate_path_latency(paths_dict[path_id], simulated_components, method_to_component, l_extra)
                
                # 3. Validación contra el umbral [2]
                if new_latency > l_max:
                    is_secure = False
                    break
                    
            # 4. Decisión final para la etapa
            if is_secure:
                commit_migration(best_component, current_stage, components_on_prem)
                candidates_pool.remove(best_component)
            else:
                blocked_components.add(best_component)
                candidates_pool.remove(best_component)
        
        # Fin de la etapa
        if len(current_stage) >= c_min:
            stages.append(current_stage)
        else:
            # Fallback de emergencia: en lugar de enviar solo 1, 
            # forzamos tantos componentes aislados/bloqueados como permita c_max
            # para no estar creando miles de etapas de 1 solo elemento.
            elementos_agregados = 0
            
            # Ordenar bloqueados por score para tomar los mejores primero
            bloqueados_ordenados = sorted(
                list(blocked_components), 
                key=lambda c: score_cache.get(c, -float('inf')), 
                reverse=True
            )
            
            for bloqueado in bloqueados_ordenados:
                if bloqueado in components_on_prem:
                    commit_migration(bloqueado, current_stage, components_on_prem)
                    elementos_agregados += 1
                if len(current_stage) >= c_max:
                    break
                    
            if elementos_agregados > 0:
                stages.append(current_stage)
            else:
                break
                
        # Guardar latencia máxima después de esta etapa
        current_max_latency = max((path_info.get("current_total", 0) for path_info in paths_dict.values()), default=0)
        if hasattr(current_max_latency, 'item'):
            current_max_latency = current_max_latency.item()
        critical_paths_latency.append(current_max_latency)
        
        # Guardar la evolucion por path
        stage_number = len(stages)
        for path_id, path_info in paths_dict.items():
            if 'evolucion_por_etapa' not in path_info:
                path_info['evolucion_por_etapa'] = []
            path_info['evolucion_por_etapa'].append({
                "stage_number": stage_number,
                "critical_time": float(path_info.get("current_total", 0)),
                "migrated_components": current_stage.copy()
            })
                
        # Imprimir porcentaje de la migracion
        migrated_components = total_components - len(components_on_prem)
        percentage = (migrated_components / total_components) * 100 if total_components > 0 else 0
        #print(f"Etapa calculada. Progreso de migración: {migrated_components}/{total_components} ({percentage:.2f}%)")
            
    return stages, critical_paths_latency


def setup(edges_path, nodes_path, paths_path, l_extra):
    edges_df, nodes_df, paths_df=import_jsons(edges_path, nodes_path, paths_path)
    edges_dict=process_edges(edges_df)
    nodes_dict=process_nodes(nodes_df)
    method_to_component=process_methods(nodes_df)
    pending_components=process_pending_components(nodes_dict)
    paths_dict=process_paths(paths_df, pending_components, method_to_component, edges_dict, l_extra)
    component_to_paths, component_adjacency = process_components(nodes_df, paths_dict, method_to_component)
    
    return edges_dict, nodes_dict, paths_dict, method_to_component, component_to_paths, component_adjacency, pending_components

def generate_migration_plan(
            ruta_nodos,
            ruta_aristas,
            ruta_paths,
            c_min,
            c_max,
            l_max,
            l_extra
        ):
    edges_dict, nodes_dict, paths_dict, method_to_component, component_to_paths, component_adjacency, pending_components=setup(ruta_aristas, ruta_nodos, ruta_paths, l_extra)
    logger.info("Iniciando algoritmo")
    stages, critical_paths_latency = get_stages(c_min, c_max, l_max, l_extra, pending_components, paths_dict, component_to_paths, component_adjacency, method_to_component)
    logger.info("Algoritmo finalizado")
    etapas_output = []
    for i, current_stage in enumerate(stages):
        etapas_output.append({
            "stage_number": i + 1,
            "migrated_components": current_stage,
            "worst_critical_time": float(critical_paths_latency[i + 1] if i + 1 < len(critical_paths_latency) else 0)
        })
        
    rutas_criticas_output = []
    for path_id, path_info in paths_dict.items():
        path_num = int(path_id.split('_')[1]) if '_' in path_id else path_id
        
        nodos_list = []
        for invoker, invoked in path_info['edges']:
            invoker_comp = method_to_component.get(invoker, str(invoker))
            invoked_comp = method_to_component.get(invoked, str(invoked))
            if not nodos_list:
                nodos_list.append(invoker_comp)
            elif nodos_list[-1] != invoker_comp:
                nodos_list.append(invoker_comp)
            if nodos_list[-1] != invoked_comp:
                nodos_list.append(invoked_comp)
                
        aristas_list = []
        for invoker, invoked, base_lat in path_info['edges_data']:
            aristas_list.append({
                "invoker": method_to_component.get(invoker, str(invoker)),
                "invoked": method_to_component.get(invoked, str(invoked)),
                "base_latency": float(base_lat)
            })
            
        rutas_criticas_output.append({
            "path_number": path_num,
            "nodos": nodos_list,
            "aristas": aristas_list,
            "evolucion_por_etapa": path_info.get('evolucion_por_etapa', [])
        })

    return {
        "etapas": etapas_output,
        "rutas_criticas": rutas_criticas_output
    }
    

if __name__ == "__main__":
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    edges_path = os.path.join(base_dir, "edges.csv")
    nodes_path = os.path.join(base_dir, "nodes.csv")
    paths_path = os.path.join(base_dir, "paths.csv")

    # Valores por defecto para ejecución manual
    c_min = 1
    c_max = 5
    l_max = 150
    l_extra = 30

    output = generate_migration_plan(nodes_path, edges_path, paths_path, c_min, c_max, l_max, l_extra)

    print(f"\nGeneración finalizada: {len(output['etapas'])} etapas de migración.")

    output_path = "stages_output.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=4)
    print(f"El resultado de las etapas ha sido exportado exitosamente a: {output_path}")