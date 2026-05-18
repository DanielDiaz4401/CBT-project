import networkx as nx
import logging

logger = logging.getLogger(__name__)

def evaluar_migracion(nodo, G_crit, crit_paths_parsed, estado, l_extra, umbral_pct=10):
    def latencia_arista(source, target, estado_sim):
        base = G_crit[source][target].get('avg_time', 0) if G_crit.has_edge(source, target) else 0
        if estado_sim.get(source, 'on-prem') != estado_sim.get(target, 'on-prem'):
            base += l_extra
        return base

    def latencia_critica(grafo_ruta, estado_sim):
        lat_acum = {n: 0 for n in grafo_ruta.nodes()}
        for n in nx.topological_sort(grafo_ruta):
            for sucesor in grafo_ruta.successors(n):
                nueva = lat_acum[n] + latencia_arista(n, sucesor, estado_sim)
                if nueva > lat_acum[sucesor]:
                    lat_acum[sucesor] = nueva

        hojas = [n for n in grafo_ruta.nodes() if grafo_ruta.out_degree(n) == 0]
        return max((lat_acum[h] for h in hojas), default=0)

    estado_sim = {**estado, nodo: 'cloud'}
    rutas_afectadas = [grafo for grafo in crit_paths_parsed if nodo in grafo.nodes()]

    if not rutas_afectadas: return True

    for grafo_ruta in rutas_afectadas:
        antes = latencia_critica(grafo_ruta, estado)
        despues = latencia_critica(grafo_ruta, estado_sim)
        if antes > 0 and despues > antes * (1 + umbral_pct / 100): return False
        if antes == 0 and despues > 0: return False

    return True

def _seleccionar_validos(G, G_crit, crit_paths_parsed, estado, c_min, c_max, l_extra, umbral_pct=10, bloqueos_dict=None, etapa_actual=0):
    bloqueados = {c for c, e in (bloqueos_dict or {}).items() if etapa_actual < e}
    grados = dict(G_crit.degree())
    max_conn = max(grados.values()) if grados else 0

    candidatos = [n for n in G_crit.nodes() if estado.get(n) == 'on-prem' and n not in bloqueados and any(estado.get(v) == 'cloud' for v in G_crit.neighbors(n))]
    if not candidatos: candidatos = [n for n in G_crit.nodes() if estado.get(n) == 'on-prem' and n not in bloqueados and G_crit.out_degree(n) == 0]
    if not candidatos: candidatos = [n for n in G_crit.nodes() if estado.get(n) == 'on-prem' and n not in bloqueados]

    validos = []
    if candidatos:
        cloud_neighbors = {n: sum(1 for vv in G_crit.neighbors(n) if estado.get(vv) == 'cloud') for n in G_crit.nodes()}

        resultados_saltos = []
        for nodo in candidatos:
            saltos_nuevos, saltos_eliminados, extra_sandwich = 0, 0, 0
            for v in G_crit.neighbors(nodo):
                if estado.get(v) == 'on-prem':
                    saltos_nuevos += 1
                    extra_sandwich += cloud_neighbors.get(v, 0)
                else: saltos_eliminados += 1
            resultados_saltos.append((nodo, saltos_nuevos - saltos_eliminados + extra_sandwich))

        resultados_saltos_ordenados = sorted(resultados_saltos, key=lambda x: (x[1], -(grados.get(x[0], 0) / max_conn if max_conn else 0)))

        for nodo, _ in resultados_saltos_ordenados:
            pasa = evaluar_migracion(nodo, G_crit, crit_paths_parsed, estado, l_extra, umbral_pct)
            if pasa: validos.append(nodo)
            if len(validos) >= c_max: break

        if not validos:
            for nodo, _ in resultados_saltos_ordenados:
                validos.append(nodo)
                if len(validos) >= c_max: break

    if len(validos) < c_max:
        ya_en_validos = set(validos)
        nodos_gcrit = set(G_crit.nodes())
        for n in G.nodes():
            if n not in nodos_gcrit and n not in ya_en_validos and n not in bloqueados and estado.get(n) == 'on-prem':
                validos.append(n)
            if len(validos) >= c_max: break

    return validos

