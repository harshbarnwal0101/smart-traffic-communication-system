"""
Network Visualizer
==================
Visualizes the VANET network topology, node positions,
routing paths, and packet flow using matplotlib and networkx.
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import networkx as nx
import os
from typing import List, Optional


class NetworkVisualizer:
    """VANET network visualizer using matplotlib and networkx."""

    COLORS = {
        "vehicle": "#4FC3F7", "emergency": "#FF5252",
        "emergency_active": "#FF1744", "signal_green": "#66BB6A",
        "signal_yellow": "#FDD835", "signal_red": "#EF5350",
        "controller": "#AB47BC", "accident": "#FF6D00",
        "congested": "#FFD600", "edge": "#B0BEC5",
        "route": "#2196F3", "broadcast": "#FF9800",
        "background": "#1A1A2E", "text": "#E0E0E0",
    }

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        plt.style.use('dark_background')

    def visualize_topology(self, topology, vehicles, signals,
                           controller=None, title="VANET Network Topology",
                           filename="network_topology.png",
                           highlight_route=None, sim_time=0.0):
        """Generate network topology visualization."""
        fig, ax = plt.subplots(1, 1, figsize=(14, 12))
        fig.set_facecolor(self.COLORS["background"])
        ax.set_facecolor(self.COLORS["background"])
        graph = topology.get_graph()
        pos = topology.node_positions
        if not pos:
            plt.close(fig)
            return None

        # Draw edges
        ec, ew = [], []
        for u, v in graph.edges():
            if highlight_route and u in highlight_route and v in highlight_route:
                iu, iv = highlight_route.index(u), highlight_route.index(v)
                if abs(iu - iv) == 1:
                    ec.append(self.COLORS["route"]); ew.append(3.0); continue
            ec.append(self.COLORS["edge"]); ew.append(0.5)
        if graph.edges():
            nx.draw_networkx_edges(graph, pos, ax=ax, edge_color=ec, width=ew, alpha=0.4, style='dashed')

        # Categorize and draw nodes
        vn, vc, vs_list = [], [], []
        sn, sc = [], []
        cn, an = [], []
        for nid in graph.nodes():
            if nid in vehicles:
                veh = vehicles[nid]
                if veh.has_accident:
                    an.append(nid)
                else:
                    vn.append(nid)
                    if veh.is_emergency and veh.emergency_active:
                        vc.append(self.COLORS["emergency_active"]); vs_list.append(400)
                    elif veh.is_emergency:
                        vc.append(self.COLORS["emergency"]); vs_list.append(350)
                    elif veh.is_congested:
                        vc.append(self.COLORS["congested"]); vs_list.append(250)
                    else:
                        vc.append(self.COLORS["vehicle"]); vs_list.append(250)
            elif nid in signals:
                sig = signals[nid]; sn.append(nid)
                sc.append(self.COLORS[f"signal_{sig.current_phase.value.lower()}"])
            elif controller and nid == controller.node_id:
                cn.append(nid)
        if vn:
            nx.draw_networkx_nodes(graph, pos, nodelist=vn, node_color=vc,
                                   node_size=vs_list, ax=ax, edgecolors='white', linewidths=1.5)
        if an:
            nx.draw_networkx_nodes(graph, pos, nodelist=an, node_color=self.COLORS["accident"],
                                   node_size=500, node_shape='X', ax=ax, edgecolors='white', linewidths=2)
        if sn:
            nx.draw_networkx_nodes(graph, pos, nodelist=sn, node_color=sc,
                                   node_size=450, node_shape='s', ax=ax, edgecolors='white', linewidths=2)
        if cn:
            nx.draw_networkx_nodes(graph, pos, nodelist=cn, node_color=self.COLORS["controller"],
                                   node_size=600, node_shape='D', ax=ax, edgecolors='white', linewidths=2)

        # Labels
        labels = {}
        for nid in graph.nodes():
            if nid in vehicles:
                labels[nid] = f"{nid}\n{vehicles[nid].speed:.0f}km/h"
            elif nid in signals:
                labels[nid] = f"{nid}\n{signals[nid].current_phase.value}"
            else:
                labels[nid] = nid
        nx.draw_networkx_labels(graph, pos, labels, font_size=6,
                                font_color=self.COLORS["text"], font_weight='bold', ax=ax)

        # Route highlight
        if highlight_route and len(highlight_route) > 1:
            rx = [pos[n][0] for n in highlight_route if n in pos]
            ry = [pos[n][1] for n in highlight_route if n in pos]
            ax.plot(rx, ry, color=self.COLORS["route"], linewidth=3, alpha=0.8, marker='>', markersize=8)

        # Legend
        leg = [
            Line2D([0],[0], marker='o', color='w', markerfacecolor=self.COLORS["vehicle"], markersize=10, label='Vehicle', linestyle='None'),
            Line2D([0],[0], marker='o', color='w', markerfacecolor=self.COLORS["emergency"], markersize=10, label='Emergency', linestyle='None'),
            Line2D([0],[0], marker='X', color='w', markerfacecolor=self.COLORS["accident"], markersize=12, label='Accident', linestyle='None'),
            Line2D([0],[0], marker='s', color='w', markerfacecolor=self.COLORS["signal_green"], markersize=10, label='Signal(GREEN)', linestyle='None'),
            Line2D([0],[0], marker='s', color='w', markerfacecolor=self.COLORS["signal_red"], markersize=10, label='Signal(RED)', linestyle='None'),
            Line2D([0],[0], marker='D', color='w', markerfacecolor=self.COLORS["controller"], markersize=10, label='Controller', linestyle='None'),
        ]
        ax.legend(handles=leg, loc='upper left', fontsize=8, facecolor='#2C2C3E',
                  edgecolor='#555', labelcolor=self.COLORS["text"], framealpha=0.9)
        ax.set_title(f"{title}\nTime: {sim_time:.1f}s | Nodes: {topology.get_node_count()} | Links: {topology.get_edge_count()}",
                     fontsize=14, color=self.COLORS["text"], fontweight='bold', pad=15)
        ax.set_xlabel("X (meters)", color=self.COLORS["text"])
        ax.set_ylabel("Y (meters)", color=self.COLORS["text"])
        ax.grid(True, alpha=0.15)
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)
        return filepath

    def visualize_broadcast(self, topology, source, reached_nodes,
                            filename="broadcast.png"):
        """Visualize broadcast propagation from a source node."""
        fig, ax = plt.subplots(1, 1, figsize=(14, 12))
        fig.set_facecolor(self.COLORS["background"])
        ax.set_facecolor(self.COLORS["background"])
        graph = topology.get_graph()
        pos = topology.node_positions
        nx.draw_networkx_edges(graph, pos, ax=ax, edge_color=self.COLORS["edge"], width=0.5, alpha=0.3)
        all_n = list(graph.nodes())
        nc, ns = [], []
        for n in all_n:
            if n == source:
                nc.append(self.COLORS["accident"]); ns.append(600)
            elif n in reached_nodes:
                nc.append("#81C784"); ns.append(300)
            else:
                nc.append("#616161"); ns.append(200)
        nx.draw_networkx_nodes(graph, pos, nodelist=all_n, node_color=nc, node_size=ns, ax=ax, edgecolors='white', linewidths=1.5)
        nx.draw_networkx_labels(graph, pos, font_size=7, font_color=self.COLORS["text"], ax=ax)
        rpct = len(reached_nodes) / max(1, len(all_n)-1) * 100
        ax.set_title(f"Broadcast from {source} | Reached: {len(reached_nodes)}/{len(all_n)-1} ({rpct:.0f}%)",
                     fontsize=14, color=self.COLORS["text"], fontweight='bold')
        ax.grid(True, alpha=0.15)
        plt.tight_layout()
        filepath = os.path.join(self.output_dir, filename)
        fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close(fig)
        return filepath
