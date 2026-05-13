import pandas as pd
import json
import ast
import logging
from tqdm import tqdm

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
def process_edges(edges_df, cap_percentil=95.0):
    edges_df = edges_df.copy()

    mask_neg = edges_df['avg_time'] < 0
    n_neg = int(mask_neg.sum())
    if n_neg:
        edges_df.loc[mask_neg, 'avg_time'] = edges_df.loc[mask_neg, 'avg_time'].abs()

    n_nan = int(edges_df['avg_time'].isna().sum())
    if n_nan:
        edges_df = edges_df.dropna(subset=['avg_time'])

    cap_val = float(edges_df['avg_time'].quantile(cap_percentil / 100))
    mask_out = edges_df['avg_time'] > cap_val
    n_cap = int(mask_out.sum())
    if n_cap:
        edges_df.loc[mask_out, 'avg_time'] = cap_val

    print(f"[Sanitización] negativos={n_neg}, NaN={n_nan}, "
          f"capados_P{cap_percentil:.0f}={n_cap} (cap={cap_val:.2f} ms)")

    edges_dict = {}
    for _, row in edges_df.iterrows():
        edges_dict[(row['invoker'], row['invoked'])] = row['avg_time']
    return edges_dict

# Exportar json frontend
# Formato:
# nodes_dict={
#     "C000001": {"nodes": [C000002, C123456], "migrated": true},
#     ...
# }
def process_nodes(nodes_df):
    # Components with mixed arch (e.g. C011878): force on-prem so they get migrated
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
    return nodes_dict

# Crear función auxiliar para limpiar caminos.
# Elimina tuplas (-1,-1), elimina duplicados con seen.
# Las auto-referencias (X,X) NO se eliminan: tienen avg_time real.
def parse_path(path_str):
    try:
        raw_tuples = ast.literal_eval(path_str)
    except (ValueError, SyntaxError):
        return []

    cleaned_path = []
    seen = set()

    for invoker, invoked in raw_tuples:
        if invoker == -1 or invoked == -1:
            continue

        current_tuple = (invoker, invoked)
        if current_tuple in seen:
            continue

        seen.add(current_tuple)
        cleaned_path.append(current_tuple)

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
        path_str = row['full_path']
        cleaned_edges = parse_path(path_str)

        if not cleaned_edges:
            continue

        if tuple(cleaned_edges) in seen_paths:
            continue
        seen_paths.add(tuple(cleaned_edges))

        edges_data = [(invoker, invoked, edges_dict.get((invoker, invoked), 0)) for invoker, invoked in cleaned_edges]
        paths_dict[f"path_{index}"] = {
            "edges": cleaned_edges,
            "edges_data": edges_data,
            "current_total": 0
        }

    # Calcular latencias iniciales, teniendo en cuenta que en un mismo camino pueden haber paralelismos
    for path_id, path_info in paths_dict.items():
        path_info["current_total"] = calculate_path_latency(path_info, pending_components, method_to_component, l_extra)
    #print(f"[Paths] {len(paths_dict)} paths cargados")

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
        method_to_component[row['node']] = row['component']
    return method_to_component

# Crear estructura component_to_paths
# component_to_paths = {
#     "C000001": [path_0, path_1, path_2],
#     "C000002": [path_3, path_4, path_5],
#     [...]
# }
def process_components(nodes_df, paths_dict, method_to_component):
    component_to_paths = {}
    component_adjacency = {}

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


# Calcula el componente del peor path con cruces de site activos.
# Precalculada una vez por etapa — bonus en el score del componente.
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


# Funcion para calcular pesos
# Score en ms: -min_slack (urgencia) + cross_elim*l_extra (beneficio) + bonus_arista_roja
def calculate_score_component(component, paths_dict, component_to_paths,
                               component_adjacency, pending_components,
                               l_max, l_extra, componentes_en_arista_roja=None):
    affected_paths = component_to_paths.get(component, set())
    if not affected_paths:
        return -float('inf')

    # Factor 1: urgencia — menor slack = mayor urgencia
    min_slack = min(
        l_max - paths_dict[p]["current_total"]
        for p in affected_paths
    )

    # Factor 2: beneficio — vecinos ya en cloud que dejan de penalizar
    adj = component_adjacency.get(component, {})
    neighbors = adj.get("invokes", set()).union(adj.get("invoked_by", set()))
    cross_elim = sum(1 for c in neighbors if c not in pending_components)

    # Factor 3: bonus arista roja — está en el cuello del peor camino
    bonus = l_extra if (componentes_en_arista_roja and component in componentes_en_arista_roja) else 0

    return -min_slack + cross_elim * l_extra + bonus


