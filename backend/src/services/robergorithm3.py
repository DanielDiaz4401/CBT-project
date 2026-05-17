import networkx as nx
<<<<<<< HEAD
import json
#from clean import procesar

# _______________ Clean _______________
def procesar(edges_with_time_file, nodes_file, paths_file, l_extra=30,
                      guardar_csv = False):
    """
    Pipeline completo de procesamiento. Devuelve dict con 4 DataFrames
    (y opcionalmente los guarda como CSV).

    Returns:
        {a
            'components':           DataFrame,
            'edges_paths':          DataFrame,
            'paths_componentes':    DataFrame,
            'critpath_latency':     DataFrame,
        }
    """
    import pandas as pd
    import networkx as nx
    import ast

    edges_df = pd.read_csv(edges_with_time_file)
    """
    ,invoker,invoked,avg_time
    0,194,17702,144.66666666666666
    1,195,6033,0.3526666666666667
    ...
    """
    nodes_df = pd.read_csv(nodes_file)
    """
    node,architecture,component
    1,on-prem,C000001
    2,on-prem,C000002
    3,on-prem,C000003
    ...
    """
    paths_df = pd.read_csv(paths_file)
    """
    full_path
    "[(6972, 6800), (5422, 6972),... ]"
    "[(14182, 14182), (191224, 14182) ...]"
    ...
    """

    nodo_arch = dict(zip(nodes_df['node'], nodes_df['architecture']))
    nodo_comp = dict(zip(nodes_df['node'], nodes_df['component']))
    comp_arch = dict(zip(nodes_df['component'], nodes_df['architecture']))

    # ── 2. Limpiar edges (sin penalización cross-boundary, se aplica dinámicamente) ─
    aristas_criticas = set()
    for linea in paths_df['full_path']:
        for n1, n2 in ast.literal_eval(linea):
            aristas_criticas.add((n1, n2))
    mask_criticas = edges_df.apply(lambda r: (r['invoker'], r['invoked']) in aristas_criticas, axis=1)
    media_critica = edges_df.loc[mask_criticas, 'avg_time'].mean()
    edges_df['avg_time'] = edges_df['avg_time'].fillna(media_critica)
    #edges_df['avg_time'] = edges_df['avg_time'].fillna(0) # hay algunos NaN, los tratamos como 0, se podria cambiarlo por la media o algo asi
    edges_df = edges_df.loc[edges_df.groupby(['invoker', 'invoked'])['avg_time'].idxmax()]  # Se queda con el peor caso (máximo avg_time)
    edges_df = edges_df[edges_df['invoker'] != edges_df['invoked']]
    """
    1,on-prem,C000001
    2,on-prem,C000002
    3,on-prem,C000003
    ...
    es lo mismo pero limpio y poner 0 en vez de NaN
    l_extra NO se incluye aquí, se aplica dinámicamente según estado en cada etapa
    todos los componentes
    """

    # ── 3. Limpiar paths ─────────────────────────────────────────────────────
    def limpiar_path(linea):
        linea = linea.strip().strip('"')
        tuplas = ast.literal_eval(linea)
        tuplas = [t for t in tuplas if t[0] != t[1]]
        vistas, unico = set(), []
        for t in tuplas:
            if t not in vistas:
                vistas.add(t)
                unico.append(t)
        return str(unico)

    paths_df['full_path'] = paths_df['full_path'].apply(limpiar_path)
    paths_df = paths_df.drop_duplicates(subset=['full_path'])
    """
    "[(6972, 6800), (5422, 6972),... ]"
    "[(14182, 14182), (191224, 14182) ...]"
    ...
    es lo mismo pero sin ciclos ni duplicados
    solo los criticos
    """

    # ── 4. components.csv ────────────────────────────────────────────────────
    components_df = (
        nodes_df.groupby(['component', 'architecture'])['node']
        .apply(list)
        .reset_index()
    )
    components_df.columns = ['component', 'architecture', 'nodos']
    """
    component,architecture,nodos
    C000001,on-prem,[1]
    C000002,on-prem,"[2, 48733]"
    C000003,on-prem,"[3, 48735, 140669]"
    ...
    Asi es su salida
    todos los componentes
    """

    # ── 5. Traducir edges a componentes (versión limpiada) ───────────────────
    edges_comp = edges_df.copy()
    edges_comp['invoker'] = edges_comp['invoker'].map(nodo_comp)
    edges_comp['invoked'] = edges_comp['invoked'].map(nodo_comp)
    edges_comp = edges_comp[edges_comp['invoker'] != edges_comp['invoked']]
    edges_comp = edges_comp.dropna(subset=['invoker', 'invoked'])
    edges_comp = edges_comp.loc[
        edges_comp.groupby(['invoker', 'invoked'])['avg_time'].idxmax() #me quedo con el peor caso
    ][['invoker', 'invoked', 'avg_time']].reset_index(drop=True)
    """
    invoker,invoked,avg_time
    C001726,C001720,144.67
    C001726,C004115,30.35
    C010870,C002265,80.10
    ...
    de nodos/metodos a componentes y si hay una varios a -> b, me quedo con el peor avg_time
    esto es de todos los nodos
    """
    # ── 6. paths_componentes ─────────────────────────────────────────────────
    def traducir_y_limpiar(linea):
        try:
            linea = linea.strip().strip('"')
            tuplas_nodos = ast.literal_eval(linea)
            tuplas_comp, vistas = [], set()
            for n1, n2 in tuplas_nodos:
                c1 = nodo_comp.get(n1, f"UNKNOWN_{n1}")
                c2 = nodo_comp.get(n2, f"UNKNOWN_{n2}")
                tupla = (c1, c2)
                if c1 != c2 and tupla not in vistas:
                    tuplas_comp.append(tupla)
                    vistas.add(tupla)
            return str(tuplas_comp)
        except Exception as e:
            print(f"Error en path: {linea} → {e}")
            return str([])

    paths_comp_df = paths_df.copy()
    paths_comp_df['full_path'] = paths_comp_df['full_path'].apply(traducir_y_limpiar)
    """
    Traduce los paths de nodos a componentes, elimina duplicados
    es solo criticos
    """


    # ── 7. edges_paths ───────────────────────────────────────────────────────
    todas_tuplas = []
    for path_str in paths_comp_df.iloc[:, 0]:
        todas_tuplas.extend(ast.literal_eval(path_str))

    df_tmp = pd.DataFrame(todas_tuplas, columns=['Source', 'Target'])
    edges_paths_df = (
        df_tmp[df_tmp['Source'] != df_tmp['Target']]
        .drop_duplicates()
        .reset_index(drop=True)
    )

    # Añade el avg_time de edges_comp para cada arista Source->Target.
    edges_paths_df = edges_paths_df.merge(
        edges_comp[['invoker', 'invoked', 'avg_time']].rename(
            columns={'invoker': 'Source', 'invoked': 'Target'}
        ),
        on=['Source', 'Target'],
        how='left'
    )

    """
    
    """
    # ── 9. Guardar CSVs (opcional) ───────────────────────────────────────────
    if guardar_csv:
        components_df.to_csv('components.csv', index=False)
        edges_paths_df.to_csv('edges_paths.csv', index=False)
        paths_comp_df.to_csv('paths_2_componentes.csv', index=False)

    return {
        'components':        components_df,
        #'edges_paths':       edges_paths_df,
        'edges_comp':        edges_comp, 
        'paths_componentes': paths_comp_df,
    }