def _calculate_path_latency_components(edges_data, estado, l_extra):
    acc_latency = {}
    for comp_invoker, comp_invoked, base_latency in edges_data:
        crossing = l_extra if estado.get(comp_invoker, 'on-prem') != estado.get(comp_invoked, 'on-prem') else 0
        acc_latency[comp_invoker] = acc_latency.get(comp_invoker, 0)
        new_latency = acc_latency[comp_invoker] + base_latency + crossing
        acc_latency[comp_invoked] = max(acc_latency.get(comp_invoked, 0), new_latency)
    return max(acc_latency.values()) if acc_latency else 0

def get_longest_continuous_path(G_path, base_weights, estado, l_extra):
    """Extrae LA línea continua que forma el peor subcamino en tiempo O(E)"""
    if not G_path.edges(): 
        return []
        
    for u, v in G_path.edges():
        crossing = l_extra if estado.get(u, 'on-prem') != estado.get(v, 'on-prem') else 0
        G_path[u][v]['weight'] = base_weights[(u, v)] + crossing
        
    try:
        ruta_nodos = nx.dag_longest_path(G_path, weight='weight')
        linea_continua = []
        for i in range(len(ruta_nodos) - 1):
            linea_continua.append({
                "invoker": ruta_nodos[i],
                "invoked": ruta_nodos[i+1],
                "base_latency": 0.0
            })
        return linea_continua
    except Exception:
        return []

