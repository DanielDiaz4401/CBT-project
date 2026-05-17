import logging
from tqdm import tqdm

logger = logging.getLogger(__name__)

# Funciones auxiliares
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

def calcular_arista_roja(paths_dict, pending_components, method_to_component):
    worst_id = max(paths_dict, key=lambda p: paths_dict[p]["current_total"])
    componentes_en_arista_roja = set()
    for invoker, invoked in paths_dict[worst_id]["edges"]:
        c1 = method_to_component.get(invoker)
        c2 = method_to_component.get(invoked)
        if c1 and c2 and c1 != c2:
            if (c1 in pending_components) != (c2 in pending_components):
                componentes_en_arista_roja.add(c1)
                componentes_en_arista_roja.add(c2)
    return componentes_en_arista_roja

def calculate_score_component(component, paths_dict, component_to_paths, component_adjacency, pending_components, l_max, l_extra, componentes_en_arista_roja=None):
    affected_paths = component_to_paths.get(component, set())
    if not affected_paths:
        return -float('inf')

    min_slack = min(l_max - paths_dict[p]["current_total"] for p in affected_paths)
    adj = component_adjacency.get(component, {})
    neighbors = adj.get("invokes", set()).union(adj.get("invoked_by", set()))
    cross_elim = sum(1 for c in neighbors if c not in pending_components)
    bonus = l_extra if (componentes_en_arista_roja and component in componentes_en_arista_roja) else 0

    return -min_slack + cross_elim * l_extra + bonus

def get_stages(c_min, c_max, l_max_final, l_extra, pending_components, paths_dict, component_to_paths, component_adjacency, method_to_component, component_to_cluster, umbral=0.0, lista_bloqueos=None, use_score=True):
    stages = []
    forzadas = []
    critical_paths_latency = []
    total_components = len(pending_components)
    components_on_prem = set(pending_components)
    score_cache = {}

    bloqueos_dict = {b['component_name']: b['stage_number'] for b in (lista_bloqueos or [])}

    def _score_key(c):
        return (-score_cache.get(c, -float('inf')), c)

    def commit_migration(component, current_stage):
        current_stage.append(component)
        components_on_prem.remove(component)
        affected_paths = component_to_paths.get(component, set())
        for path_id in affected_paths:
            paths_dict[path_id]["current_total"] = calculate_path_latency(paths_dict[path_id], components_on_prem, method_to_component, l_extra)
        componentes_a_invalidar = set()
        for path_id in affected_paths:
            for invoker, invoked in paths_dict[path_id]['edges']:
                c1, c2 = method_to_component.get(invoker), method_to_component.get(invoked)
                if c1 and c1 in components_on_prem: componentes_a_invalidar.add(c1)
                if c2 and c2 in components_on_prem: componentes_a_invalidar.add(c2)
        for c in componentes_a_invalidar: score_cache.pop(c, None)
        score_cache.pop(component, None)

    initial_max_latency = max((path_info.get("current_total", 0) for path_info in paths_dict.values()), default=0)
    critical_paths_latency.append(initial_max_latency)

    while components_on_prem:
        current_stage = []
        actual_max = max((p["current_total"] for p in paths_dict.values()), default=0)
        migrated = total_components - len(components_on_prem)
        progress = migrated / total_components if total_components > 0 else 0
        l_target = l_max_final * (1 + umbral)
        buffer = l_extra * (1 - progress)
        l_effective = max(l_target, actual_max + buffer)
        en_fase_forzada = l_effective > l_target

        componentes_en_arista_roja = calcular_arista_roja(paths_dict, components_on_prem, method_to_component)
        current_stage_num = len(stages) + 1
        candidatos_posibles = []

        for component in components_on_prem:
            if component in bloqueos_dict and current_stage_num <= bloqueos_dict[component]: continue
            candidatos_posibles.append(component)
            if component not in score_cache:
                score_cache[component] = calculate_score_component(component, paths_dict, component_to_paths, component_adjacency, components_on_prem, l_effective, l_extra, componentes_en_arista_roja) if use_score else 0.0

        if not candidatos_posibles:
            stages.append([])
            forzadas.append(False)
            critical_paths_latency.append(max((p.get("current_total", 0) for p in paths_dict.values()), default=0))
            continue

        mejor = min(candidatos_posibles, key=_score_key)
        mi_cluster = component_to_cluster.get(mejor)
        resto_ordenado = [c for c in sorted(candidatos_posibles, key=_score_key) if c != mejor]
        del_cluster = [c for c in resto_ordenado if component_to_cluster.get(c) == mi_cluster]
        fuera_cluster = [c for c in resto_ordenado if component_to_cluster.get(c) != mi_cluster]

        candidatos_etapa = [mejor] + (del_cluster + fuera_cluster)[:c_max - 1]
        grupo_valido = []

        for k in range(len(candidatos_etapa), c_min - 1, -1):
            bloque = candidatos_etapa[:k]
            simulated = components_on_prem - set(bloque)
            paths_afectados = set().union(*(component_to_paths.get(c, set()) for c in bloque))
            if all(calculate_path_latency(paths_dict[p], simulated, method_to_component, l_extra) <= l_effective for p in paths_afectados):
                grupo_valido = list(bloque)
                break

        if not grupo_valido:
            for comp in candidatos_etapa:
                simulated = components_on_prem - set(grupo_valido + [comp])
                paths_afectados = component_to_paths.get(comp, set())
                if all(calculate_path_latency(paths_dict[p], simulated, method_to_component, l_extra) <= l_effective for p in paths_afectados):
                    grupo_valido.append(comp)

        for comp in grupo_valido: commit_migration(comp, current_stage)

        forzada = False
        if len(current_stage) >= c_min:
            stages.append(current_stage)
            forzadas.append(forzada)
        else:
            fallback_done = False
            for comp in sorted(candidatos_posibles, key=_score_key):
                simulated = components_on_prem - {comp}
                if all(calculate_path_latency(paths_dict[p], simulated, method_to_component, l_extra) <= l_effective for p in component_to_paths.get(comp, set())):
                    commit_migration(comp, current_stage)
                    fallback_done = True
                    forzada = True
                    break
            if fallback_done:
                stages.append(current_stage)
                forzadas.append(forzada)
            else:
                break 

        current_max_latency = max((p.get("current_total", 0) for p in paths_dict.values()), default=0)
        critical_paths_latency.append(current_max_latency)

        stage_number = len(stages)
        for path_info in paths_dict.values():
            if 'evolucion_por_etapa' not in path_info: path_info['evolucion_por_etapa'] = []
            
            extra_edges = []
            worst_edges = []
            
            # Recorremos las aristas y traducimos el método -> componente
            for inv, invd, base_lat in path_info['edges_data']:
                comp_inv = method_to_component.get(inv, str(inv))
                comp_invd = method_to_component.get(invd, str(invd))
                
                edge_dict = {"invoker": comp_inv, "invoked": comp_invd, "base_latency": float(base_lat)}
                worst_edges.append(edge_dict) # Guardamos el mapa del camino
                
                # Si uno sigue on-prem y el otro ya no está (es decir, está en la nube), sufren L_extra
                if comp_inv and comp_invd:
                    if (comp_inv in components_on_prem) != (comp_invd in components_on_prem):
                        extra_edges.append(edge_dict)
            
            path_info['evolucion_por_etapa'].append({
                "stage_number": stage_number,
                "critical_time": float(path_info.get("current_total", 0)),
                "migrated_components": current_stage.copy(),
                "worst_path_edges": worst_edges,           # <-- Nueva propiedad para el JSONB
                "extra_latency_edges": extra_edges         # <-- Nueva propiedad para el JSONB
            })

    return stages, critical_paths_latency, forzadas


