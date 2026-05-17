import networkx as nx

def evaluar_migracion(nodo, G_crit, estado, l_extra):
    estado_sim = {**estado, nodo: 'cloud'}
    delta = 0
    for v in G_crit.neighbors(nodo):
        antes = l_extra if estado.get(nodo, 'on-prem') != estado.get(v, 'on-prem') else 0
        despues = l_extra if estado_sim.get(nodo, 'on-prem') != estado_sim.get(v, 'on-prem') else 0
        delta += despues - antes
    for v in G_crit.predecessors(nodo):
        antes = l_extra if estado.get(v, 'on-prem') != estado.get(nodo, 'on-prem') else 0
        despues = l_extra if estado_sim.get(v, 'on-prem') != estado_sim.get(nodo, 'on-prem') else 0
        delta += despues - antes
    return delta <= 0, delta

def _seleccionar_validos(G, G_crit, estado, c_min, c_max, l_extra, bloqueos_dict=None, etapa_actual=0):
    bloqueados = {c for c, e in (bloqueos_dict or {}).items() if etapa_actual < e}
    grados = dict(G_crit.degree())
    max_conn = max(grados.values()) if grados else 0

    candidatos = [n for n in G_crit.nodes() if estado.get(n) == 'on-prem' and n not in bloqueados and any(estado.get(v) == 'cloud' for v in G_crit.neighbors(n))]
    if not candidatos: candidatos = [n for n in G_crit.nodes() if estado.get(n) == 'on-prem' and n not in bloqueados and G_crit.out_degree(n) == 0]
    if not candidatos: candidatos = [n for n in G_crit.nodes() if estado.get(n) == 'on-prem' and n not in bloqueados]

    validos = []
    if candidatos:
        resultados_saltos = []
        for nodo in candidatos:
            saltos_nuevos, saltos_eliminados, extra_sandwich = 0, 0, 0
            for v in G_crit.neighbors(nodo):
                if estado.get(v) == 'on-prem':
                    saltos_nuevos += 1
                    extra_sandwich += sum(1 for vv in G_crit.neighbors(v) if vv != nodo and estado.get(vv) == 'cloud')
                else: saltos_eliminados += 1
            resultados_saltos.append((nodo, saltos_nuevos - saltos_eliminados + extra_sandwich))

        resultados_saltos_ordenados = sorted(resultados_saltos, key=lambda x: (x[1], -(grados.get(x[0], 0) / max_conn if max_conn else 0)))

        for nodo, _ in resultados_saltos_ordenados:
            pasa, _ = evaluar_migracion(nodo, G_crit, estado, l_extra)
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

def generate_migration_plan(nodes_dict, edges_dict, paths_dict, method_to_component, c_min, c_max, l_max, l_extra=30, umbral=0, lista_bloqueos=None, **kwargs):
    estado = {comp: ('cloud' if info['migrated'] else 'on-prem') for comp, info in nodes_dict.items()}

    # Reconstrucción de Grafos a nivel de Componente (Decoupled de Pandas)
    G = nx.DiGraph()
    for (u_node, v_node), avg_time in edges_dict.items():
        u_comp, v_comp = method_to_component.get(u_node), method_to_component.get(v_node)
        if u_comp and v_comp and u_comp != v_comp:
            if G.has_edge(u_comp, v_comp): 
                G[u_comp][v_comp]['avg_time'] = max(G[u_comp][v_comp]['avg_time'], avg_time)
            else: 
                G.add_edge(u_comp, v_comp, avg_time=avg_time)

    G_crit = nx.DiGraph()
    paths_info = {}

    for path_id, path_info_dict in paths_dict.items():
        edges_data_comp = []
        nodos_list = []
        for u_node, v_node in path_info_dict['edges']:
            u_comp, v_comp = method_to_component.get(u_node), method_to_component.get(v_node)
            if u_comp and v_comp and u_comp != v_comp:
                base_lat = G[u_comp][v_comp]['avg_time'] if G.has_edge(u_comp, v_comp) else edges_dict.get((u_node, v_node), 0)
                G_crit.add_edge(u_comp, v_comp, avg_time=base_lat)
                edges_data_comp.append((u_comp, v_comp, base_lat))
                
                if not nodos_list: nodos_list.append(u_comp)
                elif nodos_list[-1] != u_comp: nodos_list.append(u_comp)
                if nodos_list[-1] != v_comp: nodos_list.append(v_comp)

        paths_info[path_id] = {
            "edges": path_info_dict['edges'],
            "edges_data": edges_data_comp,
            "nodos": nodos_list,
            "aristas": [{"invoker": u, "invoked": v, "base_latency": float(l)} for u, v, l in edges_data_comp],
            "current_total": _calculate_path_latency_components(edges_data_comp, estado, l_extra),
            "evolucion_por_etapa": [],
        }

    etapa = 0
    bloqueos_dict = {b['component_name']: b['stage_number'] for b in (lista_bloqueos or [])}
    etapas_output = []
    fallback_iniciado = False

    while True:
        on_prem_actuales = {n for n, s in estado.items() if s == 'on-prem'}
        if not on_prem_actuales: break

        validos = _seleccionar_validos(G, G_crit, estado, c_min, c_max, l_extra, bloqueos_dict, etapa)
        nodos_etapa = [n for n in validos if estado.get(n) == 'on-prem']

        if not nodos_etapa:
            if not fallback_iniciado: fallback_iniciado = True
            no_bloqueados_ahora = {c for c, e in bloqueos_dict.items() if etapa < e}
            candidatos_fallback = sorted(on_prem_actuales - no_bloqueados_ahora)
            nodos_etapa = candidatos_fallback[:c_max] if candidatos_fallback else sorted(on_prem_actuales)[:c_max]

        for n in nodos_etapa: estado[n] = 'cloud'

        for p_info in paths_info.values():
            p_info["current_total"] = _calculate_path_latency_components(p_info["edges_data"], estado, l_extra)

        worst = max((p["current_total"] for p in paths_info.values()), default=0)
        etapa += 1

        etapas_output.append({"stage_number": etapa, "migrated_components": nodos_etapa, "worst_critical_time": round(worst, 3)})

        # --- CÁLCULO DE ARISTAS HÍBRIDAS (JSONB) EN TIEMPO DE ESCRITURA ---
        for p_info in paths_info.values():
            extra_edges = []
            worst_edges = []
            
            for inv, invd, base_lat in p_info["edges_data"]:
                edge_dict = {"invoker": inv, "invoked": invd, "base_latency": float(base_lat)}
                worst_edges.append(edge_dict)
                
                # Si cruzan la frontera on-prem <-> cloud, sufren l_extra
                if estado.get(inv, 'on-prem') != estado.get(invd, 'on-prem'):
                    extra_edges.append(edge_dict)

            p_info["evolucion_por_etapa"].append({
                "stage_number": etapa, 
                "critical_time": float(p_info["current_total"]), 
                "migrated_components": list(nodos_etapa),
                "worst_path_edges": worst_edges,
                "extra_latency_edges": extra_edges
            })

    rutas_criticas_output = [{"path_number": int(pid.split('_')[1]) if '_' in pid else pid, "nodos": p["nodos"], "aristas": p["aristas"], "evolucion_por_etapa": p.get("evolucion_por_etapa", [])} for pid, p in paths_info.items()]

    return {
        "etapas": etapas_output,
        "rutas_criticas": rutas_criticas_output,
        "meets_requirements": not fallback_iniciado
    }