def generate_migration_plan(nodes_dict, edges_dict, paths_dict, method_to_component, c_min, c_max, l_max, l_extra=30, umbral=10, lista_bloqueos=None, **kwargs):
    logger.info("Iniciando motor matemático: Robergorithm V3")
    estado = {comp: ('cloud' if info['migrated'] else 'on-prem') for comp, info in nodes_dict.items()}

    G = nx.DiGraph()
    for (u_node, v_node), avg_time in edges_dict.items():
        u_comp, v_comp = method_to_component.get(u_node), method_to_component.get(v_node)
        if u_comp and v_comp and u_comp != v_comp:
            if G.has_edge(u_comp, v_comp): G[u_comp][v_comp]['avg_time'] = max(G[u_comp][v_comp]['avg_time'], avg_time)
            else: G.add_edge(u_comp, v_comp, avg_time=avg_time)

    G_crit = nx.DiGraph()
    crit_paths_parsed = []
    
    for path_info in paths_dict.values():
        G_ruta = nx.DiGraph()
        for u_node, v_node in path_info['edges']:
            u_comp, v_comp = method_to_component.get(u_node), method_to_component.get(v_node)
            if u_comp and v_comp and u_comp != v_comp:
                avg_time = G[u_comp][v_comp]['avg_time'] if G.has_edge(u_comp, v_comp) else edges_dict.get((u_node, v_node), 0)
                G_crit.add_edge(u_comp, v_comp, avg_time=avg_time)
                G_ruta.add_edge(u_comp, v_comp, avg_time=avg_time)
        
        if G_ruta.edges():
            while not nx.is_directed_acyclic_graph(G_ruta):
                ciclo = nx.find_cycle(G_ruta, orientation='original')
                arista = min(ciclo, key=lambda e: G_ruta[e[0]][e[1]].get('avg_time', 0))
                G_ruta.remove_edge(arista[0], arista[1])
            crit_paths_parsed.append(G_ruta)

    paths_info = {}
    logger.info("V3: Preparando subgrafos y rompiendo ciclos internos...")
    for path_id, path_info_dict in paths_dict.items():
        edges_data_comp, nodos_list = [], []
        
        G_path = nx.DiGraph()
        base_weights = {}

        for u_node, v_node in path_info_dict['edges']:
            u_comp, v_comp = method_to_component.get(u_node), method_to_component.get(v_node)
            if u_comp and v_comp and u_comp != v_comp:
                base_lat = G[u_comp][v_comp]['avg_time'] if G.has_edge(u_comp, v_comp) else edges_dict.get((u_node, v_node), 0)
                edges_data_comp.append((u_comp, v_comp, base_lat))
                
                # Setup paramétrico del subgrafo para el Front
                w = float(base_lat)
                if G_path.has_edge(u_comp, v_comp):
                    G_path[u_comp][v_comp]['weight'] = max(G_path[u_comp][v_comp]['weight'], w)
                    base_weights[(u_comp, v_comp)] = max(base_weights.get((u_comp, v_comp), 0), w)
                else:
                    G_path.add_edge(u_comp, v_comp, weight=w)
                    base_weights[(u_comp, v_comp)] = w

                if not nodos_list: nodos_list.append(u_comp)
                elif nodos_list[-1] != u_comp: nodos_list.append(u_comp)
                if nodos_list[-1] != v_comp: nodos_list.append(v_comp)

        # Rompemos bucles para este Path
        while not nx.is_directed_acyclic_graph(G_path):
            try:
                ciclo = nx.find_cycle(G_path, orientation='original')
                min_edge = min(ciclo, key=lambda e: G_path[e[0]][e[1]]['weight'])
                G_path.remove_edge(min_edge[0], min_edge[1])
            except:
                break

        paths_info[path_id] = {
            "edges": path_info_dict['edges'],
            "edges_data": edges_data_comp,
            "nodos": nodos_list,
            "aristas": [{"invoker": u, "invoked": v, "base_latency": float(l)} for u, v, l in edges_data_comp],
            "dag": G_path,
            "base_weights": base_weights,
            "current_total": _calculate_path_latency_components(edges_data_comp, estado, l_extra),
            "evolucion_por_etapa": [],
        }

    etapa = 0
    # ETAPA 0
    for path_id, p_info in paths_info.items():
        extra_edges_inicial = [e for e in p_info["aristas"] if estado.get(e["invoker"], 'on-prem') != estado.get(e["invoked"], 'on-prem')]
        p_info["evolucion_por_etapa"].append({
            "stage_number": 0,
            "critical_time": float(p_info["current_total"]),
            "migrated_components": [comp for comp, s in estado.items() if s == 'cloud'],
            "worst_path_edges": get_longest_continuous_path(p_info['dag'], p_info['base_weights'], estado, l_extra),
            "extra_latency_edges": extra_edges_inicial
        })
        
    bloqueos_dict = {b['component_name']: b['stage_number'] for b in (lista_bloqueos or [])}
    etapas_output = []
    fallback_iniciado = False

    logger.info("Comenzando iteraciones por etapas en V3...")
    while True:
        on_prem_actuales = {n for n, s in estado.items() if s == 'on-prem'}
        if not on_prem_actuales: break

        validos = _seleccionar_validos(G, G_crit, crit_paths_parsed, estado, c_min, c_max, l_extra, umbral, bloqueos_dict, etapa)
        nodos_etapa = [n for n in validos if estado.get(n) == 'on-prem']

        if not nodos_etapa:
            if not fallback_iniciado: fallback_iniciado = True
            bloqueados_ahora = {c for c, e in bloqueos_dict.items() if etapa < e}
            candidatos_fallback = sorted(on_prem_actuales - bloqueados_ahora)
            nodos_etapa = candidatos_fallback[:c_max] if candidatos_fallback else sorted(on_prem_actuales)[:c_max]

        for n in nodos_etapa: estado[n] = 'cloud'

        for p_info in paths_info.values():
            p_info["current_total"] = _calculate_path_latency_components(p_info["edges_data"], estado, l_extra)

        worst = max((p["current_total"] for p in paths_info.values()), default=0)
        etapa += 1

        etapas_output.append({"stage_number": etapa, "migrated_components": nodos_etapa, "worst_critical_time": round(worst, 3)})

        # Bucle de guardado por subgrafos (Línea roja perfecta)
        for path_id, p_info in paths_info.items():
            extra_edges = [e for e in p_info["aristas"] if estado.get(e["invoker"], 'on-prem') != estado.get(e["invoked"], 'on-prem')]

            p_info["evolucion_por_etapa"].append({
                "stage_number": etapa, 
                "critical_time": float(p_info["current_total"]), 
                "migrated_components": list(nodos_etapa),
                "worst_path_edges": get_longest_continuous_path(p_info['dag'], p_info['base_weights'], estado, l_extra), 
                "extra_latency_edges": extra_edges
            })

    rutas_criticas_output = [{"path_number": int(pid.split('_')[1]) if '_' in pid else pid, "nodos": p["nodos"], "aristas": p["aristas"], "evolucion_por_etapa": p.get("evolucion_por_etapa", [])} for pid, p in paths_info.items()]

    return {
        "etapas": etapas_output, 
        "rutas_criticas": rutas_criticas_output, 
        "meets_requirements": not fallback_iniciado
    }