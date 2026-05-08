"""
Smart Traffic Communication System - Main Runner
=================================================
Complete VANET simulation with multi-layer networking architecture.

Usage:
    python main.py                     # Run default simulation
    python main.py --scenario basic    # Run specific scenario
    python main.py --help              # Show options

Author: Smart Traffic Team
"""

import sys
import os
import time
import logging
import argparse
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from traffic_system.simulation.engine import SimulationEngine
from traffic_system.simulation.scenarios import ScenarioManager
from traffic_system.visualization.network_viz import NetworkVisualizer
from traffic_system.visualization.dashboard import PerformanceDashboard
from traffic_system.metrics.kpi import KPICalculator
from traffic_system.physical.channel import WirelessChannel
from traffic_system.network.packet import Packet, PacketType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def print_banner():
    """Print the application banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║       🚗  SMART TRAFFIC COMMUNICATION SYSTEM  🚦                ║
║       ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                    ║
║       Vehicular Ad Hoc Network (VANET) Simulator                 ║
║                                                                  ║
║       Multi-Layer Architecture:                                  ║
║         📡 Physical Layer  → Bit transmission + noise            ║
║         🔗 Data Link Layer → Framing + CRC + ARQ                ║
║         🌐 Network Layer   → Dijkstra routing + multi-hop       ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_layer_explanation():
    """Print explanation of each network layer."""
    explanation = """
