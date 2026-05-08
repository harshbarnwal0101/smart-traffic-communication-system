"""
Network Layer Module
====================
Implements routing algorithms (Dijkstra), packet forwarding,
multi-hop communication, and broadcast mechanisms for the VANET.
"""

from .router import Router
from .packet import Packet, PacketType
from .topology import NetworkTopology

__all__ = ["Router", "Packet", "PacketType", "NetworkTopology"]
