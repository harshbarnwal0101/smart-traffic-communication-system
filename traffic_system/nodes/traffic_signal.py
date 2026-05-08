"""
Traffic Signal Node
===================
Represents a traffic signal/light at an intersection in the VANET.
Manages signal phases, responds to emergency vehicle priority,
and adjusts timing based on vehicle density.
"""

import time
import logging
from typing import Tuple, Dict, List, Optional
from enum import Enum
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class SignalPhase(Enum):
    """Traffic signal phases."""
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"


class TrafficSignalNode(BaseNode):
    """
    Traffic signal node in the VANET system.

    Manages signal phases, adapts timing based on vehicle density,
    and responds to emergency vehicle priority requests.
    """

    # Default phase durations in seconds
    DEFAULT_GREEN_DURATION = 30.0
    DEFAULT_YELLOW_DURATION = 5.0
    DEFAULT_RED_DURATION = 30.0

    def __init__(self, node_id: str, position: Tuple[float, float],
                 intersection_name: str = ""):
        """
        Initialize traffic signal node.

        Args:
            node_id: Unique signal identifier.
            position: (x, y) position at intersection.
            intersection_name: Human-readable intersection name.
        """
        super().__init__(node_id, position, "signal")
        self.intersection_name = intersection_name or f"Intersection_{node_id}"

        # Phase management
        self.current_phase = SignalPhase.RED
        self.phase_start_time = 0.0
        self.green_duration = self.DEFAULT_GREEN_DURATION
        self.yellow_duration = self.DEFAULT_YELLOW_DURATION
        self.red_duration = self.DEFAULT_RED_DURATION

        # Adaptive timing
        self.vehicle_density = 0  # Vehicles in range
        self.adaptive_mode = True
        self.min_green = 10.0
        self.max_green = 60.0

        # Emergency override
        self.emergency_override = False
        self.emergency_vehicle_id: Optional[str] = None
        self.override_start_time: Optional[float] = None

        # History
        self.phase_history: List[dict] = []
        self.density_history: List[Tuple[float, int]] = []
        self.emergency_overrides_count = 0

    def get_phase_duration(self) -> float:
        """Get current phase duration."""
        if self.current_phase == SignalPhase.GREEN:
            return self.green_duration
        elif self.current_phase == SignalPhase.YELLOW:
            return self.yellow_duration
        else:
            return self.red_duration

    def _next_phase(self) -> SignalPhase:
        """Get the next phase in sequence."""
        if self.current_phase == SignalPhase.GREEN:
            return SignalPhase.YELLOW
        elif self.current_phase == SignalPhase.YELLOW:
            return SignalPhase.RED
        else:
            return SignalPhase.GREEN

    def set_phase(self, phase: SignalPhase, sim_time: float):
        """
        Set signal to a specific phase.

        Args:
            phase: New phase.
            sim_time: Current simulation time.
        """
        old_phase = self.current_phase
        self.current_phase = phase
        self.phase_start_time = sim_time

        self.phase_history.append({
            "time": sim_time,
            "from": old_phase.value,
            "to": phase.value,
            "reason": "emergency_override" if self.emergency_override else "normal_cycle",
        })

        self.log_event("PHASE_CHANGE", {
            "from": old_phase.value,
            "to": phase.value,
            "emergency": self.emergency_override,
        })

    def update_density(self, vehicle_count: int, sim_time: float):
        """
        Update vehicle density and adjust signal timing adaptively.

        Args:
            vehicle_count: Number of vehicles in detection range.
            sim_time: Current simulation time.
        """
        self.vehicle_density = vehicle_count
        self.density_history.append((sim_time, vehicle_count))

        if self.adaptive_mode and not self.emergency_override:
            # Adjust green time based on density
            # More vehicles → longer green time
            if vehicle_count > 10:
                self.green_duration = min(self.max_green, 30 + vehicle_count * 2)
            elif vehicle_count > 5:
                self.green_duration = 30.0
            else:
                self.green_duration = max(self.min_green, 20.0)

    def handle_emergency(self, emergency_vehicle_id: str, sim_time: float):
        """
        Handle emergency vehicle priority request.
        Immediately switch to GREEN for the emergency vehicle.

        Args:
            emergency_vehicle_id: ID of the emergency vehicle.
            sim_time: Current simulation time.
        """
        if not self.emergency_override:
            self.emergency_override = True
            self.emergency_vehicle_id = emergency_vehicle_id
            self.override_start_time = sim_time
            self.emergency_overrides_count += 1

            # Force green for emergency vehicle
            self.set_phase(SignalPhase.GREEN, sim_time)

            self.log_event("EMERGENCY_OVERRIDE", {
                "emergency_vehicle": emergency_vehicle_id,
            })

            self.queue_message({
                "type": "EMERGENCY_RESPONSE",
                "signal_id": self.node_id,
                "vehicle_id": emergency_vehicle_id,
                "action": "GREEN_ACTIVATED",
                "message": f"Signal {self.node_id} GREEN for emergency vehicle {emergency_vehicle_id}",
            })

    def clear_emergency(self, sim_time: float):
        """Clear emergency override and resume normal operation."""
        if self.emergency_override:
            self.emergency_override = False
            self.emergency_vehicle_id = None
            self.override_start_time = None
            self.log_event("EMERGENCY_CLEARED", {})

    def update(self, sim_time: float, **kwargs):
        """
        Update signal state for current simulation tick.

        Args:
            sim_time: Current simulation time.
        """
        if self.emergency_override:
            # Check if emergency override should timeout (30 seconds max)
            if (self.override_start_time and
                    sim_time - self.override_start_time > 30.0):
                self.clear_emergency(sim_time)
            else:
                return  # Stay in emergency override mode

        # Normal phase cycling
        elapsed = sim_time - self.phase_start_time
        duration = self.get_phase_duration()

        if elapsed >= duration:
            next_phase = self._next_phase()
            self.set_phase(next_phase, sim_time)

    def get_status(self) -> dict:
        """Get traffic signal status."""
        status = super().get_status()
        status.update({
            "intersection": self.intersection_name,
            "current_phase": self.current_phase.value,
            "green_duration": self.green_duration,
            "vehicle_density": self.vehicle_density,
            "emergency_override": self.emergency_override,
            "emergency_vehicle": self.emergency_vehicle_id,
            "adaptive_mode": self.adaptive_mode,
            "total_emergency_overrides": self.emergency_overrides_count,
        })
        return status
