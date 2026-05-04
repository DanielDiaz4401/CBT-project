"""Motor de migración basado en NetworkX: condensation + topological + DAG longest path.


Pipeline:
  1. Parsing CSV -> grafo dirigido de Componentes (peso = max(avg_time) entre métodos).
  2. nx.condensation para colapsar SCCs en SuperNodos -> DAG.
  3. Orden topológico + desempaquetado -> Lista Maestra de componentes on-prem.
  4. Greedy por bloques de C_MAX con backtracking sobre dag_longest_path_length.


La función pública `generar_plan_migracion` devuelve un list[dict] nativo.
"""


import logging
from collections import defaultdict
from typing import Dict, List, Tuple


import networkx as nx
import pandas as pd
from tqdm import tqdm


logger = logging.getLogger(__name__)




def _cargar_csv(ruta_nodos: str, ruta_aristas: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    nodes_df = pd.read_csv(ruta_nodos, usecols=["node", "architecture", "component"])
    edges_df = pd.read_csv(ruta_aristas, usecols=["invoker", "invoked", "avg_time"])


    # Corrección #5: Sanitización de latencias negativas
    mask_neg = edges_df["avg_time"] < 0
    n_negativos = int(mask_neg.sum())
    if n_negativos > 0:
        logger.warning(
            "[Sanitización] %d aristas con avg_time negativo detectadas. "
            "Se aplica abs() asumiendo error de captura en los logs originales.",
            n_negativos,
        )
        edges_df.loc[mask_neg, "avg_time"] = edges_df.loc[mask_neg, "avg_time"].abs()


    return nodes_df, edges_df




def _construir_grafo_componentes(
    nodes_df: pd.DataFrame, edges_df: pd.DataFrame
) -> Tuple[nx.DiGraph, Dict[str, bool]]:
    """Colapsa métodos en componentes. Peso de arista = max(avg_time) entre llamadas método→método."""
    method_to_component: Dict[int, str] = dict(zip(nodes_df["node"], nodes_df["component"]))


    # cloud_state[comp] = True sii TODOS los métodos del componente están ya en cloud.
    is_cloud = nodes_df["architecture"].eq("cloud")
    cloud_state: Dict[str, bool] = (
        nodes_df.assign(_cloud=is_cloud).groupby("component")["_cloud"].all().to_dict()
    )


    max_latency: Dict[Tuple[str, str], float] = defaultdict(float)
    for invoker, invoked, avg_time in zip(
        edges_df["invoker"].to_numpy(),
        edges_df["invoked"].to_numpy(),
        edges_df["avg_time"].to_numpy(),
    ):
        c_src = method_to_component.get(invoker)
        c_dst = method_to_component.get(invoked)
        if c_src is None or c_dst is None or c_src == c_dst:
            continue
        key = (c_src, c_dst)
        if avg_time > max_latency[key]:
            max_latency[key] = float(avg_time)


    G = nx.DiGraph()
    G.add_nodes_from(cloud_state.keys())
    for (u, v), w in max_latency.items():
        G.add_edge(u, v, base_latency=w)
    return G, cloud_state




def _condensar_y_reparchear(G_comp: nx.DiGraph) -> nx.DiGraph:
    """nx.condensation devuelve un DAG con SCCs como nodos, pero BORRA los atributos de arista.


    Parche obligatorio: tras condensar, recorremos las aristas originales de G_comp y
    re-inyectamos en cada arista del DAG condensado el `base_latency` como el máximo de
    todas las latencias entre los componentes originales que conectan ambos SuperNodos.
    """
    G_cond: nx.DiGraph = nx.condensation(G_comp)
    mapping: Dict[str, int] = G_cond.graph["mapping"]  # componente -> scc_id


    # Re-inyección de atributos perdidos por condensation
    for u, v, data in G_comp.edges(data=True):
        su, sv = mapping[u], mapping[v]
        if su == sv:
            continue
        w = data["base_latency"]
        existing = G_cond[su][sv].get("base_latency", 0.0)
        if w > existing:
            G_cond[su][sv]["base_latency"] = w


    # Aristas sin base_latency (no debería ocurrir, pero por seguridad)
    for _, _, data in G_cond.edges(data=True):
        data.setdefault("base_latency", 0.0)


    # Normalizamos 'members' a lista estable para desempaquetado determinista
    for scc_id, data in G_cond.nodes(data=True):
        data["members"] = sorted(data["members"])


    return G_cond




def _lista_maestra_topologica(
    G_cond: nx.DiGraph, cloud_state: Dict[str, bool]
) -> List[str]:
    """Orden topológico del DAG condensado -> desempaquetado plano de Componentes on-prem."""
    maestra: List[str] = []
    for scc_id in nx.topological_sort(G_cond):
        for comp in G_cond.nodes[scc_id]["members"]:
            if not cloud_state.get(comp, False):
                maestra.append(comp)
    return maestra




# ── Estructuras optimizadas para el bucle greedy ─────────────────────────────


def _preparar_estructuras_rapidas(
    G_cond: nx.DiGraph, cloud_state: Dict[str, bool]
) -> Tuple[List, List[int], Dict[str, int], List[int], List[int], List[bool]]:
    """Precomputa las estructuras de datos para el DP rápido.


    Retorna:
        adj            – lista de adyacencia: scc_id -> [(vecino, base_latency), ...]
        topo_order     – orden topológico del DAG condensado (calculado UNA sola vez)
        comp_to_scc    – componente -> scc_id
        scc_total      – número total de miembros por SCC
        scc_cloud_count– miembros cloud actuales por SCC
        scc_cloud      – scc_cloud[i] = True iff todos los miembros del SCC i son cloud
    """
    n_sccs = G_cond.number_of_nodes()


    # Orden topológico calculado una sola vez (evita re-sort en cada llamada al DP)
    topo_order: List[int] = list(nx.topological_sort(G_cond))


    # Lista de adyacencia con arrays nativos (más rápido que iterar edges de networkx)
    adj: List[List[Tuple[int, float]]] = [[] for _ in range(n_sccs)]
    for u, v, data in G_cond.edges(data=True):
        adj[u].append((v, data["base_latency"]))


    # Mapeo componente -> SCC y contadores de estado cloud por SCC
    comp_to_scc: Dict[str, int] = {}
    scc_total = [0] * n_sccs
    scc_cloud_count = [0] * n_sccs


    for scc_id, data in G_cond.nodes(data=True):
        members = data["members"]
        scc_total[scc_id] = len(members)
        scc_cloud_count[scc_id] = sum(1 for c in members if cloud_state.get(c, False))
        for comp in members:
            comp_to_scc[comp] = scc_id


    # Corrección #4: guarda explícita contra SCC vacío (scc_total==0 → False, no True)
    scc_cloud: List[bool] = [
        scc_total[i] > 0 and scc_cloud_count[i] == scc_total[i]
        for i in range(n_sccs)
    ]


    return adj, topo_order, comp_to_scc, scc_total, scc_cloud_count, scc_cloud




def _dag_longest_path_fast(
    adj: List[List[Tuple[int, float]]],
    scc_cloud: List[bool],
    l_extra: float,
    topo_order: List[int],
    n_sccs: int,
) -> float:
    """DP de camino más largo sobre el DAG usando el orden topológico precalculado.


    Complejidad O(V+E) sin el coste de nx.topological_sort en cada llamada.
    Los pesos de arista se calculan al vuelo según el estado cloud actual.
    """
    dist = [0.0] * n_sccs
    for u in topo_order:
        cloud_u = scc_cloud[u]
        d_u = dist[u]
        for v, base_lat in adj[u]:
            penal = l_extra if cloud_u != scc_cloud[v] else 0.0
            new_d = d_u + base_lat + penal
            if new_d > dist[v]:
                dist[v] = new_d
    return max(dist) if dist else 0.0




def _greedy_con_backtracking(
    lista_maestra: List[str],
    G_cond: nx.DiGraph,
    cloud_state: Dict[str, bool],
    c_min: int,
    c_max: int,
    l_max: float,
    l_extra: float,
    umbral: float = 0.0,
) -> List[dict]:
    adj, topo_order, comp_to_scc, scc_total, scc_cloud_count, scc_cloud = (
        _preparar_estructuras_rapidas(G_cond, cloud_state)
    )
    n_sccs = G_cond.number_of_nodes()


    def mark(bloque: List[str], to_cloud: bool) -> None:
        """Actualiza cloud_state y scc_cloud incrementalmente (solo SCCs afectados)."""
        delta = 1 if to_cloud else -1
        for comp in bloque:
            if cloud_state.get(comp, False) == to_cloud:
                continue
            cloud_state[comp] = to_cloud
            sid = comp_to_scc[comp]
            scc_cloud_count[sid] += delta
            # Corrección #4 aplicada también en mark: guarda contra SCC vacío
            scc_cloud[sid] = scc_total[sid] > 0 and scc_cloud_count[sid] == scc_total[sid]


    def latencia() -> float:
        return _dag_longest_path_fast(adj, scc_cloud, l_extra, topo_order, n_sccs)


    l_cap = l_max * (1 + umbral)
    tqdm.write(f"[Config]  l_max={l_max:.2f} ms  |  umbral={umbral:.2f}  |  cap={l_cap:.2f} ms")


    resultado: List[dict] = []
    etapa = 1
    n = len(lista_maestra)


    i = 0


    with tqdm(total=n, desc="Planificando migración", unit="comp", dynamic_ncols=True) as pbar:
        while i < n:
            disponibles = min(c_max, n - i)
            mejor_k = None
            mejor_lat = float("inf")
            lat_k1 = None


            for k in range(disponibles, c_min - 1, -1):
                bloque = lista_maestra[i : i + k]
                mark(bloque, True)
                lat = latencia()
                mark(bloque, False)


                if k == 1:
                    lat_k1 = lat


                if lat <= l_cap:
                    if lat < mejor_lat or (lat == mejor_lat and k > (mejor_k or 0)):
                        mejor_lat = lat
                        mejor_k = k


            if mejor_k is not None:
                bloque = lista_maestra[i : i + mejor_k]
                mark(bloque, True)
                resultado.append(
                    {
                        "etapa": etapa,
                        "componentes_movidos": list(bloque),
                        "latencia_resultante": round(mejor_lat, 2),
                        "l_cap": round(l_cap, 2),
                        "forzada": False,
                    }
                )
                i += mejor_k
                etapa += 1
                pbar.update(mejor_k)


            else:
                # Red de seguridad: ningún k cumplió el corte; forzamos 1 componente.
                bloque = [lista_maestra[i]]
                mark(bloque, True)


                if lat_k1 is None:
                    lat_k1 = latencia()


                tqdm.write(f"[Etapa {etapa:>3}]  RED DE SEGURIDAD — forzando: {bloque[0]}")
                resultado.append(
                    {
                        "etapa": etapa,
                        "componentes_movidos": bloque,
                        "latencia_resultante": round(lat_k1, 2),
                        "l_cap": round(l_cap, 2),
                        "forzada": True,
                    }
                )
                i += 1
                etapa += 1
                pbar.update(1)


    return resultado




def generar_plan_migracion(
    ruta_nodos: str,
    ruta_aristas: str,
    c_min: int = 1,
    c_max: int = 5,
    l_max: float = 150,
    l_extra: float = 30,
    umbral: float = 0.3,
) -> List[dict]:
    """Punto de entrada público. Devuelve una lista de etapas lista para el backend."""
    # Corrección #7: Validaciones Fail-Fast antes de cualquier procesamiento
    if c_min < 1:
        raise ValueError(f"c_min debe ser al menos 1 (recibido: {c_min})")
    if c_min > c_max:
        raise ValueError(f"c_min no puede ser mayor que c_max (recibido: c_min={c_min}, c_max={c_max})")


    with tqdm(total=4, desc="Inicializando", unit="paso", dynamic_ncols=True) as pbar:
        pbar.set_description("Cargando CSVs")
        nodes_df, edges_df = _cargar_csv(ruta_nodos, ruta_aristas)
        pbar.update(1)


        pbar.set_description("Construyendo grafo de componentes")
        G_comp, cloud_state = _construir_grafo_componentes(nodes_df, edges_df)
        pbar.update(1)


        pbar.set_description("Condensando SCCs")
        G_cond = _condensar_y_reparchear(G_comp)
        pbar.update(1)


        pbar.set_description("Ordenando topológicamente")
        lista_maestra = _lista_maestra_topologica(G_cond, cloud_state)
        pbar.update(1)


    return _greedy_con_backtracking(
        lista_maestra, G_cond, cloud_state, c_min, c_max, l_max, l_extra, umbral
    )




if __name__ == "__main__":
    import json
    import os


    logging.basicConfig(level=logging.WARNING)
    base = os.path.dirname(os.path.abspath(__file__))
    plan = generar_plan_migracion(
        os.path.join(base, "nodes.csv"),
        os.path.join(base, "edges.csv"),
    )
    print(f"Etapas generadas: {len(plan)}")
    print(json.dumps(plan[:5], indent=2))