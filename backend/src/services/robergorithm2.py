import pandas as pd
import ast
import networkx as nx
import json
#from clean import procesar

# _______________ Clean _______________
def procesar(edges_with_time_file, nodes_file, paths_file, l_extra=30,
                      guardar_csv = False):
    """
    Pipeline completo de procesamiento. Devuelve dict con 4 DataFrames
    (y opcionalmente los guarda como CSV).

    Returns:
        {
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

    # ── 2. Limpiar edges + penalización cross-boundary ───────────────────────
    edges_df['avg_time'] = edges_df['avg_time'].fillna(0) # hay algunos NaN, los tratamos como 0, se podria cambiarlo por la media o algo asi
    edges_df = edges_df.loc[edges_df.groupby(['invoker', 'invoked'])['avg_time'].idxmax()]  # Se queda con el peor caso (máximo avg_time)
    edges_df = edges_df[edges_df['invoker'] != edges_df['invoked']]
    edges_df['avg_time'] = edges_df.apply(
        lambda r: r['avg_time'] + l_extra
        if nodo_arch.get(r['invoker']) != nodo_arch.get(r['invoked'])
        else r['avg_time'], axis=1
    )
    """
    1,on-prem,C000001
    2,on-prem,C000002
    3,on-prem,C000003
    ...
    es lo mismo pero limpio y poner 0 en vez de NaN, y con l_extra añadido
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
    def traducir_y_limpiar_ciclos(linea):
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
            G = nx.DiGraph()
            for o, d in tuplas_comp:
                G.add_edge(o, d)
            while not nx.is_directed_acyclic_graph(G):
                ciclo = nx.find_cycle(G, orientation='original')
                G.remove_edge(ciclo[0][0], ciclo[0][1])
            return str(list(G.edges()))
        except Exception as e:
            print(f"Error en path: {linea} → {e}")
            return str([])

    paths_comp_df = paths_df.copy()
    paths_comp_df['full_path'] = paths_comp_df['full_path'].apply(traducir_y_limpiar_ciclos)
    """
    Traduce los paths de nodos a componentes, elimina ciclos y duplicados
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


def evaluar_migracion(nodo, G_crit, estado, l_extra):

    estado_sim = {**estado, nodo: 'cloud'}
    delta = 0

    for v in G_crit.neighbors(nodo):
        antes = l_extra if estado.get(nodo) != estado.get(v) else 0
        despues = l_extra if estado_sim.get(nodo) != estado_sim.get(v) else 0
        delta += despues - antes

    # También los predecesores (DiGraph)
    for v in G_crit.predecessors(nodo):
        antes = l_extra if estado.get(v) != estado.get(nodo) else 0
        despues = l_extra if estado_sim.get(v) != estado_sim.get(nodo) else 0
        delta += despues - antes

    return delta <= 0, delta

def _seleccionar_validos(G, G_crit, estado, c_min, c_max, l_extra):
    grados = dict(G_crit.degree())
    max_conn = max(grados.values()) if grados else 0

    # Prioridad 1: nodos en G_crit con al menos un vecino cloud
    candidatos = [
        nodo for nodo in G_crit.nodes()
        if estado.get(nodo) == 'on-prem' 
        and any(estado.get(v) == 'cloud' for v in G_crit.neighbors(nodo))
    ]

    # Prioridad 2: nodos en G_crit sin vecinos cloud (atrapados)
    if not candidatos:
        candidatos = [
            nodo for nodo in G_crit.nodes()
            if estado.get(nodo) == 'on-prem'
        ]

    validos = []

    if candidatos:
        resultados_saltos = []
        for nodo in candidatos:
            saltos_nuevos = 0
            saltos_eliminados = 0
            extra_sandwich = 0

            for v in G_crit.neighbors(nodo):
                if estado.get(v) == 'on-prem':
                    saltos_nuevos += 1
                    sandwich_weight = sum(
                        1 for vv in G_crit.neighbors(v)
                        if vv != nodo and estado.get(vv) == 'cloud'
                    )
                    extra_sandwich += sandwich_weight
                else:
                    saltos_eliminados += 1

            saltos = saltos_nuevos - saltos_eliminados + extra_sandwich
            resultados_saltos.append((nodo, saltos))

        resultados_saltos_ordenados = sorted(
            resultados_saltos,
            key=lambda x: (x[1], -(grados.get(x[0], 0) / max_conn if max_conn else 0))
        )

        for nodo, _ in resultados_saltos_ordenados:
            pasa, delta = evaluar_migracion(nodo, G_crit, estado, l_extra)
            if pasa:
                validos.append(nodo)
            if len(validos) >= c_max:
                break
        
        if not validos:
            for nodo, _ in resultados_saltos_ordenados:
                validos.append(nodo)
                if len(validos) >= c_max:
                    break

    # Prioridad 3: relleno con nodos fuera de G_crit
    if len(validos) < c_max:
        ya_en_validos = set(validos)
        nodos_gcrit = set(G_crit.nodes())
        for n in G.nodes():
            if n not in nodos_gcrit and n not in ya_en_validos and estado.get(n) == 'on-prem':
                validos.append(n)
            if len(validos) >= c_max:
                break

    return validos

def generate_migration_plan(ruta_nodos, ruta_aristas, ruta_paths, c_min, c_max, l_extra=30):
    
    resultados = procesar(ruta_aristas, ruta_nodos, ruta_paths, l_extra=l_extra)
    df_nodos      = resultados['components']
    df_aristas    = resultados['edges_comp']
    df_crit_paths = resultados['paths_componentes']

    id_col = _columna_id_componente(df_nodos)
    estado = pd.Series(df_nodos['architecture'].values, index=df_nodos[id_col]).to_dict()

    crit_paths_parsed = [ast.literal_eval(p) for p in df_crit_paths['full_path']]

    G, G_crit = _build_graphs(df_aristas, df_crit_paths)

    etapa = 0
    etapas_output = []
    fallback_iniciado = False

    while True:
        on_prem_actuales = {n for n, s in estado.items() if s == 'on-prem'}
        if not on_prem_actuales:
            break

        validos = _seleccionar_validos(G, G_crit, estado, c_min, c_max, l_extra)
        nodos_etapa = [n for n in validos if estado.get(n) == 'on-prem']

        if not nodos_etapa:
            if not fallback_iniciado:
                print("NO HAY CANDIDATOS VÁLIDOS, MIGRANDO RESTANTES DIRECTAMENTE")
                fallback_iniciado = True
            nodos_etapa = sorted(on_prem_actuales)[:c_max]

        for n in nodos_etapa:
            estado[n] = 'cloud'

        worst = max(
            sum(G_crit[s][t].get('avg_time', 0) for s, t in ruta)
            for ruta in crit_paths_parsed
        )

        etapa += 1
        print(f"Etapa {etapa}: {nodos_etapa}")

        etapas_output.append({
            "stage_number": etapa,
            "migrated_components": nodos_etapa,
            "worst_critical_time": round(worst, 3)
        })

    return etapas_output


if __name__ == "__main__":
# llamada de ejemplo (sin reporte por defecto)
    etapas_output = generate_migration_plan("nodes.csv", "edges_with_time.csv", "paths.csv", 2, 5, l_extra=30) # nodos, edges, paths, c_min, c_max, l_extra
    output = {"etapas": etapas_output}
    output_path = "stages_output4.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=4)
    print(f"El resultado de las etapas ha sido exportado exitosamente a: {output_path}")


