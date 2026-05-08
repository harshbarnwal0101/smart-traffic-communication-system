"""
Network Packet
===============
Defines packet structure for the Network Layer,
including packet types for different VANET scenarios.
"""

import time
import json
from enum import Enum
from typing import Optional, List


class PacketType(Enum):
    """Types of network layer packets."""
    UNICAST = "UNICAST"           # Point-to-point message
    BROADCAST = "BROADCAST"       # Broadcast to all nodes
    ACCIDENT_ALERT = "ACCIDENT"   # Emergency accident notification
    EMERGENCY = "EMERGENCY"       # Emergency vehicle priority signal
    CONGESTION = "CONGESTION"     # Congestion report
    TRAFFIC_UPDATE = "TRAFFIC"    # Traffic signal timing update
    BEACON = "BEACON"             # Periodic hello/discovery
    ROUTE_UPDATE = "ROUTE"        # Routing table update


class Packet:
    """
    Network Layer packet with routing metadata.

    Structure:
    ┌──────────┬────────┬──────┬─────┬──────┬─────────┬──────┬─────────┐
    │ PACKET_ID│ TYPE   │ SRC  │ DST │ TTL  │ HOP_CNT │ DATA │ ROUTE   │
    └──────────┴────────┴──────┴─────┴──────┴─────────┴──────┴─────────┘
    """

    _id_counter = 0

    def __init__(self, packet_type: PacketType, source: str,
                 destination: str, data: str, ttl: int = 10):
        """
        Create a network packet.

        Args:
            packet_type: Type of packet.
            source: Source node ID.
            destination: Destination node ID or "BROADCAST" for broadcast.
            data: Payload data.
            ttl: Time to Live (max hops before discarding).
        """
        Packet._id_counter += 1
        self.packet_id = Packet._id_counter
        self.packet_type = packet_type
        self.source = source
        self.destination = destination
        self.data = data
        self.ttl = ttl
        self.hop_count = 0
        self.route: List[str] = [source]  # Path taken so far
        self.creation_time = time.time()
        self.delivery_time: Optional[float] = None
        self.delivered = False
        self.dropped = False
        self.metadata: dict = {}

    def add_hop(self, node_id: str):
        """Record a hop through a node."""
        self.hop_count += 1
        self.ttl -= 1
        self.route.append(node_id)

    def is_expired(self) -> bool:
        """Check if packet TTL has expired."""
        return self.ttl <= 0

    def mark_delivered(self):
        """Mark packet as successfully delivered."""
        self.delivered = True
        self.delivery_time = time.time()

    def mark_dropped(self):
        """Mark packet as dropped."""
        self.dropped = True

    def get_latency(self) -> float:
        """
        Get end-to-end latency in milliseconds.

        Returns:
            Latency in ms, or -1 if not delivered.
        """
        if self.delivery_time is not None:
            return (self.delivery_time - self.creation_time) * 1000
        return -1.0

    def is_broadcast(self) -> bool:
        """Check if this is a broadcast packet."""
        return (self.destination == "BROADCAST" or
                self.packet_type in (PacketType.BROADCAST, PacketType.ACCIDENT_ALERT))

    def is_emergency(self) -> bool:
        """Check if this is an emergency packet."""
        return self.packet_type in (PacketType.EMERGENCY, PacketType.ACCIDENT_ALERT)

    def serialize(self) -> str:
        """Serialize packet to JSON string."""
        return json.dumps({
            "id": self.packet_id,
            "type": self.packet_type.value,
            "src": self.source,
            "dst": self.destination,
            "data": self.data,
            "ttl": self.ttl,
            "hops": self.hop_count,
            "route": self.route,
            "meta": self.metadata,
        })

    @classmethod
    def deserialize(cls, json_str: str) -> Optional['Packet']:
        """Deserialize packet from JSON string."""
        try:
            d = json.loads(json_str)
            pkt = cls(
                PacketType(d["type"]),
                d["src"],
                d["dst"],
                d["data"],
                d["ttl"],
            )
            pkt.packet_id = d["id"]
            pkt.hop_count = d["hops"]
            pkt.route = d["route"]
            pkt.metadata = d.get("meta", {})
            return pkt
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def __repr__(self) -> str:
        return (f"Packet(id={self.packet_id}, type={self.packet_type.value}, "
                f"src={self.source}, dst={self.destination}, "
                f"hops={self.hop_count}, ttl={self.ttl})")
