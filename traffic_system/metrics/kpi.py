"""
KPI Calculator
==============
Computes Key Performance Indicators from collected metrics data.
Provides summary statistics for network performance evaluation.
"""

from typing import Dict, List, Optional
from .collector import MetricsCollector


class KPICalculator:
    """
    Computes KPIs from collected simulation metrics.

    KPIs computed:
    - Packet Delivery Ratio (PDR)
    - Average Latency
    - Throughput (bits/sec)
    - Packet Loss Rate
    - Routing Efficiency
    - Network Load
    - Bit Error Rate
    - Frame Error Rate
    """

    def __init__(self, collector: MetricsCollector):
        """
        Initialize KPI calculator.

        Args:
            collector: MetricsCollector instance with recorded data.
        """
        self.collector = collector

    def compute_all_kpis(self, total_time: float = None) -> dict:
        """
        Compute all KPIs from the collected metrics.

        Args:
            total_time: Total simulation time in seconds.

        Returns:
            Dictionary of all computed KPIs.
        """
        # Get latest metrics from each layer
        physical = self.collector.get_latest("physical") or {}
        datalink = self.collector.get_latest("datalink") or {}
        network = self.collector.get_latest("network") or {}
        system = self.collector.get_latest("system") or {}

        # Calculate time if not provided
        if total_time is None:
            snapshots = self.collector.get_all_snapshots()
            if snapshots:
                total_time = snapshots[-1].get("time", 1.0)
            else:
                total_time = 1.0

        kpis = {
            # Network Layer KPIs
            "packet_delivery_ratio": network.get("packet_delivery_ratio", 0.0),
            "average_latency_ms": network.get("average_latency_ms", 0.0),
            "average_hop_count": network.get("average_hop_count", 0.0),
            "total_packets_routed": network.get("total_packets_routed", 0),
            "total_packets_delivered": network.get("total_packets_delivered", 0),
            "total_packets_dropped": network.get("total_packets_dropped", 0),
            "packet_loss_rate": 1.0 - network.get("packet_delivery_ratio", 1.0),

            # Data Link Layer KPIs
            "frame_error_rate": datalink.get("frame_error_rate", 0.0),
            "total_retransmissions": datalink.get("total_retransmissions", 0),
            "delivery_rate": datalink.get("delivery_rate", 0.0),

            # Physical Layer KPIs
            "bit_error_rate": physical.get("bit_error_rate", 0.0),
            "signal_reliability": physical.get("signal_reliability", 1.0),

            # System KPIs
            "total_nodes": system.get("total_nodes", 0),
            "total_vehicles": system.get("total_vehicles", 0),
            "total_signals": system.get("total_signals", 0),
            "network_density": system.get("network_density", 0.0),
            "average_degree": system.get("average_degree", 0.0),

            # Computed KPIs
            "throughput_packets_per_sec": (
                network.get("total_packets_delivered", 0) / total_time
                if total_time > 0 else 0.0
            ),
            "routing_efficiency": self._compute_routing_efficiency(network),
            "network_load": self._compute_network_load(network, datalink, total_time),

            # Simulation info
            "simulation_duration_sec": total_time,
        }

        return kpis

    def _compute_routing_efficiency(self, network_metrics: dict) -> float:
        """
        Compute routing efficiency.
        Ratio of delivered packets to total routing overhead.
        """
        delivered = network_metrics.get("total_packets_delivered", 0)
        routed = network_metrics.get("total_packets_routed", 0)
        updates = network_metrics.get("routing_table_updates", 1)

        if routed == 0:
            return 0.0

        # Efficiency = delivered / (routed + routing_overhead)
        return delivered / (routed + updates * 0.1)

    def _compute_network_load(self, network_metrics: dict,
                               datalink_metrics: dict,
                               total_time: float) -> float:
        """
        Compute network load as packets per second per node.
        """
        total_frames = datalink_metrics.get("total_frames_sent", 0)
        total_packets = network_metrics.get("total_packets_routed", 0)
        total = total_frames + total_packets

        if total_time <= 0:
            return 0.0
        return total / total_time

    def get_kpi_summary_text(self, kpis: dict = None) -> str:
        """
        Generate formatted text summary of all KPIs.

        Args:
            kpis: Pre-computed KPIs dict, or None to compute fresh.

        Returns:
            Formatted KPI summary string.
        """
        if kpis is None:
            kpis = self.compute_all_kpis()

        lines = [
            "=" * 60,
            "      KEY PERFORMANCE INDICATORS (KPIs)",
            "=" * 60,
            "",
            "  📡 PHYSICAL LAYER",
            f"    Bit Error Rate (BER)    : {kpis['bit_error_rate']:.6f}",
            f"    Signal Reliability      : {kpis['signal_reliability']:.4f}",
            "",
            "  🔗 DATA LINK LAYER",
            f"    Frame Error Rate        : {kpis['frame_error_rate']:.6f}",
            f"    Total Retransmissions   : {kpis['total_retransmissions']}",
            f"    Delivery Rate           : {kpis['delivery_rate']:.4f}",
            "",
            "  🌐 NETWORK LAYER",
            f"    Packet Delivery Ratio   : {kpis['packet_delivery_ratio']:.4f}",
            f"    Average Latency         : {kpis['average_latency_ms']:.2f} ms",
            f"    Average Hop Count       : {kpis['average_hop_count']:.2f}",
            f"    Packet Loss Rate        : {kpis['packet_loss_rate']:.4f}",
            f"    Packets Routed          : {kpis['total_packets_routed']}",
            f"    Packets Delivered       : {kpis['total_packets_delivered']}",
            f"    Packets Dropped         : {kpis['total_packets_dropped']}",
            "",
            "  📊 SYSTEM",
            f"    Throughput              : {kpis['throughput_packets_per_sec']:.2f} pkts/sec",
            f"    Routing Efficiency      : {kpis['routing_efficiency']:.4f}",
            f"    Network Load            : {kpis['network_load']:.2f} operations/sec",
            f"    Total Nodes             : {kpis['total_nodes']}",
            f"    Network Density         : {kpis['network_density']:.4f}",
            f"    Avg Node Degree         : {kpis['average_degree']:.2f}",
            "",
            f"  ⏱  Simulation Duration    : {kpis['simulation_duration_sec']:.1f} sec",
            "=" * 60,
        ]
        return "\n".join(lines)

    def get_kpi_for_plotting(self) -> Dict[str, list]:
        """
        Get time-series KPI data suitable for plotting.

        Returns:
            Dict mapping metric name to (timestamps, values) tuples.
        """
        plot_data = {}

        # PDR over time
        times, values = self.collector.get_time_series("network", "packet_delivery_ratio")
        if times:
            plot_data["pdr_vs_time"] = (times, values)

        # Latency over time
        times, values = self.collector.get_time_series("network", "average_latency_ms")
        if times:
            plot_data["latency_vs_time"] = (times, values)

        # BER over time
        times, values = self.collector.get_time_series("physical", "bit_error_rate")
        if times:
            plot_data["ber_vs_time"] = (times, values)

        # Throughput over time
        times, values = self.collector.get_time_series("network", "total_packets_delivered")
        if times:
            plot_data["delivered_vs_time"] = (times, values)

        # Retransmissions over time
        times, values = self.collector.get_time_series("datalink", "total_retransmissions")
        if times:
            plot_data["retransmissions_vs_time"] = (times, values)

        # Frame error rate over time
        times, values = self.collector.get_time_series("datalink", "frame_error_rate")
        if times:
            plot_data["fer_vs_time"] = (times, values)

        # Node count over time
        times, values = self.collector.get_time_series("system", "total_nodes")
        if times:
            plot_data["nodes_vs_time"] = (times, values)

        return plot_data