# Solo para visualización/output — el algoritmo siempre usa scores crudos internamente
def normalize_scores(score_cache):
    if not score_cache:
        return {}
    valores = list(score_cache.values())
    min_val = min(valores)
    max_val = max(valores)
    rango = max_val - min_val
    if rango == 0:
        return {c: 50.0 for c in score_cache}
    return {
        comp: round((score - min_val) / rango * 100, 1)
        for comp, score in score_cache.items()
    }


# Clustering Leiden a nivel de componente.
# Asigna cluster_id a cada componente para agrupar candidatos por etapa.
# resolution: solo aplica con CPM. Más alto → clusters más pequeños y numerosos.
def compute_clusters(nodes_df, edges_df, method_to_component,
                     method='cpm', resolution=10.0):
    try:
        import igraph as ig
        import leidenalg
    except ImportError:
        print("leidenalg/igraph no disponible — cada componente en su propio cluster.")
        all_components = nodes_df['component'].unique().tolist()
        return {c: i for i, c in enumerate(all_components)}

    all_components = nodes_df['component'].unique().tolist()
    comp_to_idx = {c: i for i, c in enumerate(all_components)}

    edge_weights = {}
    for _, row in edges_df.iterrows():
        avg_time = row['avg_time']
        if pd.isna(avg_time):
            continue
        comp_inv = method_to_component.get(row['invoker'])
        comp_invd = method_to_component.get(row['invoked'])
        if not comp_inv or not comp_invd or comp_inv == comp_invd:
            continue
        key = (min(comp_inv, comp_invd), max(comp_inv, comp_invd))
        edge_weights[key] = edge_weights.get(key, 0) + avg_time

    g = ig.Graph(
        n=len(all_components),
        edges=[(comp_to_idx[a], comp_to_idx[b]) for a, b in edge_weights],
        directed=False
    )
    g.es['weight'] = list(edge_weights.values())

    if method == 'cpm':
        partition = leidenalg.find_partition(
            g, leidenalg.CPMVertexPartition,
            weights='weight', resolution_parameter=resolution,
            n_iterations=10, seed=42
        )
    else:
        partition = leidenalg.find_partition(
            g, leidenalg.ModularityVertexPartition,
            weights='weight', n_iterations=10, seed=42
        )

    cluster_sizes = sorted((len(m) for m in partition), reverse=True)
    #print(f"[Leiden/{method}] {len(partition)} clusters | "
    #      f"top5={cluster_sizes[:5]} | "
    #      f"singletons={sum(1 for s in cluster_sizes if s == 1)}")

    return {all_components[node_idx]: cluster_id
            for cluster_id, members in enumerate(partition)
            for node_idx in members}


