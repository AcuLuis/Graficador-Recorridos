import heapq
from collections import deque

class AlgoritmosGrafo:
    """Módulo que contiene los algoritmos puros para el visualizador de grafos."""
    
    @staticmethod
    def bfs(graph, inicio) -> dict:
        """
        Ejecuta Búsqueda en Anchura (BFS).
        Retorna un diccionario con las aristas recorridas y los pasos detallados.
        """
        content = "Pasos BFS:\n"
        aristas = []
        
        if inicio not in graph.nodes():
            return {"aristas": aristas, "content": "El nodo inicial no existe."}
            
        visited = set()
        queue = deque([(inicio, None)])
        vecinos_cargados = set([inicio])
        
        while queue:
            node, prev_node = queue.popleft()
            
            if node not in visited:
                visited.add(node)
                
            if prev_node is not None:
                tupla = (prev_node, node)
                aristas.append(tupla)
                content += f"Va de nodo {prev_node} -> nodo {node}\n"
                
            # Obtener vecinos
            neighbors = list(graph.neighbors(node))
            for neighbor in neighbors:
                if neighbor not in visited and neighbor not in vecinos_cargados:
                    vecinos_cargados.add(neighbor)
                    queue.append((neighbor, node))
                    
        return {"aristas": aristas, "content": content}

    @staticmethod
    def dfs(graph, inicio) -> dict:
        """
        Ejecuta Búsqueda en Profundidad (DFS).
        Retorna un diccionario con las aristas recorridas y los pasos detallados.
        """
        content = "Pasos DFS:\n"
        aristas = []
        
        if inicio not in graph.nodes():
            return {"aristas": aristas, "content": "El nodo inicial no existe."}
            
        visitado = set()
        
        def dfs_util(nodo):
            visitado.add(nodo)
            vecinos = list(graph.neighbors(nodo))
            for veci in vecinos:
                if veci not in visitado:
                    arista = (nodo, veci)
                    aristas.append(arista)
                    nonlocal content
                    content += f"Va de nodo {nodo} -> nodo {veci}\n"
                    dfs_util(veci)
                    
        dfs_util(inicio)
        return {"aristas": aristas, "content": content}

    @staticmethod
    def kruskal(graph) -> dict:
        """
        Ejecuta el algoritmo de Kruskal para encontrar el Árbol de Expansión Mínima.
        Retorna las aristas que componen el MST y los pasos detallados.
        """
        content = "Pasos Kruskal:\n"
        aristas_mst = []
        
        # Obtener todas las aristas y ordenarlas por peso
        edges_with_weights = []
        for u, v, data in graph.edges(data=True):
            weight = data.get('weight', 1)
            edges_with_weights.append((weight, u, v))
            
        edges_with_weights.sort()
        
        # Estructura Union-Find
        parent = {node: node for node in graph.nodes()}
        rank = {node: 0 for node in graph.nodes()}
        
        def find(node):
            if parent[node] != node:
                parent[node] = find(parent[node])
            return parent[node]
            
        def union(node1, node2):
            root1 = find(node1)
            root2 = find(node2)
            if root1 != root2:
                if rank[root1] > rank[root2]:
                    parent[root2] = root1
                elif rank[root1] < rank[root2]:
                    parent[root1] = root2
                else:
                    parent[root2] = root1
                    rank[root1] += 1
                return True
            return False
            
        # Ejecutar Kruskal
        peso_total = 0
        for weight, u, v in edges_with_weights:
            if union(u, v):
                aristas_mst.append((u, v))
                peso_total += weight
                content += f"Arista añadida: {u} -> {v} (Peso: {weight})\n"
                
        content += f"\nPeso total del MST: {peso_total}"
        return {"aristas": aristas_mst, "content": content}

    @staticmethod
    def dijkstra(graph, inicio) -> dict:
        """
        Ejecuta el algoritmo de Dijkstra para encontrar el camino más corto.
        Retorna las aristas que forman los caminos y los pasos detallados.
        """
        content = "Pasos Dijkstra:\n"
        aristas_camino = []
        
        if inicio not in graph.nodes():
            return {"aristas": aristas_camino, "content": "El nodo inicial no existe."}
            
        distancias = {node: float('inf') for node in graph.nodes()}
        distancias[inicio] = 0
        padre = {}
        visitado = set()
        
        # Cola de prioridad: (distancia, nodo)
        pq = [(0, inicio)]
        
        while pq:
            dist_actual, u = heapq.heappop(pq)
            
            if u in visitado:
                continue
                
            visitado.add(u)
            content += f"Visitando nodo {u} con distancia mínima {dist_actual}\n"
            
            for v in graph.neighbors(u):
                peso = graph.edges[u, v].get('weight', 1)
                dist_nueva = dist_actual + peso
                
                if dist_nueva < distancias[v]:
                    distancias[v] = dist_nueva
                    padre[v] = u
                    heapq.heappush(pq, (dist_nueva, v))
                    content += f"  -> Actualizando distancia a {v}: {dist_nueva}\n"
                    
        # Construir las aristas para dibujar
        for nodo_destino, nodo_origen in padre.items():
            aristas_camino.append((nodo_origen, nodo_destino))
            
        content += "\nDistancias finales desde el origen:\n"
        for nodo, dist in distancias.items():
            content += f"Nodo {nodo}: {dist if dist != float('inf') else 'Inalcanzable'}\n"
            
        return {"aristas": aristas_camino, "content": content}
