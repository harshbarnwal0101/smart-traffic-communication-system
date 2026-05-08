"""
Network Router
==============
Implements Dijkstra's shortest path routing with dynamic routing
table updates, multi-hop forwarding, and broadcast support for VANET.
"""

import heapq
import logging
import time
from typing import Dict, List, Optional, Set, Tuple
from .topology import NetworkTopology
from .packet import Packet, PacketType

logger = logging.getLogger(__name__)


class Router:
    """
    Network layer router implementing Dijkstra's shortest path algorithm
    with support for multi-hop forwarding and broadcast propagation.
    """

    def __init__(self, topology: NetworkTopology):
        """
        Initialize router with network topology.

        Args:
            topology: NetworkTopology instance.
        """
        self.topology = topology
        self.routing_tables: Dict[str, Dict[str, dict]] = {}  # node_id -> {dest: {next_hop, cost, hops}}
        self.broadcast_seen: Dict[str, Set[int]] = {}  # node_id -> set of seen packet IDs

        # Metrics
        self.total_packets_routed = 0
        self.total_packets_delivered = 0
        self.total_packets_dropped = 0
        self.total_broadcasts = 0
        self.routing_updates = 0
        self.packet_history: List[dict] = []

    def compute_shortest_paths(self, source: str) -> Dict[str, dict]:
        """
        Compute shortest paths from source to all other nodes using Dijkstra's algorithm.

        Args:
            source: Source node ID.

        Returns:
            Dict mapping destination to {next_hop, cost, path, hops}.
        """
        graph = self.topology.get_graph()
        if source not in graph:
            return {}

        # Dijkstra's algorithm
        distances: Dict[str, float] = {source: 0}
        previous: Dict[str, Optional[str]] = {source: None}
        visited: Set[str] = set()
        pq = [(0, source)]

        while pq:
            dist, node = heapq.heappop(pq)

            if node in visited:
                continue
            visited.add(node)

            for neighbor in graph.neighbors(node):
                if neighbor in visited:
                    continue
                edge_weight = graph[node][neighbor].get('weight', 1.0)
                new_dist = dist + edge_weight

                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = node
                    heapq.heappush(pq, (new_dist, neighbor))

        # Build routing table entries
        routes = {}
        for dest in distances:
            if dest == source:
                continue

            # Reconstruct path
            path = []
            current = dest
            while current is not None:
                path.append(current)
                current = previous.get(current)
            path.reverse()

            # Next hop is second node in path
            next_hop = path[1] if len(path) > 1 else dest

            routes[dest] = {
                "next_hop": next_hop,
                "cost": distances[dest],
                "path": path,
                "hops": len(path) - 1,
            }

        return routes

    def update_routing_table(self, node_id: str):
        """
        Update routing table for a specific node.

        Args:
            node_id: Node ID to update routing table for.
        """
        self.routing_tables[node_id] = self.compute_shortest_paths(node_id)
        self.routing_updates += 1

    def update_all_routing_tables(self):
        """Update routing tables for all nodes in the network."""
        for node_id in self.topology.get_all_nodes():
            self.update_routing_table(node_id)

    def get_next_hop(self, source: str, destination: str) -> Optional[str]:
        """
        Get next hop for routing a packet from source to destination.

        Args:
            source: Current node ID.
            destination: Final destination node ID.

        Returns:
            Next hop node ID, or None if no route exists.
        """
        if source not in self.routing_tables:
            self.update_routing_table(source)

        routes = self.routing_tables.get(source, {})
        if destination in routes:
            return routes[destination]["next_hop"]
        return None

    def get_route(self, source: str, destination: str) -> Optional[List[str]]:
        """
        Get full route from source to destination.

        Args:
            source: Source node ID.
            destination: Destination node ID.

        Returns:
            List of node IDs forming the route, or None.
        """
        if source not in self.routing_tables:
            self.update_routing_table(source)

        routes = self.routing_tables.get(source, {})
        if destination in routes:
            return routes[destination]["path"]
        return None

    def route_packet(self, packet: Packet) -> List[dict]:
        """
        Route a packet through the network, simulating multi-hop forwarding.

        Args:
            packet: Packet to route.

        Returns:
            List of hop records [{node, action, timestamp}, ...].
        """
        self.total_packets_routed += 1
        hop_records = []

        if packet.is_broadcast():
            return self._route_broadcast(packet)

        # Unicast routing
        current_node = packet.source
        route = self.get_route(packet.source, packet.destination)

        if route is None:
            packet.mark_dropped()
            self.total_packets_dropped += 1
            hop_records.append({
                "node": current_node,
                "action": "DROP_NO_ROUTE",
                "timestamp": time.time(),
            })
            self._record_packet(packet, hop_records)
            return hop_records

        # Simulate forwarding through each hop
        for i, node_id in enumerate(route):
            if i == 0:
                hop_records.append({
                    "node": node_id,
                    "action": "ORIGINATE",
                    "timestamp": time.time(),
                })
                continue

            packet.add_hop(node_id)

            if packet.is_expired():
                packet.mark_dropped()
                self.total_packets_dropped += 1
                hop_records.append({
                    "node": node_id,
                    "action": "DROP_TTL_EXPIRED",
                    "timestamp": time.time(),
                })
                break

            if node_id == packet.destination:
                packet.mark_delivered()
                self.total_packets_delivered += 1
                hop_records.append({
                    "node": node_id,
                    "action": "DELIVER",
                    "timestamp": time.time(),
                })
            else:
                hop_records.append({
                    "node": node_id,
                    "action": "FORWARD",
                    "timestamp": time.time(),
                })

        self._record_packet(packet, hop_records)
        return hop_records

    def _route_broadcast(self, packet: Packet) -> List[dict]:
        """
        Route a broadcast packet using flooding with duplicate detection.

        Args:
            packet: Broadcast packet.

        Returns:
            List of hop records.
        """
        self.total_broadcasts += 1
        hop_records = []

        # Initialize broadcast tracking for source
        if packet.source not in self.broadcast_seen:
            self.broadcast_seen[packet.source] = set()

        # BFS-based flooding
        visited = {packet.source}
        queue = [packet.source]
        delivered_to = []

        hop_records.append({
            "node": packet.source,
            "action": "BROADCAST_ORIGINATE",
            "timestamp": time.time(),
        })

        while queue:
            current = queue.pop(0)
            neighbors = self.topology.get_neighbors(current)

            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
                    delivered_to.append(neighbor)
                    hop_records.append({
                        "node": neighbor,
                        "action": "BROADCAST_RECEIVE",
                        "timestamp": time.time(),
                        "from": current,
                    })

        packet.mark_delivered()
        packet.metadata["broadcast_reach"] = len(delivered_to)
        packet.metadata["broadcast_nodes"] = delivered_to
        self.total_packets_delivered += 1
        self._record_packet(packet, hop_records)
        return hop_records

    def _record_packet(self, packet: Packet, hop_records: List[dict]):
        """Record packet routing history for metrics."""
        self.packet_history.append({
            "packet_id": packet.packet_id,
            "type": packet.packet_type.value,
            "source": packet.source,
            "destination": packet.destination,
            "delivered": packet.delivered,
            "dropped": packet.dropped,
            "hop_count": packet.hop_count,
            "route": packet.route,
            "latency_ms": packet.get_latency(),
            "hop_records": hop_records,
        })

    def get_packet_delivery_ratio(self) -> float:
        """Calculate Packet Delivery Ratio (PDR)."""
        if self.total_packets_routed == 0:
            return 0.0
        return self.total_packets_delivered / self.total_packets_routed

    def get_average_hop_count(self) -> float:
        """Calculate average hop count for delivered packets."""
        delivered = [p for p in self.packet_history if p["delivered"]]
        if not delivered:
            return 0.0
        return sum(p["hop_count"] for p in delivered) / len(delivered)

    def get_average_latency(self) -> float:
        """Calculate average end-to-end latency in ms."""
        delivered = [p for p in self.packet_history
                     if p["delivered"] and p["latency_ms"] >= 0]
        if not delivered:
            return 0.0
        return sum(p["latency_ms"] for p in delivered) / len(delivered)

    def get_metrics(self) -> dict:
        """Get comprehensive routing metrics."""
        return {
            "total_packets_routed": self.total_packets_routed,
            "total_packets_delivered": self.total_packets_delivered,
            "total_packets_dropped": self.total_packets_dropped,
            "total_broadcasts": self.total_broadcasts,
            "packet_delivery_ratio": self.get_packet_delivery_ratio(),
            "average_hop_count": self.get_average_hop_count(),
            "average_latency_ms": self.get_average_latency(),
            "routing_table_updates": self.routing_updates,
        }

    def reset_metrics(self):
        """Reset all routing metrics."""
        self.total_packets_routed = 0
        self.total_packets_delivered = 0
        self.total_packets_dropped = 0
        self.total_broadcasts = 0
        self.routing_updates = 0
        self.packet_history.clear()
        self.broadcast_seen.clear()