"""
components.csv/components_df:
component,architecture,nodos
C000001,on-prem,[1]
C000002,on-prem,"[2, 48733]"
C000003,on-prem,"[3, 48735, 140669]"

edges_paths.csv/edges_paths_df:
Source,Target,avg_time
C001726,C001720,144.67
C001726,C004115,30.35
C001726,C003429,7.20
C001726,C002310,1.50
C001720,C003350,4.50

paths_2_componentes.csv/paths_comp_df:
full_path
"[('C001726', 'C001720'), ('C001726', 'C004115'), ('C001726', 'C003429'), ...]"
"[('C010870', 'C002265'), ('C010870', 'C002564'), ('C010870', 'C002148'), ...]"
""" 
#_________________________________________________________________________


def _columna_id_componente(df_nodos):
    if 'Id' in df_nodos.columns:
        return 'Id'
    if 'component' in df_nodos.columns:
        return 'component'
    raise KeyError("No se encontró columna de identificador de componente ('Id' o 'component').")
"""
def _build_graphs(df_aristas, df_crit_paths):
    G = nx.DiGraph()
    for _, row in df_aristas.iterrows():
        G.add_edge(row['invoker'], row['invoked'], avg_time=row['avg_time'])

    G_crit = nx.DiGraph()
    for path_str in df_crit_paths['full_path']:
        for source, target in ast.literal_eval(path_str):
            if G.has_edge(source, target):
                G_crit.add_edge(source, target, avg_time=G[source][target]['avg_time'])
            else:
                G_crit.add_edge(source, target)

    return G, G_crit
"""

