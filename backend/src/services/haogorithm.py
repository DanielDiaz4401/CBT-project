

"""Motor de migración basado en Paths Reales.

Pipeline:
  1. Parsing CSVs -> nodos, aristas, caminos críticos reales (paths.csv).
  2. Sanitización: avg_time negativo -> abs(); NaN -> drop.
  3. Winsorización de edges por cap_percentil.
  4. Si no se proporcionan, derivar l_max / l_extra de los percentiles de los datos.
  5. Precalcular viabilidad (latencia si todo cloud vs l_cap).
  6. Greedy por etapas con scoring basado en slack de paths críticos reales,
     eliminación de fronteras y c_max adaptativo según umbral.

La función pública `generar_plan_migracion` mantiene la misma interfaz que antes
pero ahora acepta `ruta_paths` y utiliza los caminos reales del sistema como
fuente de verdad para la latencia.
"""

import ast
import logging
import os
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CARGA Y SANITIZACIÓN
# ═══════════════════════════════════════════════════════════════════════════════

def _cargar_csv(
    ruta_nodos: str,
    ruta_aristas: str,
    cap_percentil: float = 95.0,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    nodes_df = pd.read_csv(ruta_nodos, usecols=["node", "architecture", "component"])
    edges_df = pd.read_csv(ruta_aristas, usecols=["invoker", "invoked", "avg_time"])

    # Sanitización de latencias negativas
    mask_neg = edges_df["avg_time"] < 0
    n_negativos = int(mask_neg.sum())
    if n_negativos > 0:
        logger.warning(
            "[Sanitización] %d aristas con avg_time negativo → abs().",
            n_negativos,
        )
        edges_df.loc[mask_neg, "avg_time"] = edges_df.loc[mask_neg, "avg_time"].abs()

    # Eliminar filas con avg_time NaN — no podemos usarlas
    n_nan = int(edges_df["avg_time"].isna().sum())
    if n_nan > 0:
        logger.warning(
            "[Sanitización] %d aristas con avg_time NaN → eliminadas.",
            n_nan,
        )
        edges_df = edges_df.dropna(subset=["avg_time"])

    # Winsorización al percentil indicado
    cap_val = float(edges_df["avg_time"].quantile(cap_percentil / 100))
    mask_out = edges_df["avg_time"] > cap_val
    n_out = int(mask_out.sum())
    if n_out > 0:
        logger.warning(
            "[Outliers] %d aristas (%.1f%%) superan P%.0f (%.2f ms) → capadas.",
            n_out,
            100.0 * n_out / len(edges_df),
            cap_percentil,
            cap_val,
        )
        edges_df.loc[mask_out, "avg_time"] = cap_val

    return nodes_df, edges_df


def _parse_path(path_str: str) -> List[Tuple[int, int]]:
    """Limpia un path: elimina (-1,-1) y duplicados consecutivos."""
    try:
        raw_tuples = ast.literal_eval(path_str)
    except (ValueError, SyntaxError):
        return []

    cleaned_path: List[Tuple[int, int]] = []
    seen: Set[Tuple[int, int]] = set()

    for invoker, invoked in raw_tuples:
        if invoker == -1 or invoked == -1:
            continue
        current_tuple = (invoker, invoked)
        if current_tuple in seen:
            continue
        seen.add(current_tuple)
        cleaned_path.append(current_tuple)

    return cleaned_path


def _process_edges(edges_df: pd.DataFrame) -> Dict[Tuple[int, int], float]:
    """Dict (invoker, invoked) -> avg_time."""
    edges_dict: Dict[Tuple[int, int], float] = {}
    for _, row in edges_df.iterrows():
        edges_dict[(int(row["invoker"]), int(row["invoked"]))] = float(row["avg_time"])
    return edges_dict


def _process_methods(nodes_df: pd.DataFrame) -> Dict[int, str]:
    return dict(zip(nodes_df["node"].astype(int), nodes_df["component"].astype(str)))


def _process_paths(
    paths_df: pd.DataFrame,
    edges_dict: Dict[Tuple[int, int], float],
    l_extra: float,
    method_to_component: Dict[int, str],
    pending_components: Set[str],
) -> Dict[str, dict]:
    """Genera paths_dict con latencias reales iniciales."""
    paths_dict: Dict[str, dict] = {}
    seen_paths: Set[tuple] = set()

    for index, row in paths_df.iterrows():
        cleaned_edges = _parse_path(row["full_path"])
        if not cleaned_edges:
            continue
        key = tuple(cleaned_edges)
        if key in seen_paths:
            continue
        seen_paths.add(key)

        edges_data = [
            (invoker, invoked, edges_dict.get((invoker, invoked), 0.0))
            for invoker, invoked in cleaned_edges
        ]

        path_id = f"path_{index}"
        paths_dict[path_id] = {
            "edges": cleaned_edges,
            "edges_data": edges_data,
        }

    # Calcular latencias iniciales con el estado cloud actual
    for path_id, path_info in paths_dict.items():
        path_info["current_total"] = _calculate_path_latency(
            path_info, pending_components, method_to_component, l_extra
        )

    logger.info("Paths únicos procesados: %d", len(paths_dict))
    return paths_dict


def _process_components(
    nodes_df: pd.DataFrame,
    paths_dict: Dict[str, dict],
    method_to_component: Dict[int, str],
) -> Tuple[Dict[str, Set[str]], Dict[str, dict]]:
    """Devuelve component_to_paths y component_adjacency."""
    component_to_paths: Dict[str, Set[str]] = {}
    component_adjacency: Dict[str, dict] = {}

    for comp in nodes_df["component"].unique():
        component_to_paths[comp] = set()
        component_adjacency[comp] = {"invokes": set(), "invoked_by": set()}

    for path_id, path_info in paths_dict.items():
        for invoker, invoked in path_info["edges"]:
            c1 = method_to_component.get(invoker)
            c2 = method_to_component.get(invoked)
            if c1:
                component_to_paths[c1].add(path_id)
            if c2:
                component_to_paths[c2].add(path_id)
            if c1 and c2 and c1 != c2:
                component_adjacency[c1]["invokes"].add(c2)
                component_adjacency[c2]["invoked_by"].add(c1)

    return component_to_paths, component_adjacency


# ═══════════════════════════════════════════════════════════════════════════════
# 2. LATENCIA REAL SOBRE PATHS
# ═══════════════════════════════════════════════════════════════════════════════

def _calculate_path_latency(
    path_info: dict,
    pending_components: Set[str],
    method_to_component: Dict[int, str],
    l_extra: float,
) -> float:
    """Latencia de un path considerando cruces de frontera on-prem/cloud."""
    acc_latency: Dict[int, float] = {}
    for invoker, invoked, edge_latency in path_info["edges_data"]:
        comp_invoker = method_to_component.get(invoker)
        comp_invoked = method_to_component.get(invoked)

        crossing = 0.0
        if comp_invoker and comp_invoked:
            if (comp_invoker in pending_components) != (comp_invoked in pending_components):
                crossing = 1.0

        if invoker not in acc_latency:
            acc_latency[invoker] = 0.0

        new_latency = acc_latency[invoker] + edge_latency + (crossing * l_extra)

        if invoked not in acc_latency:
            acc_latency[invoked] = new_latency
        else:
            acc_latency[invoked] = max(acc_latency[invoked], new_latency)

    return max(acc_latency.values()) if acc_latency else 0.0


def _recalcular_paths_afectados(
    paths_dict: Dict[str, dict],
    component_to_paths: Dict[str, Set[str]],
    components_on_prem: Set[str],
    method_to_component: Dict[int, str],
    l_extra: float,
    bloque: List[str],
) -> None:
    """Recalcula current_total de todos los paths donde aparece algún componente del bloque."""
    afectados: Set[str] = set()
    for comp in bloque:
        afectados |= component_to_paths.get(comp, set())
    for path_id in afectados:
        paths_dict[path_id]["current_total"] = _calculate_path_latency(
            paths_dict[path_id], components_on_prem, method_to_component, l_extra
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PERCENTILES PARA DEFAULTS INTELIGENTES
# ═══════════════════════════════════════════════════════════════════════════════

def _calcular_diagnostico(
    paths_dict: Dict[str, dict],
    edges_dict: Dict[Tuple[int, int], float],
    cap_percentil: float,
    l_max: float,
    l_extra: float,
    pending_components: Set[str],
    method_to_component: Dict[int, str],
) -> dict:
    """Calcula métricas del dataset para informar al cliente si sus parámetros son viables.

    Retorna un dict con:
      - latencia_base_max: latencia del peor path sin fronteras (suma pura de edges).
      - latencia_inicial: latencia máxima con el estado actual (cloud/on-prem).
      - latencia_minima_posible: latencia si todo estuviera en cloud.
      - p95_path_latency: percentil 95 de las latencias base de paths.
      - p50_edge_latency: mediana de las latencias de edges.
      - paths_sobre_l_max: cuántos paths base superan l_max.
    """
    path_latencies_base = []
    for path_info in paths_dict.values():
        lat = sum(edge_lat for _, _, edge_lat in path_info["edges_data"])
        path_latencies_base.append(lat)

    edge_latencies = list(edges_dict.values())

    if not path_latencies_base:
        path_latencies_base = [0.0]
    if not edge_latencies:
        edge_latencies = [0.0]

    p95 = float(np.nanpercentile(path_latencies_base, cap_percentil))
    p50_edge = float(np.nanpercentile(edge_latencies, 50.0))
    base_max = max(path_latencies_base)

    # Latencia inicial (estado actual)
    lat_inicial = max(
        (p["current_total"] for p in paths_dict.values()), default=0.0
    )

    # Latencia mínima posible (todo cloud)
    empty = set()
    lat_minima = max(
        (
            _calculate_path_latency(p, empty, method_to_component, l_extra)
            for p in paths_dict.values()
        ),
        default=0.0,
    )

    paths_sobre_lmax = sum(1 for lat in path_latencies_base if lat > l_max)

    diag = {
        "latencia_base_max": round(base_max, 2),
        "latencia_inicial": round(lat_inicial, 2),
        "latencia_minima_posible": round(lat_minima, 2),
        "p95_path_latency": round(p95, 2),
        "p50_edge_latency": round(p50_edge, 2),
        "paths_sobre_l_max": paths_sobre_lmax,
    }

    logger.info(
        "[Diagnóstico] l_max cliente=%.2f | l_extra cliente=%.2f | "
        "latencia_base_max=%.2f | latencia_inicial=%.2f | latencia_minima=%.2f | "
        "P95_paths=%.2f | P50_edges=%.2f | paths_que_superan_l_max=%d",
        l_max, l_extra, base_max, lat_inicial, lat_minima, p95, p50_edge, paths_sobre_lmax
    )
    return diag


# ═══════════════════════════════════════════════════════════════════════════════
# 4. SCORING BASADO EN PATHS CRÍTICOS
# ═══════════════════════════════════════════════════════════════════════════════

def _calcular_arista_roja(
    paths_dict: Dict[str, dict],
    pending_components: Set[str],
    method_to_component: Dict[int, str],
) -> Set[str]:
    """Devuelve los componentes que están en la frontera del peor path actual."""
    if not paths_dict:
        return set()

    worst_id = max(paths_dict, key=lambda p: paths_dict[p]["current_total"])
    componentes_en_arista_roja: Set[str] = set()

    for invoker, invoked in paths_dict[worst_id]["edges"]:
        c1 = method_to_component.get(invoker)
        c2 = method_to_component.get(invoked)
        if c1 and c2 and c1 != c2:
            if (c1 in pending_components) != (c2 in pending_components):
                componentes_en_arista_roja.add(c1)
                componentes_en_arista_roja.add(c2)

    return componentes_en_arista_roja


def _calculate_score_component(
    component: str,
    paths_dict: Dict[str, dict],
    component_to_paths: Dict[str, Set[str]],
    component_adjacency: Dict[str, dict],
    pending_components: Set[str],
    l_cap: float,
    l_extra: float,
    componentes_en_arista_roja: Optional[Set[str]] = None,
) -> float:
    """Score: menor slack = mayor urgencia. Mayor eliminación de cruces = mejor.
    Bonus si está en la arista roja del peor path."""
    affected_paths = component_to_paths.get(component)
    if not affected_paths:
        return -float("inf")

    # Factor 1: urgencia (menor slack = más urgente)
    min_slack = min(
        l_cap - paths_dict[p]["current_total"]
        for p in affected_paths
    )

    # Factor 2: beneficio — vecinos ya en cloud que dejarían de penalizar
    neighbors = component_adjacency[component]["invokes"] | component_adjacency[component]["invoked_by"]
    cross_elim = sum(1 for c in neighbors if c not in pending_components)

    # Factor 3: bonus arista roja
    bonus = l_extra if (componentes_en_arista_roja and component in componentes_en_arista_roja) else 0.0

    return -min_slack + cross_elim * l_extra + bonus


# ═══════════════════════════════════════════════════════════════════════════════
# 5. GREEDY POR ETAPAS CON BACKTRACKING SOBRE PATHS REALES
# ═══════════════════════════════════════════════════════════════════════════════

def _simular_bloque(
    bloque: List[str],
    components_on_prem: Set[str],
    paths_dict: Dict[str, dict],
    component_to_paths: Dict[str, Set[str]],
    method_to_component: Dict[int, str],
    l_extra: float,
) -> float:
    """Simula migrar el bloque y devuelve la latencia máxima resultante.
    Solo recalcula los paths afectados por el bloque."""
    simulated = components_on_prem - set(bloque)
    afectados: Set[str] = set()
    for comp in bloque:
        afectados |= component_to_paths.get(comp, set())

    max_lat = 0.0
    for path_id, path_info in paths_dict.items():
        if path_id in afectados:
            lat = _calculate_path_latency(path_info, simulated, method_to_component, l_extra)
        else:
            lat = path_info["current_total"]
        if lat > max_lat:
            max_lat = lat
    return max_lat


def _greedy_con_backtracking(
    pending_components: Set[str],
    paths_dict: Dict[str, dict],
    component_to_paths: Dict[str, Set[str]],
    component_adjacency: Dict[str, dict],
    method_to_component: Dict[int, str],
    c_min: int,
    c_max: int,
    l_max: float,
    l_extra: float,
    umbral: float,
) -> List[dict]:

    l_cap = l_max * (1.0 + umbral)
    total_components = len(pending_components)
    components_on_prem = set(pending_components)
    score_cache: Dict[str, float] = {}
    resultado: List[dict] = []
    etapa = 1

    # c_max adaptativo: umbral alto → podemos ser más agresivos
    c_max_adaptivo = max(c_min, min(c_max, int(round(c_max * (1.0 + umbral * 2.0)))))

    # ── Precálculo de viabilidad ──────────────────────────────────────────
    lat_all_on_prem = max(
        (p["current_total"] for p in paths_dict.values()), default=0.0
    )

    # Simular todo en cloud
    lat_all_cloud = _simular_bloque(
        list(components_on_prem), components_on_prem, paths_dict,
        component_to_paths, method_to_component, l_extra
    )

    tqdm.write(
        f"[Config]  l_max={l_max:.2f} ms  |  umbral={umbral:.2f}  |  l_cap={l_cap:.2f} ms\n"
        f"[Config]  l_extra={l_extra:.2f} ms  |  c_max_adaptivo={c_max_adaptivo}\n"
        f"[Config]  latencia inicial (todo on-prem) = {lat_all_on_prem:.2f} ms\n"
        f"[Config]  latencia mínima posible (todo cloud) = {lat_all_cloud:.2f} ms"
    )

    if lat_all_cloud > l_cap:
        tqdm.write(
            f"[AVISO]  Incluso con todo en cloud, la latencia mínima es {lat_all_cloud:.2f} ms, "
            f"que supera l_cap ({l_cap:.2f} ms). El plan tendrá etapas forzadas."
        )

    # ── Funciones auxiliares inline ───────────────────────────────────────
    def _invalidar_scores(component: str) -> None:
        a_invalidar: Set[str] = set()
        for path_id in component_to_paths.get(component, set()):
            for invoker, invoked in paths_dict[path_id]["edges"]:
                c1 = method_to_component.get(invoker)
                c2 = method_to_component.get(invoked)
                if c1 and c1 in components_on_prem:
                    a_invalidar.add(c1)
                if c2 and c2 in components_on_prem:
                    a_invalidar.add(c2)
        for c in a_invalidar:
            score_cache.pop(c, None)
        score_cache.pop(component, None)

    # ── Bucle principal ───────────────────────────────────────────────────
    with tqdm(
        total=total_components,
        desc="Planificando migración",
        unit="comp",
        dynamic_ncols=True,
    ) as pbar:
        while components_on_prem:
            # Pre-calcular arista roja (una vez por etapa)
            componentes_en_arista_roja = _calcular_arista_roja(
                paths_dict, components_on_prem, method_to_component
            )

            # Calcular/Recuperar scores
            for comp in components_on_prem:
                if comp not in score_cache:
                    score_cache[comp] = _calculate_score_component(
                        comp,
                        paths_dict,
                        component_to_paths,
                        component_adjacency,
                        components_on_prem,
                        l_cap,
                        l_extra,
                        componentes_en_arista_roja,
                    )

            # Ordenar componentes pendientes por score descendente
            ordenados = sorted(
                components_on_prem,
                key=lambda c: score_cache.get(c, -float("inf")),
                reverse=True,
            )

            # Buscar el mejor bloque válido
            mejor_bloque: Optional[List[str]] = None
            mejor_lat = float("inf")
            forzado = False

            # Rango de tamaños a probar
            max_k = min(c_max_adaptivo, len(ordenados))
            min_k = 1 if len(components_on_prem) < c_min else c_min

            # Primero buscamos uno que cumpla l_cap
            for k in range(max_k, min_k - 1, -1):
                bloque = ordenados[:k]
                lat = _simular_bloque(
                    bloque, components_on_prem, paths_dict,
                    component_to_paths, method_to_component, l_extra
                )
                if lat <= l_cap:
                    if lat < mejor_lat or (
                        lat == mejor_lat and k > (len(mejor_bloque) if mejor_bloque else 0)
                    ):
                        mejor_lat = lat
                        mejor_bloque = bloque

            # Si no encontramos nada que cumpla l_cap, tomamos el que minimice latencia
            if mejor_bloque is None:
                forzado = True
                for k in range(max_k, 0, -1):
                    bloque = ordenados[:k]
                    lat = _simular_bloque(
                        bloque, components_on_prem, paths_dict,
                        component_to_paths, method_to_component, l_extra
                    )
                    if lat < mejor_lat:
                        mejor_lat = lat
                        mejor_bloque = bloque

            # Confirmar migración
            bloque = mejor_bloque if mejor_bloque else [ordenados[0]]
            for comp in bloque:
                components_on_prem.remove(comp)

            _recalcular_paths_afectados(
                paths_dict, component_to_paths, components_on_prem,
                method_to_component, l_extra, bloque
            )
            for comp in bloque:
                _invalidar_scores(comp)

            resultado.append(
                {
                    "etapa": etapa,
                    "componentes_movidos": list(bloque),
                    "latencia_resultante": round(mejor_lat, 2),
                    "l_cap": round(l_cap, 2),
                    "forzada": forzado,
                }
            )

            # Guardar la evolucion por path
            for path_id, path_info in paths_dict.items():
                if 'evolucion_por_etapa' not in path_info:
                    path_info['evolucion_por_etapa'] = []
                path_info['evolucion_por_etapa'].append({
                    "stage_number": etapa,
                    "critical_time": float(path_info.get("current_total", 0)),
                    "migrated_components": list(bloque)
                })

            if forzado:
                tqdm.write(
                    f"[Etapa {etapa:>3}]  RED DE SEGURIDAD — forzando {len(bloque)} comp(s): {bloque}"
                )

            etapa += 1
            pbar.update(len(bloque))

            # Logging de progreso
            migrados = total_components - len(components_on_prem)
            porcentaje = (migrados / total_components) * 100 if total_components else 0
            tqdm.write(
                f"Etapa {len(resultado)}. Progreso: {migrados}/{total_components} ({porcentaje:.2f}%)"
            )

    return resultado


# ═══════════════════════════════════════════════════════════════════════════════
# 6. FUNCIÓN PÚBLICA
# ═══════════════════════════════════════════════════════════════════════════════

def generar_plan_migracion(
    ruta_nodos: str,
    ruta_aristas: str,
    ruta_paths: Optional[str] = None,
    c_min: int = 1,
    c_max: int = 5,
    l_max: Optional[float] = None,
    l_extra: Optional[float] = None,
    umbral: float = 4.0,
    cap_percentil: float = 95.0,
) -> List[dict]:
    """Punto de entrada público.

    Si `l_max` o `l_extra` son None, se derivan automáticamente de los percentiles
    de los datos usando `cap_percentil`.

    Si `ruta_paths` es None, se busca un archivo `paths.csv` en el mismo directorio
    que `ruta_nodos`.
    """
    if c_min < 1:
        raise ValueError(f"c_min debe ser al menos 1 (recibido: {c_min})")
    if c_min > c_max:
        raise ValueError(
            f"c_min no puede ser mayor que c_max (recibido: c_min={c_min}, c_max={c_max})"
        )
    if not (0.0 < cap_percentil <= 100.0):
        raise ValueError(
            f"cap_percentil debe estar en (0, 100] (recibido: {cap_percentil})"
        )

    # Autodetectar paths.csv si no se proporciona
    if ruta_paths is None:
        base_dir = os.path.dirname(os.path.abspath(ruta_nodos))
        candidato = os.path.join(base_dir, "paths.csv")
        if os.path.isfile(candidato):
            ruta_paths = candidato
        else:
            raise FileNotFoundError(
                f"No se encontró paths.csv en {base_dir}. "
                f"Proporciona `ruta_paths` explícitamente."
            )

    with tqdm(total=5, desc="Inicializando", unit="paso", dynamic_ncols=True) as pbar:
        pbar.set_description("Cargando CSVs")
        nodes_df, edges_df = _cargar_csv(ruta_nodos, ruta_aristas, cap_percentil)
        edges_dict = _process_edges(edges_df)
        pbar.update(1)

        pbar.set_description("Procesando métodos y paths")
        method_to_component = _process_methods(nodes_df)

        # Estado cloud inicial
        is_cloud = nodes_df.assign(_cloud=nodes_df["architecture"].eq("cloud"))
        cloud_state = is_cloud.groupby("component")["_cloud"].all().to_dict()
        pending_components = {c for c, cloud in cloud_state.items() if not cloud}

        paths_df = pd.read_csv(ruta_paths, usecols=["full_path"])
        # Placeholder para l_extra; recalcularemos abajo si cambia
        paths_dict = _process_paths(
            paths_df, edges_dict, 30.0, method_to_component, pending_components
        )
        pbar.update(1)

        pbar.set_description("Construyendo adyacencias")
        component_to_paths, component_adjacency = _process_components(
            nodes_df, paths_dict, method_to_component
        )
        pbar.update(1)

        pbar.set_description("Calculando diagnóstico del dataset")
        # l_max y l_extra son del cliente; si no vienen, usamos defaults fijos
        if l_max is None:
            l_max = 150.0
        if l_extra is None:
            l_extra = 30.0
        l_max = float(l_max)
        l_extra = float(l_extra)

        diagnostico = _calcular_diagnostico(
            paths_dict, edges_dict, cap_percentil, l_max, l_extra,
            pending_components, method_to_component
        )
        pbar.update(1)

        # Recalcular paths con el l_extra definitivo del cliente
        if l_extra != 30.0:
            for path_info in paths_dict.values():
                path_info["current_total"] = _calculate_path_latency(
                    path_info, pending_components, method_to_component, l_extra
                )
        pbar.update(1)

    plan = _greedy_con_backtracking(
        pending_components,
        paths_dict,
        component_to_paths,
        component_adjacency,
        method_to_component,
        c_min,
        c_max,
        float(l_max),
        float(l_extra),
        umbral,
    )
    return plan, diagnostico


def generate_migration_plan(
            ruta_nodos,
            ruta_aristas,
            ruta_paths,
            c_min,
            c_max,
            l_max,
            l_extra,
            umbral=0.0
        ):
    nodes_df, edges_df = _cargar_csv(ruta_nodos, ruta_aristas, cap_percentil=95.0)
    edges_dict = _process_edges(edges_df)
    method_to_component = _process_methods(nodes_df)

    is_cloud = nodes_df.assign(_cloud=nodes_df["architecture"].eq("cloud"))
    cloud_state = is_cloud.groupby("component")["_cloud"].all().to_dict()
    pending_components = {c for c, cloud in cloud_state.items() if not cloud}

    paths_df = pd.read_csv(ruta_paths, usecols=["full_path"])
    paths_dict = _process_paths(
        paths_df, edges_dict, float(l_extra), method_to_component, pending_components
    )

    component_to_paths, component_adjacency = _process_components(
        nodes_df, paths_dict, method_to_component
    )

    # Diagnóstico previo
    diagnostico = _calcular_diagnostico(
        paths_dict, edges_dict, 95.0, float(l_max), float(l_extra),
        pending_components, method_to_component
    )

    l_cap = float(l_max) * (1.0 + umbral)
    lat_minima = diagnostico["latencia_minima_posible"]

    if lat_minima > l_cap:
        umbral_minimo = (lat_minima / float(l_max)) - 1.0
        raise ValueError(
            f"Con l_max={l_max} y umbral={umbral}, l_cap={l_cap:.1f}ms, "
            f"pero la latencia mínima alcanzable es {lat_minima:.1f}ms. "
            f"Necesitas umbral >= {umbral_minimo:.2f} o l_max >= {lat_minima:.1f}."
        )

    plan = _greedy_con_backtracking(
        pending_components,
        paths_dict,
        component_to_paths,
        component_adjacency,
        method_to_component,
        c_min,
        c_max,
        float(l_max),
        float(l_extra),
        umbral,
    )

    etapas_forzadas = sum(1 for e in plan if e.get("forzada"))

    etapas_output = []
    for i, stage_data in enumerate(plan):
        etapas_output.append({
            "stage_number": stage_data["etapa"],
            "migrated_components": stage_data["componentes_movidos"],
            "worst_critical_time": float(stage_data["latencia_resultante"])
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

    metadatos = {
        "l_max": float(l_max),
        "l_extra": float(l_extra),
        "umbral": float(umbral),
        "l_cap_efectivo": round(l_cap, 2),
        "total_componentes": len(pending_components),
        "etapas_totales": len(plan),
        "etapas_forzadas": etapas_forzadas,
    }

    return {
        "etapas": etapas_output,
        "rutas_criticas": rutas_criticas_output,
        "diagnostico": diagnostico,
        "metadatos": metadatos
    }


if __name__ == "__main__":
    import os
    import json

    base_dir = os.path.dirname(os.path.abspath(__file__))
    edges_path = os.path.join(base_dir, "edges_with_time.csv")
    nodes_path = os.path.join(base_dir, "nodes.csv")
    paths_path = os.path.join(base_dir, "paths.csv")

    c_min = 1
    c_max = 5
    l_max = 150
    l_extra = 30
    umbral = 0.0

    output = generate_migration_plan(nodes_path, edges_path, paths_path, c_min, c_max, l_max, l_extra, umbral)

    print(f"\nGeneración finalizada: {len(output['etapas'])} etapas de migración.")

    output_path = "stages_output.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=4)
    print(f"El resultado de las etapas ha sido exportado exitosamente a: {output_path}")