# Algoritmo principal
def get_stages(c_min, c_max, l_max_final, l_extra, pending_components, paths_dict,
               component_to_paths, component_adjacency, method_to_component,
               component_to_cluster, umbral=0.0, lista_bloqueos=None, use_score=True):
    stages = []
    forzadas = []

    critical_paths_latency = []
    total_components = len(pending_components)
    components_on_prem = set(pending_components)
    score_cache = {}

    bloqueos_dict = {}
    if lista_bloqueos:
        for b in lista_bloqueos:
            bloqueos_dict[b['component_name']] = b['stage_number']

    # Desempate determinista: mayor score primero, luego component_id ascendente.
    def _score_key(c):
        return (-score_cache.get(c, -float('inf')), c)

    def commit_migration(component, current_stage):
        current_stage.append(component)
        components_on_prem.remove(component)

        affected_paths = component_to_paths.get(component, set())
        for path_id in affected_paths:
            paths_dict[path_id]["current_total"] = calculate_path_latency(
                paths_dict[path_id], components_on_prem, method_to_component, l_extra
            )

        componentes_a_invalidar = set()
        for path_id in affected_paths:
            for invoker, invoked in paths_dict[path_id]['edges']:
                c1 = method_to_component.get(invoker)
                c2 = method_to_component.get(invoked)
                if c1 and c1 in components_on_prem:
                    componentes_a_invalidar.add(c1)
                if c2 and c2 in components_on_prem:
                    componentes_a_invalidar.add(c2)

        for c in componentes_a_invalidar:
            score_cache.pop(c, None)
        score_cache.pop(component, None)

    initial_max_latency = max((path_info.get("current_total", 0) for path_info in paths_dict.values()), default=0)
    if hasattr(initial_max_latency, 'item'):
        initial_max_latency = initial_max_latency.item()

    tqdm.write(
        f"[Config]  l_max_final={l_max_final} ms  |  umbral={umbral}  |  l_extra={l_extra} ms\n"
        f"[Config]  latencia inicial = {initial_max_latency:.2f} ms  →  objetivo = {l_max_final * (1 + umbral):.2f} ms"
    )

    critical_paths_latency.append(initial_max_latency)

    with tqdm(total=total_components, desc="Migrando", unit="comp", dynamic_ncols=True) as pbar:
        while components_on_prem:
            current_stage = []

            # l_effective: actual_max + buffer que se cierra con el progreso.
            # Buffer inicial = l_extra: absorbe una frontera nueva creada al migrar un
            # componente del camino crítico. Conforme avanza la migración, el buffer
            # tiende a 0 y l_effective converge a l_target.
            actual_max = max((p["current_total"] for p in paths_dict.values()), default=0)
            if hasattr(actual_max, 'item'):
                actual_max = actual_max.item()
            migrated = total_components - len(components_on_prem)
            progress = migrated / total_components if total_components > 0 else 0
            l_target = l_max_final * (1 + umbral)
            buffer = l_extra * (1 - progress)
            l_effective = max(l_target, actual_max + buffer)
            en_fase_forzada = l_effective > l_target

            # Paso A: precalcular arista roja (una vez por etapa)
            componentes_en_arista_roja = calcular_arista_roja(paths_dict, components_on_prem, method_to_component)

            current_stage_num = len(stages) + 1
            candidatos_posibles = []

            # Paso B: recalcular score solo de componentes no cacheados.
            # Score referenciado a l_effective: en fase forzada diferencia mejor los
            # componentes pegados al cap actual (min_slack pequeño) del resto.
            l_score_ref = l_effective
            for component in components_on_prem:
                if component in bloqueos_dict and current_stage_num <= bloqueos_dict[component]:
                    continue  # Si está bloqueado, pasamos al siguiente sin calcularle score
                
                candidatos_posibles.append(component)

                if component not in score_cache:
                    if use_score:
                        score_cache[component] = calculate_score_component(
                            component, paths_dict, component_to_paths, component_adjacency,
                            components_on_prem, l_score_ref, l_extra, componentes_en_arista_roja
                        )
                    else:
                        score_cache[component] = 0.0

            if not candidatos_posibles:
                stages.append([])
                forzadas.append(False)
                # Conservamos la latencia máxima anterior para la gráfica
                current_max_latency = max((path_info.get("current_total", 0) for path_info in paths_dict.values()), default=0)
                if hasattr(current_max_latency, 'item'): current_max_latency = current_max_latency.item()
                critical_paths_latency.append(current_max_latency)
                continue

            # Paso D: top-1 por score crudo + compañeros ordenados por score.
            # Prioriza compañeros del mismo cluster que el top-1 (afinidad estructural
            # de Leiden → menos cruces temporales intra-etapa). Si el cluster no llega
            # a c_max-1 candidatos, completa con los mejores del resto por score.
            mejor = min(candidatos_posibles, key=_score_key)
            mi_cluster = component_to_cluster.get(mejor)

            # Ordenar SOLO los que no están bloqueados por score (mejor primero) y separar por cluster.
            # Esto garantiza que dentro del cluster también elegimos los más urgentes/útiles.
            resto_ordenado = [c for c in sorted(candidatos_posibles, key=_score_key) if c != mejor]
            del_cluster = [c for c in resto_ordenado if component_to_cluster.get(c) == mi_cluster]
            fuera_cluster = [c for c in resto_ordenado if component_to_cluster.get(c) != mi_cluster]

            # Cluster primero, resto después — corta en c_max-1.
            companeros = (del_cluster + fuera_cluster)[:c_max - 1]
            candidatos_etapa = [mejor] + companeros

            # Paso E: simular por bloques primero (k descendente). Si ningún bloque
            # cumple l_effective, caer al incremental (nunca peor que antes).
            grupo_valido = []
            for k in range(len(candidatos_etapa), c_min - 1, -1):
                bloque = candidatos_etapa[:k]
                simulated = components_on_prem - set(bloque)
                paths_afectados = set().union(
                    *(component_to_paths.get(c, set()) for c in bloque)
                )
                ok = all(
                    calculate_path_latency(paths_dict[p], simulated, method_to_component, l_extra) <= l_effective
                    for p in paths_afectados
                )
                if ok:
                    grupo_valido = list(bloque)
                    break

            if not grupo_valido:
                for comp in candidatos_etapa:
                    simulated = components_on_prem - set(grupo_valido + [comp])
                    paths_afectados = component_to_paths.get(comp, set())
                    ok = all(
                        calculate_path_latency(paths_dict[p], simulated, method_to_component, l_extra) <= l_effective
                        for p in paths_afectados
                    )
                    if ok:
                        grupo_valido.append(comp)

            # Paso F: confirmar migraciones válidas
            for comp in grupo_valido:
                commit_migration(comp, current_stage)

            forzada = False
            if len(current_stage) >= c_min:
                stages.append(current_stage)
                forzadas.append(forzada)
            else:
                # Paso G: fallback seguro — simular antes de confirmar, nunca migrar a ciegas
                fallback_done = False
                for comp in sorted(candidatos_posibles, key=_score_key):
                    simulated = components_on_prem - {comp}
                    ok = all(
                        calculate_path_latency(paths_dict[p], simulated, method_to_component, l_extra) <= l_effective
                        for p in component_to_paths.get(comp, set())
                    )
                    if ok:
                        commit_migration(comp, current_stage)
                        fallback_done = True
                        forzada = True
                        break

                if fallback_done:
                    stages.append(current_stage)
                    forzadas.append(forzada)
                else:
                    break  # Ningún componente puede migrarse de forma segura

            # Guardar latencia máxima después de esta etapa
            current_max_latency = max((path_info.get("current_total", 0) for path_info in paths_dict.values()), default=0)
            if hasattr(current_max_latency, 'item'):
                current_max_latency = current_max_latency.item()
            critical_paths_latency.append(current_max_latency)

            # Guardar la evolución por path (consumido por generate_migration_plan)
            stage_number = len(stages)
            for path_info in paths_dict.values():
                if 'evolucion_por_etapa' not in path_info:
                    path_info['evolucion_por_etapa'] = []
                path_info['evolucion_por_etapa'].append({
                    "stage_number": stage_number,
                    "critical_time": float(path_info.get("current_total", 0)),
                    "migrated_components": current_stage.copy()
                })

            migrated_components = total_components - len(components_on_prem)
            pbar.update(len(current_stage))
            flag = " [FALLBACK]" if forzada else ""
            fase = "FORZ" if en_fase_forzada else "OK"
            tqdm.write(
                f"  Etapa {len(stages):>3}{flag}  |  [{fase}]  "
                f"{len(current_stage)} comp(s): {current_stage}  |  "
                f"lat: {current_max_latency:.1f} ms  |  "
                f"l_eff: {l_effective:.1f} ms  |  "
                f"{migrated_components}/{total_components} migrados"
            )

    return stages, critical_paths_latency, forzadas


