from typing import Any

import networkx as nx


def compute_stats(graph: nx.Graph) -> dict[str, Any]:
    """Métricas generales del grafo, usadas por el panel y por los reportes."""
    total_nodes = graph.number_of_nodes()
    degrees = [degree for _, degree in graph.degree()]

    stats: dict[str, Any] = {
        "directed": graph.is_directed(),
        "nodes": total_nodes,
        "edges": graph.number_of_edges(),
        "isolated": sum(1 for degree in degrees if degree == 0),
        "avg_degree": (sum(degrees) / total_nodes) if total_nodes else 0.0,
    }

    if graph.is_directed():
        stats["weak_components"] = nx.number_weakly_connected_components(graph)
        stats["strong_components"] = nx.number_strongly_connected_components(graph)
    else:
        stats["components"] = nx.number_connected_components(graph)

    return stats


def graph_type_label(graph: nx.Graph) -> str:
    return "Grafo Dirigido" if graph.is_directed() else "Grafo No Dirigido"


def format_stats(graph: nx.Graph) -> list[str]:
    stats = compute_stats(graph)
    lines = [
        f"Tipo: {graph_type_label(graph)}",
        f"Nodos: {stats['nodes']}",
        f"Aristas: {stats['edges']}",
    ]

    if stats["directed"]:
        lines.append(f"Componentes débilmente conexas: {stats['weak_components']}")
        lines.append(f"Componentes fuertemente conexas: {stats['strong_components']}")
    else:
        lines.append(f"Componentes conexas: {stats['components']}")

    lines.append(f"Nodos aislados: {stats['isolated']}")
    lines.append(f"Grado promedio: {stats['avg_degree']:.2f}")
    return lines
