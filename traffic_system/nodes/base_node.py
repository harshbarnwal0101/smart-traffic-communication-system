"""
Base Node
=========
Abstract base class for all VANET nodes, providing common
communication, neighbor management, and event handling.
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Set

logger = logging.getLogger(__name__)


class BaseNode(ABC):
    """
    Abstract base node for the VANET system.
    
    All node types (Vehicle, Traffic Signal, Controller) extend this class,
    inheriting common communication and neighbor management logic.
    """

    def __init__(self, node_id: str, position: Tuple[float, float],
                 node_type: str = "generic"):
        """
        Initialize base node.

        Args:
            node_id: Unique identifier.
            position: (x, y) position in meters.
            node_type: Type string ("vehicle", "signal", "controller").
        """
        self.node_id = node_id
        self.position = position
        self.node_type = node_type
        self.neighbors: Set[str] = set()
        self.active = True
        self.message_queue: List[dict] = []
        self.received_messages: List[dict] = []
        self.sent_messages: List[dict] = []
        self.event_log: List[dict] = []
        self.creation_time = time.time()

    def update_neighbors(self, neighbor_ids: List[str]):
        """Update the neighbor list for this node."""
        self.neighbors = set(neighbor_ids)

    def add_neighbor(self, neighbor_id: str):
        """Add a neighbor."""
        self.neighbors.add(neighbor_id)

    def remove_neighbor(self, neighbor_id: str):
        """Remove a neighbor."""
        self.neighbors.discard(neighbor_id)

    def has_neighbor(self, node_id: str) -> bool:
        """Check if a node is a neighbor."""
        return node_id in self.neighbors

    def queue_message(self, message: dict):
        """Add a message to the outgoing queue."""
        message["timestamp"] = time.time()
        message["sender"] = self.node_id
        self.message_queue.append(message)

    def receive_message(self, message: dict):
        """Process a received message."""
        self.received_messages.append(message)
        self.log_event("MESSAGE_RECEIVED", {
            "from": message.get("sender", "unknown"),
            "type": message.get("type", "unknown"),
        })

    def log_event(self, event_type: str, details: dict = None):
        """Log an event for this node."""
        self.event_log.append({
            "time": time.time(),
            "event": event_type,
            "node": self.node_id,
            "details": details or {},
        })

    def get_pending_messages(self) -> List[dict]:
        """Get and clear pending outgoing messages."""
        messages = self.message_queue.copy()
        self.message_queue.clear()
        return messages

    @abstractmethod
    def update(self, sim_time: float, **kwargs):
        """
        Update node state for current simulation tick.

        Args:
            sim_time: Current simulation time in seconds.
        """
        pass

    def get_status(self) -> dict:
        """Get current node status."""
        return {
            "node_id": self.node_id,
            "type": self.node_type,
            "position": self.position,
            "active": self.active,
            "neighbors": list(self.neighbors),
            "neighbor_count": len(self.neighbors),
            "messages_sent": len(self.sent_messages),
            "messages_received": len(self.received_messages),
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.node_id}, pos={self.position})"