def setup(edges_path, nodes_path, paths_path, l_extra):
    edges_df, nodes_df, paths_df = import_jsons(edges_path, nodes_path, paths_path)
    edges_dict = process_edges(edges_df)
    nodes_dict = process_nodes(nodes_df)
    method_to_component = process_methods(nodes_df)
    pending_components = process_pending_components(nodes_dict)
    paths_dict = process_paths(paths_df, pending_components, method_to_component, edges_dict, l_extra)
    component_to_paths, component_adjacency = process_components(nodes_df, paths_dict, method_to_component)
    component_to_cluster = compute_clusters(nodes_df, edges_df, method_to_component)

    return edges_dict, nodes_dict, paths_dict, method_to_component, component_to_paths, component_adjacency, pending_components, component_to_cluster


def generate_migration_plan(
            ruta_nodos,
            ruta_aristas,
            ruta_paths,
            c_min,
            c_max,
            l_max,
            l_extra,
            umbral,
            lista_bloqueos
        ):
    edges_dict, nodes_dict, paths_dict, method_to_component, component_to_paths, component_adjacency, pending_components, component_to_cluster = setup(
        ruta_aristas, ruta_nodos, ruta_paths, l_extra
    )
    logger.info("Iniciando algoritmo")
    stages, critical_paths_latency, forzadas = get_stages(
        c_min, c_max, l_max, l_extra,
        pending_components, paths_dict,
        component_to_paths, component_adjacency, method_to_component,
        component_to_cluster, umbral, lista_bloqueos
    )
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
        "rutas_criticas": rutas_criticas_output,
        "meets_requirements": not any(forzadas)
    }


if __name__ == "__main__":
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    edges_path = os.path.join(base_dir, "edges_with_time.csv")
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