def generate_migration_plan(nodes_dict, edges_dict, paths_dict, method_to_component, component_to_paths, component_adjacency, pending_components, component_to_cluster, c_min, c_max, l_max, l_extra, umbral, lista_bloqueos, **kwargs):
    logger.info("Iniciando algoritmo Guangorithm")
    stages, critical_paths_latency, forzadas = get_stages(
        c_min, c_max, l_max, l_extra, pending_components, paths_dict, component_to_paths, component_adjacency, method_to_component, component_to_cluster, umbral, lista_bloqueos
    )
    logger.info("Algoritmo finalizado")

    etapas_output = [{"stage_number": i + 1, "migrated_components": current_stage, "worst_critical_time": float(critical_paths_latency[i + 1] if i + 1 < len(critical_paths_latency) else 0)} for i, current_stage in enumerate(stages)]

    rutas_criticas_output = []
    for path_id, path_info in paths_dict.items():
        path_num = int(path_id.split('_')[1]) if '_' in path_id else path_id
        nodos_list = []
        for invoker, invoked in path_info['edges']:
            invoker_comp, invoked_comp = method_to_component.get(invoker, str(invoker)), method_to_component.get(invoked, str(invoked))
            if not nodos_list: nodos_list.append(invoker_comp)
            elif nodos_list[-1] != invoker_comp: nodos_list.append(invoker_comp)
            if nodos_list[-1] != invoked_comp: nodos_list.append(invoked_comp)

        aristas_list = [{"invoker": method_to_component.get(u, str(u)), "invoked": method_to_component.get(v, str(v)), "base_latency": float(lat)} for u, v, lat in path_info['edges_data']]

        rutas_criticas_output.append({"path_number": path_num, "nodos": nodos_list, "aristas": aristas_list, "evolucion_por_etapa": path_info.get('evolucion_por_etapa', [])})

    return {"etapas": etapas_output, "rutas_criticas": rutas_criticas_output, "meets_requirements": not any(forzadas)}