"""
Network Topology
================
Manages the network graph representing VANET nodes and links.
Provides dynamic topology updates as vehicles move and connections change.
"""

import math
import networkx as nx
from typing import Dict, List, Optional, Tuple, Set


class NetworkTopology:
    """
    Network topology manager using networkx graph.

    Maintains the network graph of all VANET nodes and their
    connections, with support for dynamic updates as vehicles move.
    """

    def __init__(self, communication_range: float = 300.0):
        """
        Initialize network topology.

        Args:
            communication_range: Maximum communication range in meters.
        """
        self.graph = nx.Graph()
        self.communication_range = communication_range
        self.node_positions: Dict[str, Tuple[float, float]] = {}
        self.node_types: Dict[str, str] = {}  # node_id -> "vehicle" | "signal" | "controller"

    def add_node(self, node_id: str, position: Tuple[float, float],
                 node_type: str = "vehicle", **attributes):
        """
        Add a node to the network topology.

        Args:
            node_id: Unique node identifier.
            position: (x, y) position in meters.
            node_type: Type of node ("vehicle", "signal", "controller").
            **attributes: Additional node attributes.
        """
        self.graph.add_node(node_id, pos=position, node_type=node_type, **attributes)
        self.node_positions[node_id] = position
        self.node_types[node_id] = node_type

    def remove_node(self, node_id: str):
        """Remove a node from the topology."""
        if node_id in self.graph:
            self.graph.remove_node(node_id)
            self.node_positions.pop(node_id, None)
            self.node_types.pop(node_id, None)

    def update_node_position(self, node_id: str, new_position: Tuple[float, float]):
        """
        Update a node's position and refresh its connections.

        Args:
            node_id: Node to update.
            new_position: New (x, y) position.
        """
        if node_id in self.graph:
            self.node_positions[node_id] = new_position
            self.graph.nodes[node_id]['pos'] = new_position
            self._refresh_links_for_node(node_id)

    def _calculate_distance(self, pos1: Tuple[float, float],
                            pos2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two positions."""
        return math.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)

    def _refresh_links_for_node(self, node_id: str):
        """Refresh all links for a given node based on current positions."""
        if node_id not in self.node_positions:
            return

        pos = self.node_positions[node_id]

        # Remove existing edges for this node
        edges_to_remove = list(self.graph.edges(node_id))
        self.graph.remove_edges_from(edges_to_remove)

        # Add edges to nodes within range
        for other_id, other_pos in self.node_positions.items():
            if other_id == node_id:
                continue
            distance = self._calculate_distance(pos, other_pos)
            if distance <= self.communication_range:
                self.graph.add_edge(node_id, other_id, weight=distance)

    def refresh_all_links(self):
        """Refresh all links in the topology based on current positions."""
        # Clear all edges
        self.graph.clear_edges()

        # Rebuild edges based on distances
        node_ids = list(self.node_positions.keys())
        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                n1, n2 = node_ids[i], node_ids[j]
                distance = self._calculate_distance(
                    self.node_positions[n1], self.node_positions[n2]
                )
                if distance <= self.communication_range:
                    self.graph.add_edge(n1, n2, weight=distance)

    def get_neighbors(self, node_id: str) -> List[str]:
        """Get list of neighbor node IDs within communication range."""
        if node_id not in self.graph:
            return []
        return list(self.graph.neighbors(node_id))

    def get_distance(self, node1: str, node2: str) -> float:
        """Get distance between two nodes."""
        if node1 in self.node_positions and node2 in self.node_positions:
            return self._calculate_distance(
                self.node_positions[node1], self.node_positions[node2]
            )
        return float('inf')

    def are_connected(self, node1: str, node2: str) -> bool:
        """Check if two nodes can communicate (directly connected)."""
        return self.graph.has_edge(node1, node2)

    def is_reachable(self, source: str, destination: str) -> bool:
        """Check if destination is reachable from source via multi-hop."""
        if source not in self.graph or destination not in self.graph:
            return False
        return nx.has_path(self.graph, source, destination)

    def get_all_nodes(self) -> List[str]:
        """Get all node IDs."""
        return list(self.graph.nodes())

    def get_nodes_by_type(self, node_type: str) -> List[str]:
        """Get all node IDs of a specific type."""
        return [nid for nid, ntype in self.node_types.items() if ntype == node_type]

    def get_node_count(self) -> int:
        """Get total number of nodes."""
        return self.graph.number_of_nodes()

    def get_edge_count(self) -> int:
        """Get total number of edges."""
        return self.graph.number_of_edges()

    def get_graph(self) -> nx.Graph:
        """Get the underlying networkx graph."""
        return self.graph

    def get_density(self) -> float:
        """Get network density (ratio of actual to possible edges)."""
        n = self.get_node_count()
        if n < 2:
            return 0.0
        return nx.density(self.graph)

    def get_average_degree(self) -> float:
        """Get average node degree (average number of neighbors)."""
        if self.get_node_count() == 0:
            return 0.0
        degrees = [d for _, d in self.graph.degree()]
        return sum(degrees) / len(degrees)