def _build_graphs(df_aristas, crit_paths_parsed):
    G = nx.DiGraph()
    for _, row in df_aristas.iterrows():
        G.add_edge(row['invoker'], row['invoked'], avg_time=row['avg_time'])

    G_crit = nx.DiGraph()
    for edges in crit_paths_parsed:  # Ya está parseado
        for source, target in edges:
            if G.has_edge(source, target):
                G_crit.add_edge(source, target, avg_time=G[source][target]['avg_time'])
            else:
                G_crit.add_edge(source, target)

    return G, G_crit

def evaluar_migracion(nodo, G_crit, crit_paths_parsed, estado, l_extra, umbral_pct=10):

    def latencia_arista(source, target, estado_sim): # L_extra no esta de base
        base = G_crit[source][target].get('avg_time', 0)
        if estado_sim.get(source, 'on-prem') != estado_sim.get(target, 'on-prem'):
            base += l_extra
=======

def evaluar_migracion(nodo, G_crit, crit_paths_parsed, estado, l_extra, umbral_pct=10):
    def latencia_arista(source, target, estado_sim):
        base = G_crit[source][target].get('avg_time', 0) if G_crit.has_edge(source, target) else 0
        if estado_sim.get(source) != estado_sim.get(target): base += l_extra
>>>>>>> 4966ae3 (refactor(algorithms): standardize interfaces and remove pandas dependency from math logic)
        return base

    def latencia_critica(ruta, estado_sim):
        """Calcula la latencia del camino crítico (peor camino raíz→hoja) por topological sort."""
        G_ruta = nx.DiGraph()
        G_ruta.add_edges_from(ruta)

<<<<<<< HEAD
        # Romper ciclos, arista con menor avg_time
        while not nx.is_directed_acyclic_graph(G_ruta):
            ciclo = nx.find_cycle(G_ruta, orientation='original')
            arista = min(
                ciclo,
                key=lambda e: G_crit[e[0]][e[1]].get('avg_time', 0) if G_crit.has_edge(e[0], e[1]) else 0
            )
            G_ruta.remove_edge(arista[0], arista[1])

        # Propagar latencia acumulada máxima por orden topológico
        lat_acum = {n: 0 for n in G_ruta.nodes()}
        for n in nx.topological_sort(G_ruta):
            for sucesor in G_ruta.successors(n):
                nueva = lat_acum[n] + latencia_arista(n, sucesor, estado_sim)
                if nueva > lat_acum[sucesor]:
                    lat_acum[sucesor] = nueva

        # El camino crítico es la latencia máxima que llega a cualquier hoja
        hojas = [n for n in G_ruta.nodes() if G_ruta.out_degree(n) == 0]
        return max((lat_acum[h] for h in hojas), default=0)

    estado_sim = {**estado, nodo: 'cloud'}
    rutas = [r for r in crit_paths_parsed if nodo in {n for edge in r for n in edge}]

    if not rutas:
        return True  # fuera de paths críticos: seguro migrar

    for ruta in rutas:
        antes = latencia_critica(ruta, estado)
        despues = latencia_critica(ruta, estado_sim)
        if antes > 0 and despues > antes * (1 + umbral_pct / 100):
            return False
        if antes == 0 and despues > 0:
            return False

=======
    estado_sim = {**estado, nodo: 'cloud'}
    rutas = [ruta for ruta in crit_paths_parsed if nodo in {n for edge in ruta for n in edge}]
    if not rutas: return False

    for ruta in rutas:
        for rama in ramas_raiz_hoja(ruta):
            antes = sum(latencia_arista(s, t, estado) for s, t in rama)
            despues = sum(latencia_arista(s, t, estado_sim) for s, t in rama)
            if despues > antes * (1 + umbral_pct / 100): return False
