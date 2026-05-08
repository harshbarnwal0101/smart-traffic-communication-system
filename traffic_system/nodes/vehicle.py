"""
Vehicle Node
=============
Represents a vehicle in the VANET, with movement simulation,
accident detection, emergency signaling, and congestion reporting.
"""

import random
import math
import time
import logging
from typing import Tuple, Optional, List
from .base_node import BaseNode

logger = logging.getLogger(__name__)


class VehicleType:
    """Vehicle type constants."""
    CAR = "car"
    AMBULANCE = "ambulance"
    FIRE_TRUCK = "fire_truck"
    POLICE = "police"


class VehicleNode(BaseNode):
    """
    Vehicle node in the VANET system.

    Simulates vehicle movement, speed changes, accident detection,
    and communication with other vehicles and traffic signals.
    """

    def __init__(self, node_id: str, position: Tuple[float, float],
                 vehicle_type: str = VehicleType.CAR,
                 speed: float = 40.0, direction: float = 0.0):
        """
        Initialize vehicle node.

        Args:
            node_id: Unique vehicle identifier.
            position: (x, y) starting position in meters.
            vehicle_type: Type of vehicle (car, ambulance, etc.).
            speed: Initial speed in km/h.
            direction: Movement direction in degrees (0=East, 90=North).
        """
        super().__init__(node_id, position, "vehicle")
        self.vehicle_type = vehicle_type
        self.speed = speed  # km/h
        self.max_speed = 120.0 if vehicle_type == VehicleType.CAR else 140.0
        self.direction = direction  # degrees
        self.acceleration = 0.0  # km/h per second
        self.is_emergency = vehicle_type in (
            VehicleType.AMBULANCE, VehicleType.FIRE_TRUCK, VehicleType.POLICE
        )

        # State flags
        self.has_accident = False
        self.is_congested = False
        self.emergency_active = False  # For emergency vehicles: lights/siren on
        self.stopped = False

        # Movement boundaries
        self.bounds = (0, 0, 1000, 1000)  # (min_x, min_y, max_x, max_y)

        # History tracking
        self.position_history: List[Tuple[float, float]] = [position]
        self.speed_history: List[float] = [speed]

    def set_bounds(self, min_x: float, min_y: float, max_x: float, max_y: float):
        """Set movement boundaries for the vehicle."""
        self.bounds = (min_x, min_y, max_x, max_y)

    def move(self, dt: float):
        """
        Move vehicle based on current speed and direction.

        Args:
            dt: Time step in seconds.
        """
        if self.stopped or self.has_accident:
            return

        # Apply acceleration
        self.speed = max(0, min(self.max_speed, self.speed + self.acceleration * dt))

        # Convert speed to m/s for position update
        speed_ms = self.speed * 1000 / 3600

        # Calculate displacement
        rad = math.radians(self.direction)
        dx = speed_ms * math.cos(rad) * dt
        dy = speed_ms * math.sin(rad) * dt

        # Update position with boundary wrapping
        x = self.position[0] + dx
        y = self.position[1] + dy

        # Wrap around boundaries
        min_x, min_y, max_x, max_y = self.bounds
        if x > max_x:
            x = min_x + (x - max_x)
            self.direction = random.uniform(0, 360)
        elif x < min_x:
            x = max_x - (min_x - x)
            self.direction = random.uniform(0, 360)
        if y > max_y:
            y = min_y + (y - max_y)
            self.direction = random.uniform(0, 360)
        elif y < min_y:
            y = max_y - (min_y - y)
            self.direction = random.uniform(0, 360)

        self.position = (x, y)
        self.position_history.append(self.position)
        self.speed_history.append(self.speed)

    def trigger_accident(self):
        """Simulate an accident occurring at this vehicle."""
        self.has_accident = True
        self.speed = 0
        self.stopped = True
        self.log_event("ACCIDENT", {
            "position": self.position,
            "previous_speed": self.speed_history[-2] if len(self.speed_history) > 1 else 0,
        })

        # Queue accident broadcast message
        self.queue_message({
            "type": "ACCIDENT_ALERT",
            "vehicle_id": self.node_id,
            "position": self.position,
            "severity": random.choice(["minor", "moderate", "severe"]),
            "message": f"ACCIDENT at {self.node_id} position ({self.position[0]:.1f}, {self.position[1]:.1f})",
        })

    def activate_emergency(self):
        """Activate emergency mode (for emergency vehicles)."""
        if self.is_emergency:
            self.emergency_active = True
            self.log_event("EMERGENCY_ACTIVATED", {
                "vehicle_type": self.vehicle_type,
                "position": self.position,
            })

            # Queue emergency priority message
            self.queue_message({
                "type": "EMERGENCY_PRIORITY",
                "vehicle_id": self.node_id,
                "vehicle_type": self.vehicle_type,
                "position": self.position,
                "direction": self.direction,
                "speed": self.speed,
                "message": f"EMERGENCY {self.vehicle_type} {self.node_id} requesting priority",
            })

    def detect_congestion(self, neighbor_speeds: List[float]) -> bool:
        """
        Detect congestion based on own and neighbor speeds.

        Args:
            neighbor_speeds: List of speeds from neighboring vehicles.

        Returns:
            True if congestion is detected.
        """
        if not neighbor_speeds:
            self.is_congested = False
            return False

        avg_speed = (sum(neighbor_speeds) + self.speed) / (len(neighbor_speeds) + 1)
        # Congestion if average speed is below 20 km/h
        self.is_congested = avg_speed < 20.0

        if self.is_congested:
            self.log_event("CONGESTION_DETECTED", {
                "avg_speed": avg_speed,
                "own_speed": self.speed,
                "neighbor_count": len(neighbor_speeds),
            })
            self.queue_message({
                "type": "CONGESTION_REPORT",
                "vehicle_id": self.node_id,
                "position": self.position,
                "avg_speed": avg_speed,
                "density": len(neighbor_speeds),
                "message": f"CONGESTION near {self.node_id}: avg speed {avg_speed:.1f} km/h",
            })

        return self.is_congested

    def update(self, sim_time: float, dt: float = 1.0, **kwargs):
        """
        Update vehicle state for current simulation tick.

        Args:
            sim_time: Current simulation time.
            dt: Time step in seconds.
        """
        # Random speed adjustments (simulating traffic flow)
        if not self.stopped and not self.has_accident:
            # Small random direction changes
            self.direction += random.uniform(-5, 5)
            self.direction %= 360

            # Random acceleration changes
            self.acceleration = random.uniform(-2, 2)

        self.move(dt)

    def get_status(self) -> dict:
        """Get comprehensive vehicle status."""
        status = super().get_status()
        status.update({
            "vehicle_type": self.vehicle_type,
            "speed": self.speed,
            "direction": self.direction,
            "has_accident": self.has_accident,
            "is_congested": self.is_congested,
            "is_emergency": self.is_emergency,
            "emergency_active": self.emergency_active,
        })
        return status
