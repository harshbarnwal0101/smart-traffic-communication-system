"""
Performance Dashboard
=====================
Generates comprehensive performance analysis graphs for all KPIs.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import os
from typing import Dict, List, Tuple


class PerformanceDashboard:
    """Generates KPI visualization graphs for the VANET simulation."""

    COLORS = {
        "primary": "#4FC3F7", "secondary": "#FF5252",
        "accent": "#66BB6A", "warning": "#FDD835",
        "purple": "#AB47BC", "orange": "#FF9800",
        "background": "#1A1A2E", "text": "#E0E0E0",
        "grid": "#2C2C3E",
    }

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        plt.style.use('dark_background')

    def _style_ax(self, ax, title, xlabel, ylabel):
        ax.set_title(title, fontsize=13, color=self.COLORS["text"], fontweight='bold', pad=10)
        ax.set_xlabel(xlabel, color=self.COLORS["text"], fontsize=10)
        ax.set_ylabel(ylabel, color=self.COLORS["text"], fontsize=10)
        ax.tick_params(colors=self.COLORS["text"])
        ax.grid(True, alpha=0.2, color=self.COLORS["grid"])
        ax.set_facecolor(self.COLORS["background"])

    def generate_full_dashboard(self, collector, kpis: dict,
                                filename="performance_dashboard.png"):
        """Generate a comprehensive 3x2 performance dashboard."""
        fig, axes = plt.subplots(3, 2, figsize=(18, 20))
        fig.set_facecolor(self.COLORS["background"])
        fig.suptitle("VANET Performance Analysis Dashboard",
                     fontsize=18, color=self.COLORS["text"], fontweight='bold', y=0.98)

        # 1. PDR vs Time
        ax = axes[0, 0]
        t, v = collector.get_time_series("network", "packet_delivery_ratio")
        if t:
            ax.plot(t, v, color=self.COLORS["primary"], linewidth=2, marker='o', markersize=4)
            ax.fill_between(t, v, alpha=0.2, color=self.COLORS["primary"])
            ax.axhline(y=np.mean(v), color=self.COLORS["warning"], linestyle='--', alpha=0.7, label=f'Avg: {np.mean(v):.3f}')
            ax.legend(fontsize=8, facecolor='#2C2C3E')
        self._style_ax(ax, "Packet Delivery Ratio vs Time", "Time (s)", "PDR")
        ax.set_ylim(-0.05, 1.05)

        # 2. End-to-End Delay vs Time
        ax = axes[0, 1]
        t, v = collector.get_time_series("network", "average_latency_ms")
        if t:
            ax.plot(t, v, color=self.COLORS["secondary"], linewidth=2, marker='s', markersize=4)
            ax.fill_between(t, v, alpha=0.15, color=self.COLORS["secondary"])
            ax.axhline(y=np.mean(v), color=self.COLORS["warning"], linestyle='--', alpha=0.7, label=f'Avg: {np.mean(v):.2f}ms')
            ax.legend(fontsize=8, facecolor='#2C2C3E')
        self._style_ax(ax, "End-to-End Delay vs Time", "Time (s)", "Latency (ms)")

        # 3. Throughput vs Time
        ax = axes[1, 0]
        t, v = collector.get_time_series("network", "total_packets_delivered")
        if t and len(t) > 1:
            throughput = [0]
            for i in range(1, len(t)):
                dt = t[i] - t[i-1] if t[i] != t[i-1] else 1
                throughput.append((v[i] - v[i-1]) / dt if dt > 0 else 0)
            ax.bar(t, throughput, width=max(0.5, (t[-1]-t[0])/len(t)*0.8),
                   color=self.COLORS["accent"], alpha=0.8, edgecolor='white', linewidth=0.5)
        self._style_ax(ax, "Throughput vs Time", "Time (s)", "Packets/sec")

        # 4. BER vs Time
        ax = axes[1, 1]
        t, v = collector.get_time_series("physical", "bit_error_rate")
        if t:
            ax.plot(t, v, color=self.COLORS["orange"], linewidth=2, marker='^', markersize=4)
            ax.fill_between(t, v, alpha=0.15, color=self.COLORS["orange"])
        self._style_ax(ax, "Bit Error Rate vs Time", "Time (s)", "BER")

        # 5. Retransmissions vs Time
        ax = axes[2, 0]
        t, v = collector.get_time_series("datalink", "total_retransmissions")
        if t:
            ax.plot(t, v, color=self.COLORS["purple"], linewidth=2, marker='d', markersize=4)
            ax.fill_between(t, v, alpha=0.15, color=self.COLORS["purple"])
        self._style_ax(ax, "Retransmissions Over Time", "Time (s)", "Total Retransmissions")

        # 6. KPI Summary Bar Chart
        ax = axes[2, 1]
        kpi_names = ["PDR", "Signal\nReliability", "Delivery\nRate", "Routing\nEfficiency"]
        kpi_vals = [
            kpis.get("packet_delivery_ratio", 0),
            kpis.get("signal_reliability", 0),
            kpis.get("delivery_rate", 0),
            kpis.get("routing_efficiency", 0),
        ]
        colors = [self.COLORS["primary"], self.COLORS["accent"],
                  self.COLORS["warning"], self.COLORS["purple"]]
        bars = ax.bar(kpi_names, kpi_vals, color=colors, alpha=0.85,
                      edgecolor='white', linewidth=1)
        for bar, val in zip(bars, kpi_vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                    f'{val:.3f}', ha='center', va='bottom',
                    color=self.COLORS["text"], fontsize=10, fontweight='bold')
        self._style_ax(ax, "KPI Summary", "", "Value")
        ax.set_ylim(0, 1.2)

        plt.tight_layout(rect=[0, 0, 1, 0.96])
        filepath = os.path.join(self.output_dir, filename)
        fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)
        return filepath

    def generate_node_analysis(self, collector, filename="node_analysis.png"):
        """Generate node count and network density analysis."""
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))
        fig.set_facecolor(self.COLORS["background"])

        # Nodes over time
        ax = axes[0]
        t, v = collector.get_time_series("system", "total_nodes")
        if t:
            ax.plot(t, v, color=self.COLORS["primary"], linewidth=2, marker='o', markersize=3)
        self._style_ax(ax, "Active Nodes vs Time", "Time (s)", "Node Count")

        # Network density
        ax = axes[1]
        t, v = collector.get_time_series("system", "network_density")
        if t:
            ax.plot(t, v, color=self.COLORS["accent"], linewidth=2, marker='s', markersize=3)
            ax.fill_between(t, v, alpha=0.2, color=self.COLORS["accent"])
        self._style_ax(ax, "Network Density vs Time", "Time (s)", "Density")

        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)
        return filepath

    def generate_layer_comparison(self, kpis: dict, filename="layer_comparison.png"):
        """Generate a layer-by-layer performance comparison chart."""
        fig, ax = plt.subplots(figsize=(12, 7))
        fig.set_facecolor(self.COLORS["background"])
        ax.set_facecolor(self.COLORS["background"])

        categories = ['Physical\nLayer', 'Data Link\nLayer', 'Network\nLayer']
        metrics = {
            'Reliability': [
                kpis.get("signal_reliability", 0),
                kpis.get("delivery_rate", 0),
                kpis.get("packet_delivery_ratio", 0),
            ],
            'Error Rate': [
                min(1, kpis.get("bit_error_rate", 0) * 100),
                min(1, kpis.get("frame_error_rate", 0) * 100),
                min(1, kpis.get("packet_loss_rate", 0) * 100),
            ],
        }

        x = np.arange(len(categories))
        width = 0.3
        colors_list = [self.COLORS["accent"], self.COLORS["secondary"]]

        for i, (label, values) in enumerate(metrics.items()):
            bars = ax.bar(x + i * width, values, width, label=label,
                          color=colors_list[i], alpha=0.85, edgecolor='white')
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                        f'{val:.4f}', ha='center', va='bottom',
                        color=self.COLORS["text"], fontsize=9)

        ax.set_xticks(x + width / 2)
        ax.set_xticklabels(categories)
        ax.legend(fontsize=10, facecolor='#2C2C3E', edgecolor='#555', labelcolor=self.COLORS["text"])
        self._style_ax(ax, "Layer-by-Layer Performance Comparison", "", "Value")

        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)
        return filepath

    def generate_ber_vs_noise(self, noise_levels, ber_values, filename="ber_vs_noise.png"):
        """Generate BER vs Noise Level plot from sweep data."""
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.set_facecolor(self.COLORS["background"])
        ax.set_facecolor(self.COLORS["background"])
        ax.plot(noise_levels, ber_values, color=self.COLORS["orange"],
                linewidth=2.5, marker='o', markersize=8, markeredgecolor='white')
        ax.fill_between(noise_levels, ber_values, alpha=0.15, color=self.COLORS["orange"])
        self._style_ax(ax, "Bit Error Rate vs Noise Level", "Noise Level", "BER")
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)
        return filepath

    def generate_pdr_vs_nodes(self, node_counts, pdr_values, filename="pdr_vs_nodes.png"):
        """Generate PDR vs Number of Nodes plot from sweep data."""
        fig, ax = plt.subplots(figsize=(10, 6))
        fig.set_facecolor(self.COLORS["background"])
        ax.set_facecolor(self.COLORS["background"])
        ax.plot(node_counts, pdr_values, color=self.COLORS["primary"],
                linewidth=2.5, marker='s', markersize=8, markeredgecolor='white')
        ax.fill_between(node_counts, pdr_values, alpha=0.15, color=self.COLORS["primary"])
        self._style_ax(ax, "Packet Delivery Ratio vs Number of Nodes", "Number of Nodes", "PDR")
        ax.set_ylim(-0.05, 1.05)
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)
        return filepath