┌─────────────────────────────────────────────────────────────┐
│                    LAYER ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📡 PHYSICAL LAYER (Layer 1)                               │
│  ─────────────────────────                                  │
│  • Converts data to binary for transmission                │
│  • Simulates wireless channel with noise (bit flipping)    │
│  • Models signal attenuation over distance                 │
│  • Introduces packet loss probability                      │
│  • Tracks Bit Error Rate (BER) and signal reliability      │
│                                                             │
│  🔗 DATA LINK LAYER (Layer 2)                              │
│  ─────────────────────────                                  │
│  • Frame format: [START|TYPE|SEQ|SRC|DST|LEN|DATA|CRC|END]│
│  • CRC-16 (CCITT) error detection on every frame          │
│  • Stop-and-Wait ARQ with ACK/NACK acknowledgments        │
│  • Automatic retransmission on errors (configurable)       │
│  • Tracks Frame Error Rate, retransmissions, throughput    │
│                                                             │
│  🌐 NETWORK LAYER (Layer 3)                                │
│  ─────────────────────────                                  │
│  • Graph-based network topology (networkx)                 │
│  • Dijkstra's shortest path routing                        │
│  • Dynamic routing table updates on topology changes       │
│  • Multi-hop packet forwarding with TTL                    │
│  • Broadcast flooding for accident/emergency alerts        │
│  • Tracks PDR, latency, hop count                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
"""
    print(explanation)


def run_simulation(scenario_name: str = "basic", output_dir: str = "output"):
    """
    Run a complete VANET simulation with the specified scenario.
    
    Args:
        scenario_name: Name of the scenario to run.
        output_dir: Directory for output files.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Load scenario
    config = ScenarioManager.get_scenario(scenario_name)
    print(f"\n📋 Scenario: {config.get('name', scenario_name)}")
    print(f"   {config.get('description', '')}")
    print(f"   Vehicles: {config['num_vehicles']} | "
          f"Signals: {config['num_signals']} | "
          f"Emergency: {config['num_emergency']}")
    print(f"   Duration: {config['duration']}s | "
          f"Noise: {config['noise_level']} | "
          f"Range: {config['communication_range']}m")
    print()

    # Create and setup engine
    engine = SimulationEngine(config)
    engine.setup()

    print("🔧 Simulation initialized")
    print(f"   Network: {engine.topology.get_node_count()} nodes, "
          f"{engine.topology.get_edge_count()} links")
    print(f"   Avg degree: {engine.topology.get_average_degree():.1f}")
    print()

    # Run simulation with progress
    def progress_cb(tick, total, sim_time):
        pct = (tick / total) * 100
        bar = '█' * int(pct / 2) + '░' * (50 - int(pct / 2))
        print(f"\r   ⏳ [{bar}] {pct:.0f}% (t={sim_time:.0f}s)", end='', flush=True)

    print("🚀 Running simulation...")
    start = time.time()
    kpis = engine.run(progress_callback=progress_cb)
    elapsed = time.time() - start
    print(f"\n   ✅ Completed in {elapsed:.2f}s real time\n")

    # Print event log highlights
    print("📜 KEY EVENTS:")
    print("   " + "─" * 55)
    event_types = {"ACCIDENT", "EMERGENCY", "EMERGENCY_SIGNAL", "SIMULATION_START", "SIMULATION_END"}
    for evt in engine.event_log:
        if evt["event"] in event_types:
            print(f"   [{evt['time']:6.1f}s] {evt['event']}: {evt['message']}")
    print()

    # Print KPIs
    kpi_text = engine.kpi_calculator.get_kpi_summary_text(kpis)
    print(kpi_text)

    # Generate visualizations
    print("\n📊 Generating visualizations...")
    viz = NetworkVisualizer(output_dir)
    dashboard = PerformanceDashboard(output_dir)

    # 1. Network topology
    topo_path = viz.visualize_topology(
        engine.topology, engine.vehicles, engine.signals,
        engine.controller, title=f"VANET Topology - {config.get('name', '')}",
        filename="01_network_topology.png", sim_time=engine.sim_time
    )
    print(f"   ✅ Network topology → {topo_path}")

    # 2. Find and visualize a routing path
    vehicle_ids = list(engine.vehicles.keys())
    if len(vehicle_ids) >= 2:
        src, dst = vehicle_ids[0], vehicle_ids[-1]
        route = engine.router.get_route(src, dst)
        if route:
            route_path = viz.visualize_topology(
                engine.topology, engine.vehicles, engine.signals,
                engine.controller,
                title=f"Routing Path: {src} → {dst} ({len(route)-1} hops)",
                filename="02_routing_path.png",
                highlight_route=route, sim_time=engine.sim_time
            )
            print(f"   ✅ Routing path → {route_path}")
            print(f"      Route: {' → '.join(route)}")

    # 3. Broadcast visualization
    accident_vehicles = [v for v in engine.vehicles.values() if v.has_accident]
    if accident_vehicles:
        av = accident_vehicles[0]
        reached = engine.topology.get_all_nodes()
        reached = [n for n in reached if n != av.node_id]
        bc_path = viz.visualize_broadcast(
            engine.topology, av.node_id, reached,
            filename="03_broadcast_propagation.png"
        )
        print(f"   ✅ Broadcast propagation → {bc_path}")
    elif vehicle_ids:
        # Simulate a broadcast from first vehicle
        reached = engine.topology.get_all_nodes()
        reached = [n for n in reached if n != vehicle_ids[0]]
        bc_path = viz.visualize_broadcast(
            engine.topology, vehicle_ids[0], reached,
            filename="03_broadcast_propagation.png"
        )
        print(f"   ✅ Broadcast propagation → {bc_path}")

    # 4. Performance dashboard
    dash_path = dashboard.generate_full_dashboard(
        engine.collector, kpis, filename="04_performance_dashboard.png"
    )
    print(f"   ✅ Performance dashboard → {dash_path}")

    # 5. Node analysis
    node_path = dashboard.generate_node_analysis(
        engine.collector, filename="05_node_analysis.png"
    )
    print(f"   ✅ Node analysis → {node_path}")

    # 6. Layer comparison
    layer_path = dashboard.generate_layer_comparison(
        kpis, filename="06_layer_comparison.png"
    )
    print(f"   ✅ Layer comparison → {layer_path}")

    # 7. BER vs Noise sweep
    print("\n🔬 Running BER vs Noise Level sweep...")
    noise_levels = [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.15, 0.2]
    ber_values = []
    for nl in noise_levels:
        ch = WirelessChannel(noise_level=nl, packet_loss_rate=0.01)
        test_data = "ACCIDENT_ALERT_TEST_DATA_FOR_BER_ANALYSIS"
        errors = 0
        total_bits = 0
        for _ in range(50):
            result = ch.transmit(test_data, "TEST_SRC", "TEST_DST", 100.0)
            if result:
                total_bits += ch.total_bits_sent
                errors += ch.total_bits_errored
        ber_values.append(errors / total_bits if total_bits > 0 else 0)
        ch.reset_metrics()
    ber_path = dashboard.generate_ber_vs_noise(noise_levels, ber_values, "07_ber_vs_noise.png")
    print(f"   ✅ BER vs Noise → {ber_path}")

    # 8. PDR vs Node Count sweep
    print("🔬 Running PDR vs Node Count sweep...")
    node_counts = [5, 10, 15, 20, 25, 30]
    pdr_values = []
    for nc in node_counts:
        sweep_config = dict(config)
        sweep_config["num_vehicles"] = nc
        sweep_config["duration"] = 20.0
        sweep_config["accident_probability"] = 0.005
        sweep_engine = SimulationEngine(sweep_config)
        sweep_engine.setup()
        sweep_kpis = sweep_engine.run()
        pdr_values.append(sweep_kpis.get("packet_delivery_ratio", 0))
    pdr_path = dashboard.generate_pdr_vs_nodes(node_counts, pdr_values, "08_pdr_vs_nodes.png")
    print(f"   ✅ PDR vs Nodes → {pdr_path}")

    print(f"\n{'='*60}")
    print(f"  📁 All outputs saved to: {os.path.abspath(output_dir)}/")
    print(f"  📊 Total graphs generated: 8")
    print(f"{'='*60}\n")

    return kpis, engine


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Smart Traffic Communication System - VANET Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Available scenarios: " + ", ".join(ScenarioManager.list_scenarios())
    )
    parser.add_argument('--scenario', '-s', type=str, default='basic',
                        choices=ScenarioManager.list_scenarios(),
                        help='Simulation scenario to run (default: basic)')
    parser.add_argument('--output', '-o', type=str, default='output',
                        help='Output directory for graphs (default: output)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility (default: 42)')

    args = parser.parse_args()

    # Set random seed
    random.seed(args.seed)

    print_banner()
    print_layer_explanation()

    kpis, engine = run_simulation(args.scenario, args.output)

    print("🎉 Simulation complete! Check the output directory for all visualizations.\n")


if __name__ == "__main__":
    main()