>>>>>>> 4966ae3 (refactor(algorithms): standardize interfaces and remove pandas dependency from math logic)
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
        crossing = l_extra if estado.get(comp_invoker) != estado.get(comp_invoked) else 0
        acc_latency[comp_invoker] = acc_latency.get(comp_invoker, 0)
        new_latency = acc_latency[comp_invoker] + base_latency + crossing
        acc_latency[comp_invoked] = max(acc_latency.get(comp_invoked, 0), new_latency)
    return max(acc_latency.values()) if acc_latency else 0

def generate_migration_plan(nodes_dict, edges_dict, paths_dict, method_to_component, c_min, c_max, l_max, l_extra=30, umbral=10, lista_bloqueos=None, **kwargs):
    estado = {comp: ('cloud' if info['migrated'] else 'on-prem') for comp, info in nodes_dict.items()}

    # Reconstrucción de Grafos
    G = nx.DiGraph()
    for (u_node, v_node), avg_time in edges_dict.items():
        u_comp, v_comp = method_to_component.get(u_node), method_to_component.get(v_node)
        if u_comp and v_comp and u_comp != v_comp:
            if G.has_edge(u_comp, v_comp): G[u_comp][v_comp]['avg_time'] = max(G[u_comp][v_comp]['avg_time'], avg_time)
            else: G.add_edge(u_comp, v_comp, avg_time=avg_time)

<<<<<<< HEAD
    id_col = _columna_id_componente(df_nodos)
    estado = pd.Series(df_nodos['architecture'].values, index=df_nodos[id_col]).to_dict()

    crit_paths_parsed = [ast.literal_eval(p) for p in df_crit_paths['full_path']]

    G, G_crit = _build_graphs(df_aristas, crit_paths_parsed)

    # dani
    edge_latency_lookup = {
        (row['invoker'], row['invoked']): row['avg_time']
        for _, row in df_aristas.iterrows()
    }
=======
    G_crit = nx.DiGraph()
    crit_paths_parsed = []
    for path_info in paths_dict.values():
        comp_path = []
        for u_node, v_node in path_info['edges']:
            u_comp, v_comp = method_to_component.get(u_node), method_to_component.get(v_node)
            if u_comp and v_comp and u_comp != v_comp:
                avg_time = G[u_comp][v_comp]['avg_time'] if G.has_edge(u_comp, v_comp) else edges_dict.get((u_node, v_node), 0)
                G_crit.add_edge(u_comp, v_comp, avg_time=avg_time)
                comp_path.append((u_comp, v_comp))
        if comp_path: crit_paths_parsed.append(comp_path)
>>>>>>> 4966ae3 (refactor(algorithms): standardize interfaces and remove pandas dependency from math logic)

    paths_info = {}
    for path_id, path_info_dict in paths_dict.items():
        edges_data_comp, nodos_list = [], []
        for u_node, v_node in path_info_dict['edges']:
            u_comp, v_comp = method_to_component.get(u_node), method_to_component.get(v_node)
            if u_comp and v_comp and u_comp != v_comp:
                base_lat = G[u_comp][v_comp]['avg_time'] if G.has_edge(u_comp, v_comp) else edges_dict.get((u_node, v_node), 0)
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

        for p_info in paths_info.values():
            p_info["evolucion_por_etapa"].append({"stage_number": etapa, "critical_time": float(p_info["current_total"]), "migrated_components": list(nodos_etapa)})

    rutas_criticas_output = [{"path_number": int(pid.split('_')[1]) if '_' in pid else pid, "nodos": p["nodos"], "aristas": p["aristas"], "evolucion_por_etapa": p.get("evolucion_por_etapa", [])} for pid, p in paths_info.items()]

<<<<<<< HEAD
    return {
        "etapas": etapas_output,
        "rutas_criticas": rutas_criticas_output,
        "meets_requirements": not fallback_iniciado
    }

"""
if __name__ == "__main__":
    etapas_output = generate_migration_plan(
        ruta_nodos="nodes.csv",
        ruta_aristas="edges_with_time.csv",
        ruta_paths="paths.csv",
        c_min=2,
        c_max=5,
        l_max=150,
        l_extra=30,
        umbral=10
    )
    output_path = "stages_output5.json"
    with open(output_path, "w") as f:
        json.dump(etapas_output, f, indent=4)
    print(f"Exportado a: {output_path}")
    """
=======
    return {"etapas": etapas_output, "rutas_criticas": rutas_criticas_output, "meets_requirements": not fallback_iniciado}
>>>>>>> 4966ae3 (refactor(algorithms): standardize interfaces and remove pandas dependency from math logic)
