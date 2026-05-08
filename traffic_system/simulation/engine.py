"""
Simulation Engine
=================
Time-based discrete event simulation engine that orchestrates
all VANET nodes, manages communication, and collects metrics.
"""

import random
import time
import math
import logging
from typing import Dict, List, Optional, Tuple

from ..physical.channel import WirelessChannel
from ..physical.transmitter import PhysicalTransmitter
from ..datalink.frame import Frame, FrameType
from ..datalink.arq import StopAndWaitARQ
from ..network.topology import NetworkTopology
from ..network.router import Router
from ..network.packet import Packet, PacketType
from ..nodes.vehicle import VehicleNode, VehicleType
from ..nodes.traffic_signal import TrafficSignalNode, SignalPhase
from ..nodes.controller import CentralController
from ..metrics.collector import MetricsCollector
from ..metrics.kpi import KPICalculator

logger = logging.getLogger(__name__)


class SimulationEngine:
    """
    Main simulation engine for the VANET system.

    Manages:
    - Node creation and lifecycle
    - Time-stepped simulation loop
    - Cross-layer communication
    - Event scheduling and processing
    - Metrics collection per tick
    """

    def __init__(self, config: dict = None):
        """
        Initialize simulation engine.

        Args:
            config: Simulation configuration dictionary.
        """
        self.config = config or self._default_config()

        # Core simulation parameters
        self.sim_time = 0.0
        self.dt = self.config.get("time_step", 1.0)  # seconds per tick
        self.duration = self.config.get("duration", 60.0)  # total sim seconds
        self.running = False
        self.tick_count = 0

        # Network components
        self.channel = WirelessChannel(
            noise_level=self.config.get("noise_level", 0.01),
            packet_loss_rate=self.config.get("packet_loss_rate", 0.02),
            max_range=self.config.get("communication_range", 300.0),
        )
        self.topology = NetworkTopology(
            communication_range=self.config.get("communication_range", 300.0)
        )
        self.router = Router(self.topology)
        self.arq = StopAndWaitARQ(
            max_retries=self.config.get("max_retries", 3),
            timeout=self.config.get("arq_timeout", 0.5),
        )

        # Nodes
        self.vehicles: Dict[str, VehicleNode] = {}
        self.signals: Dict[str, TrafficSignalNode] = {}
        self.controller: Optional[CentralController] = None

        # Physical transmitters per node
        self.transmitters: Dict[str, PhysicalTransmitter] = {}

        # Metrics
        self.collector = MetricsCollector()
        self.kpi_calculator = KPICalculator(self.collector)

        # Event log
        self.event_log: List[dict] = []

        # World boundaries
        self.world_size = self.config.get("world_size", (1000, 1000))

    @staticmethod
    def _default_config() -> dict:
        """Default simulation configuration."""
        return {
            "num_vehicles": 15,
            "num_signals": 4,
            "num_emergency": 2,
            "communication_range": 300.0,
            "noise_level": 0.01,
            "packet_loss_rate": 0.02,
            "max_retries": 3,
            "arq_timeout": 0.5,
            "time_step": 1.0,
            "duration": 60.0,
            "world_size": (1000, 1000),
            "accident_probability": 0.02,
            "congestion_check_interval": 5.0,
            "metrics_interval": 2.0,
        }

    def setup(self):
        """Set up the simulation with nodes and initial topology."""
        self._create_controller()
        self._create_traffic_signals()
        self._create_vehicles()
        self._update_topology()

        self.log("SETUP_COMPLETE",
                 f"Created {len(self.vehicles)} vehicles, "
                 f"{len(self.signals)} signals, 1 controller")

    def _create_controller(self):
        """Create the central controller."""
        cx, cy = self.world_size[0] / 2, self.world_size[1] / 2
        self.controller = CentralController("CTRL", (cx, cy))
        self.topology.add_node("CTRL", (cx, cy), "controller")
        self.transmitters["CTRL"] = PhysicalTransmitter("CTRL", self.channel)

    def _create_traffic_signals(self):
        """Create traffic signal nodes at intersection positions."""
        num_signals = self.config.get("num_signals", 4)
        w, h = self.world_size

        # Place signals at grid intersections
        positions = []
        if num_signals >= 4:
            positions = [
                (w * 0.25, h * 0.25), (w * 0.75, h * 0.25),
                (w * 0.25, h * 0.75), (w * 0.75, h * 0.75),
            ]
        # Add more signals if needed
        for i in range(4, num_signals):
            positions.append((
                random.uniform(w * 0.1, w * 0.9),
                random.uniform(h * 0.1, h * 0.9),
            ))

        for i, pos in enumerate(positions[:num_signals]):
            sig_id = f"SIG_{i + 1}"
            signal = TrafficSignalNode(sig_id, pos, f"Intersection_{i + 1}")
            # Stagger initial phases
            if i % 2 == 0:
                signal.set_phase(SignalPhase.GREEN, 0)
            else:
                signal.set_phase(SignalPhase.RED, 0)

            self.signals[sig_id] = signal
            self.topology.add_node(sig_id, pos, "signal")
            self.transmitters[sig_id] = PhysicalTransmitter(sig_id, self.channel)

            if self.controller:
                self.controller.register_signal(sig_id, {
                    "position": pos,
                    "intersection": signal.intersection_name,
                })

    def _create_vehicles(self):
        """Create vehicle nodes at random positions."""
        num_vehicles = self.config.get("num_vehicles", 15)
        num_emergency = self.config.get("num_emergency", 2)
        w, h = self.world_size

        for i in range(num_vehicles):
            veh_id = f"VEH_{i + 1:02d}"
            pos = (random.uniform(50, w - 50), random.uniform(50, h - 50))
            direction = random.uniform(0, 360)
            speed = random.uniform(20, 80)

            # First N vehicles are emergency vehicles
            if i < num_emergency:
                v_type = random.choice([VehicleType.AMBULANCE, VehicleType.FIRE_TRUCK])
                veh_id = f"EMG_{i + 1:02d}"
            else:
                v_type = VehicleType.CAR

            vehicle = VehicleNode(veh_id, pos, v_type, speed, direction)
            vehicle.set_bounds(0, 0, w, h)
            self.vehicles[veh_id] = vehicle
            self.topology.add_node(veh_id, pos, "vehicle")
            self.transmitters[veh_id] = PhysicalTransmitter(veh_id, self.channel)

            if self.controller:
                self.controller.register_vehicle(veh_id, {
                    "type": v_type,
                    "position": pos,
                    "speed": speed,
                })

    def _update_topology(self):
        """Update network topology based on current node positions."""
        # Update vehicle positions in topology
        for veh_id, vehicle in self.vehicles.items():
            self.topology.update_node_position(veh_id, vehicle.position)

        # Refresh all links
        self.topology.refresh_all_links()

        # Update neighbor lists for all nodes
        for node_id in self.topology.get_all_nodes():
            neighbors = self.topology.get_neighbors(node_id)
            if node_id in self.vehicles:
                self.vehicles[node_id].update_neighbors(neighbors)
            elif node_id in self.signals:
                self.signals[node_id].update_neighbors(neighbors)
            elif self.controller and node_id == self.controller.node_id:
                self.controller.update_neighbors(neighbors)

        # Update routing tables
        self.router.update_all_routing_tables()

    def run(self, progress_callback=None) -> dict:
        """
        Run the simulation.

        Args:
            progress_callback: Optional callback(tick, total_ticks, sim_time).

        Returns:
            Final KPIs dictionary.
        """
        self.running = True
        total_ticks = int(self.duration / self.dt)

        self.log("SIMULATION_START",
                 f"Duration={self.duration}s, dt={self.dt}s, ticks={total_ticks}")

        start_real_time = time.time()

        for tick in range(total_ticks):
            if not self.running:
                break

            self.sim_time = tick * self.dt
            self.tick_count = tick

            # 1. Update node positions and movements
            self._tick_movement()

            # 2. Update network topology
            self._update_topology()

            # 3. Update traffic signals
            self._tick_signals()

            # 4. Check for events (accidents, congestion, emergencies)
            self._tick_events()

            # 5. Process communication
            self._tick_communication()

            # 6. Collect metrics
            if tick % max(1, int(self.config.get("metrics_interval", 2.0) / self.dt)) == 0:
                self._collect_metrics()

            # Progress callback
            if progress_callback and tick % 5 == 0:
                progress_callback(tick, total_ticks, self.sim_time)

        self.running = False
        elapsed = time.time() - start_real_time

        # Final metrics collection
        self._collect_metrics()

        self.log("SIMULATION_END",
                 f"Completed {self.tick_count} ticks in {elapsed:.2f}s real time")

        return self.kpi_calculator.compute_all_kpis(self.duration)

    def _tick_movement(self):
        """Update all vehicle movements."""
        for vehicle in self.vehicles.values():
            vehicle.update(self.sim_time, dt=self.dt)

    def _tick_signals(self):
        """Update all traffic signals."""
        for sig_id, signal in self.signals.items():
            # Count vehicles near this signal
            vehicle_count = 0
            for veh in self.vehicles.values():
                dist = math.sqrt(
                    (veh.position[0] - signal.position[0]) ** 2 +
                    (veh.position[1] - signal.position[1]) ** 2
                )
                if dist <= 200:  # Detection range
                    vehicle_count += 1

            signal.update_density(vehicle_count, self.sim_time)
            signal.update(self.sim_time)

    def _tick_events(self):
        """Check for and trigger simulation events."""
        accident_prob = self.config.get("accident_probability", 0.02)
        congestion_interval = self.config.get("congestion_check_interval", 5.0)

        for veh_id, vehicle in self.vehicles.items():
            # Random accident trigger
            if (not vehicle.has_accident and
                    random.random() < accident_prob * self.dt and
                    self.sim_time > 5.0):  # No accidents in first 5 seconds
                vehicle.trigger_accident()
                self.log("ACCIDENT", f"Vehicle {veh_id} accident at "
                                     f"({vehicle.position[0]:.0f}, {vehicle.position[1]:.0f})")

                if self.controller:
                    self.controller.report_accident(
                        veh_id, vehicle.position,
                        vehicle.event_log[-1]["details"].get("severity", "moderate")
                        if vehicle.event_log else "moderate",
                        self.sim_time,
                    )

                # Create and route accident broadcast packet
                pkt = Packet(PacketType.ACCIDENT_ALERT, veh_id, "BROADCAST",
                             f"ACCIDENT:{veh_id}:{vehicle.position}", ttl=10)
                self.router.route_packet(pkt)

            # Emergency vehicle activation
            if (vehicle.is_emergency and not vehicle.emergency_active and
                    self.sim_time > 3.0 and random.random() < 0.05 * self.dt):
                vehicle.activate_emergency()
                self.log("EMERGENCY", f"Emergency vehicle {veh_id} activated")

                if self.controller:
                    self.controller.report_emergency_vehicle(
                        veh_id, vehicle.vehicle_type,
                        vehicle.position, vehicle.direction, self.sim_time,
                    )

                # Send emergency priority to nearby signals
                for sig_id, signal in self.signals.items():
                    dist = math.sqrt(
                        (vehicle.position[0] - signal.position[0]) ** 2 +
                        (vehicle.position[1] - signal.position[1]) ** 2
                    )
                    if dist <= 400:  # Emergency signal range
                        signal.handle_emergency(veh_id, self.sim_time)
                        self.log("EMERGENCY_SIGNAL",
                                 f"Signal {sig_id} GREEN for {veh_id}")

                # Route emergency packet
                pkt = Packet(PacketType.EMERGENCY, veh_id, "BROADCAST",
                             f"EMERGENCY:{vehicle.vehicle_type}:{veh_id}", ttl=10)
                self.router.route_packet(pkt)

            # Congestion detection (periodic)
            if (int(self.sim_time) % int(max(1, congestion_interval)) == 0 and
                    not vehicle.has_accident):
                neighbor_speeds = []
                for neighbor_id in vehicle.neighbors:
                    if neighbor_id in self.vehicles:
                        neighbor_speeds.append(self.vehicles[neighbor_id].speed)

                if vehicle.detect_congestion(neighbor_speeds) and self.controller:
                    self.controller.report_congestion(
                        vehicle.position,
                        sum(neighbor_speeds + [vehicle.speed]) / (len(neighbor_speeds) + 1),
                        len(neighbor_speeds),
                        self.sim_time,
                    )

    def _tick_communication(self):
        """Process inter-node communication for this tick."""
        all_nodes = list(self.vehicles.keys()) + list(self.signals.keys())

        # Process pending messages from all nodes
        for node_id in all_nodes:
            node = self.vehicles.get(node_id) or self.signals.get(node_id)
            if not node:
                continue

            messages = node.get_pending_messages()
            for msg in messages:
                msg_type = msg.get("type", "GENERIC")

                # Determine packet type and destination
                if msg_type in ("ACCIDENT_ALERT", "ACCIDENT_BROADCAST"):
                    pkt_type = PacketType.ACCIDENT_ALERT
                    dest = "BROADCAST"
                elif msg_type == "EMERGENCY_PRIORITY":
                    pkt_type = PacketType.EMERGENCY
                    dest = "BROADCAST"
                elif msg_type == "CONGESTION_REPORT":
                    pkt_type = PacketType.CONGESTION
                    dest = "CTRL"
                elif msg_type == "EMERGENCY_RESPONSE":
                    pkt_type = PacketType.TRAFFIC_UPDATE
                    dest = msg.get("vehicle_id", "BROADCAST")
                else:
                    pkt_type = PacketType.UNICAST
                    dest = msg.get("destination", "CTRL")

                # Create and route packet
                pkt = Packet(pkt_type, node_id, dest,
                             msg.get("message", str(msg)), ttl=10)
                self.router.route_packet(pkt)

                # Simulate physical + datalink transmission for first hop
                if pkt.route and len(pkt.route) >= 2:
                    next_hop = pkt.route[1] if len(pkt.route) > 1 else pkt.route[0]
                    distance = self.topology.get_distance(node_id, next_hop)
                    if distance < float('inf'):
                        # Physical layer transmission
                        frame = Frame(FrameType.DATA, self.arq.seq_num,
                                      node_id, next_hop, msg.get("message", "")[:100])
                        self.arq.seq_num = (self.arq.seq_num + 1) % 256
                        self.arq.total_frames_sent += 1

                        result = self.channel.transmit(
                            frame.serialize(), node_id, next_hop, distance
                        )

                        if result is not None:
                            received_data, stats = result
                            # Verify frame at receiver
                            received_frame = Frame.deserialize(received_data)
                            if received_frame and received_frame.verify_crc():
                                self.arq.successful_deliveries += 1
                                self.arq.total_acks_sent += 1
                            else:
                                self.arq.frame_errors_detected += 1
                                self.arq.total_nacks_sent += 1
                                # Attempt retransmission
                                for retry in range(self.arq.max_retries):
                                    self.arq.total_retransmissions += 1
                                    self.arq.total_frames_sent += 1
                                    result2 = self.channel.transmit(
                                        frame.serialize(), node_id, next_hop, distance
                                    )
                                    if result2:
                                        recv2, _ = result2
                                        f2 = Frame.deserialize(recv2)
                                        if f2 and f2.verify_crc():
                                            self.arq.successful_deliveries += 1
                                            break
                                else:
                                    self.arq.total_frames_dropped += 1

        # Generate some routine traffic (beacons/heartbeats)
        if int(self.sim_time) % 10 == 0:
            for node_id in random.sample(all_nodes, min(3, len(all_nodes))):
                # Random unicast message
                other_nodes = [n for n in all_nodes if n != node_id]
                if other_nodes:
                    dest = random.choice(other_nodes)
                    pkt = Packet(PacketType.UNICAST, node_id, dest,
                                 f"HEARTBEAT from {node_id}", ttl=10)
                    self.router.route_packet(pkt)

    def _collect_metrics(self):
        """Collect metrics from all layers."""
        physical_metrics = self.channel.get_metrics()
        datalink_metrics = self.arq.get_metrics()
        network_metrics = self.router.get_metrics()
        system_metrics = {
            "total_nodes": self.topology.get_node_count(),
            "total_vehicles": len(self.vehicles),
            "total_signals": len(self.signals),
            "total_edges": self.topology.get_edge_count(),
            "network_density": self.topology.get_density(),
            "average_degree": self.topology.get_average_degree(),
            "active_accidents": sum(1 for v in self.vehicles.values() if v.has_accident),
            "active_emergencies": sum(1 for v in self.vehicles.values() if v.emergency_active),
            "congested_vehicles": sum(1 for v in self.vehicles.values() if v.is_congested),
        }

        self.collector.take_snapshot(
            self.sim_time, physical_metrics, datalink_metrics,
            network_metrics, system_metrics,
        )

    def log(self, event_type: str, message: str):
        """Log simulation event."""
        entry = {
            "time": self.sim_time,
            "tick": self.tick_count,
            "event": event_type,
            "message": message,
        }
        self.event_log.append(entry)
        logger.info(f"[{self.sim_time:.1f}s] [{event_type}] {message}")

    def get_state_snapshot(self) -> dict:
        """Get current simulation state."""
        return {
            "sim_time": self.sim_time,
            "tick": self.tick_count,
            "vehicles": {vid: v.get_status() for vid, v in self.vehicles.items()},
            "signals": {sid: s.get_status() for sid, s in self.signals.items()},
            "controller": self.controller.get_status() if self.controller else None,
            "topology": {
                "nodes": self.topology.get_node_count(),
                "edges": self.topology.get_edge_count(),
                "density": self.topology.get_density(),
            },
        }

    def stop(self):
        """Stop the simulation."""
        self.running = False
