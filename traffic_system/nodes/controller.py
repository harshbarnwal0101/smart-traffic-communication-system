"""
Central Controller
==================
Optional central controller node that aggregates information
from all nodes and provides network-wide traffic management.
"""

import time
import logging
from typing import Tuple, Dict, List, Optional
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class CentralController(BaseNode):
    """
    Central controller for the VANET system.

    Aggregates data from vehicles and traffic signals to provide:
    - Network-wide traffic overview
    - Coordinated signal management
    - Emergency routing coordination
    - Congestion management strategies
    """

    def __init__(self, node_id: str = "CONTROLLER",
                 position: Tuple[float, float] = (500, 500)):
        """
        Initialize central controller.

        Args:
            node_id: Controller identifier.
            position: Position in the network (usually center).
        """
        super().__init__(node_id, position, "controller")

        # Network state tracking
        self.active_accidents: Dict[str, dict] = {}
        self.active_emergencies: Dict[str, dict] = {}
        self.congestion_zones: List[dict] = []
        self.vehicle_registry: Dict[str, dict] = {}
        self.signal_registry: Dict[str, dict] = {}

        # Statistics
        self.total_accidents_handled = 0
        self.total_emergencies_handled = 0
        self.total_congestion_events = 0
        self.alerts_broadcast = 0

    def register_vehicle(self, vehicle_id: str, vehicle_info: dict):
        """Register a vehicle with the controller."""
        self.vehicle_registry[vehicle_id] = {
            **vehicle_info,
            "registered_at": time.time(),
        }

    def register_signal(self, signal_id: str, signal_info: dict):
        """Register a traffic signal with the controller."""
        self.signal_registry[signal_id] = {
            **signal_info,
            "registered_at": time.time(),
        }

    def report_accident(self, vehicle_id: str, position: Tuple[float, float],
                        severity: str, sim_time: float):
        """
        Handle accident report from a vehicle.

        Args:
            vehicle_id: Vehicle that had the accident.
            position: Accident location.
            severity: Accident severity level.
            sim_time: Current simulation time.
        """
        self.active_accidents[vehicle_id] = {
            "vehicle_id": vehicle_id,
            "position": position,
            "severity": severity,
            "reported_at": sim_time,
            "status": "active",
        }
        self.total_accidents_handled += 1

        self.log_event("ACCIDENT_REPORTED", {
            "vehicle_id": vehicle_id,
            "position": position,
            "severity": severity,
        })

        # Broadcast accident alert
        self.queue_message({
            "type": "ACCIDENT_BROADCAST",
            "controller_id": self.node_id,
            "accident_info": self.active_accidents[vehicle_id],
            "message": f"CONTROLLER: Accident at ({position[0]:.0f}, {position[1]:.0f}) - {severity}",
        })
        self.alerts_broadcast += 1

    def report_emergency_vehicle(self, vehicle_id: str, vehicle_type: str,
                                 position: Tuple[float, float], direction: float,
                                 sim_time: float):
        """Handle emergency vehicle report."""
        self.active_emergencies[vehicle_id] = {
            "vehicle_id": vehicle_id,
            "vehicle_type": vehicle_type,
            "position": position,
            "direction": direction,
            "reported_at": sim_time,
        }
        self.total_emergencies_handled += 1

        self.log_event("EMERGENCY_REPORTED", {
            "vehicle_id": vehicle_id,
            "vehicle_type": vehicle_type,
        })

    def report_congestion(self, position: Tuple[float, float],
                          avg_speed: float, density: int, sim_time: float):
        """Handle congestion report."""
        zone = {
            "position": position,
            "avg_speed": avg_speed,
            "density": density,
            "reported_at": sim_time,
        }
        self.congestion_zones.append(zone)
        self.total_congestion_events += 1

        self.log_event("CONGESTION_REPORTED", {
            "position": position,
            "avg_speed": avg_speed,
        })

    def get_nearest_signals_to_accident(self, accident_position: Tuple[float, float],
                                        max_distance: float = 300.0) -> List[str]:
        """Find traffic signals near an accident for rerouting."""
        import math
        nearby = []
        for sig_id, sig_info in self.signal_registry.items():
            pos = sig_info.get("position", (0, 0))
            dist = math.sqrt(
                (pos[0] - accident_position[0]) ** 2 +
                (pos[1] - accident_position[1]) ** 2
            )
            if dist <= max_distance:
                nearby.append(sig_id)
        return nearby

    def update(self, sim_time: float, **kwargs):
        """Update controller state."""
        # Clean up old congestion zones (older than 60 seconds)
        self.congestion_zones = [
            z for z in self.congestion_zones
            if sim_time - z["reported_at"] < 60.0
        ]

    def get_network_summary(self) -> dict:
        """Get a summary of the entire network state."""
        return {
            "total_vehicles": len(self.vehicle_registry),
            "total_signals": len(self.signal_registry),
            "active_accidents": len(self.active_accidents),
            "active_emergencies": len(self.active_emergencies),
            "congestion_zones": len(self.congestion_zones),
            "total_accidents_handled": self.total_accidents_handled,
            "total_emergencies_handled": self.total_emergencies_handled,
            "total_congestion_events": self.total_congestion_events,
            "alerts_broadcast": self.alerts_broadcast,
        }

    def get_status(self) -> dict:
        """Get controller status."""
        status = super().get_status()
        status.update(self.get_network_summary())
        return status
