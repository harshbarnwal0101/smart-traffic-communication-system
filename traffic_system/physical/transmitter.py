"""
Physical Layer Transmitter
==========================
Manages physical-layer transmission between nodes,
handling encoding, modulation simulation, and channel access.
"""

import time
from typing import Optional, Tuple
from .channel import WirelessChannel


class PhysicalTransmitter:
    """
    Physical layer transmitter that interfaces with the wireless channel.
    
    Handles:
    - Data encoding for transmission
    - Channel access and transmission scheduling
    - Reception and signal quality assessment
    - Physical layer metrics collection
    """

    def __init__(self, node_id: str, channel: WirelessChannel):
        """
        Initialize physical transmitter for a node.

        Args:
            node_id: Unique identifier for this node.
            channel: Shared wireless channel instance.
        """
        self.node_id = node_id
        self.channel = channel
        self.transmission_count = 0
        self.reception_count = 0
        self.failed_transmissions = 0

    def send(self, data: str, dest_id: str, distance: float = 10.0) -> Optional[Tuple[str, dict]]:
        """
        Send data through physical layer.

        Args:
            data: Text data to transmit.
            dest_id: Destination node ID.
            distance: Distance to destination in meters.

        Returns:
            Tuple of (received data, stats) or None if transmission failed.
        """
        self.transmission_count += 1
        result = self.channel.transmit(data, self.node_id, dest_id, distance)

        if result is None:
            self.failed_transmissions += 1
            return None

        return result

    def receive(self, data: str, source_id: str) -> str:
        """
        Process received data at physical layer.

        Args:
            data: Received data string.
            source_id: ID of the sending node.

        Returns:
            Processed data string.
        """
        self.reception_count += 1
        return data

    def is_in_range(self, distance: float) -> bool:
        """Check if a node at given distance is within communication range."""
        return distance <= self.channel.max_range

    def get_metrics(self) -> dict:
        """Get physical transmitter metrics."""
        return {
            "node_id": self.node_id,
            "transmissions": self.transmission_count,
            "receptions": self.reception_count,
            "failed_transmissions": self.failed_transmissions,
            "success_rate": (
                (self.transmission_count - self.failed_transmissions) / self.transmission_count
                if self.transmission_count > 0 else 1.0
            ),
        }
