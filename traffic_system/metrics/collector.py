"""
Metrics Collector
=================
Centralized metrics collection for all layers of the VANET simulation.
Collects time-series data for performance analysis and visualization.
"""

import time
from typing import Dict, List, Optional, Any
from collections import defaultdict


class MetricsCollector:
    """
    Centralized metrics collection system.
    
    Collects and stores time-series data from all simulation layers
    for post-simulation analysis and real-time dashboard updates.
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.start_time = time.time()
        self.metrics_data: Dict[str, List[dict]] = defaultdict(list)
        self.snapshots: List[dict] = []
        self.event_counts: Dict[str, int] = defaultdict(int)

        # Time-series storage for each metric category
        self.physical_metrics: List[dict] = []
        self.datalink_metrics: List[dict] = []
        self.network_metrics: List[dict] = []
        self.system_metrics: List[dict] = []

    def record(self, category: str, metrics: dict, sim_time: float = None):
        """
        Record a metrics snapshot.

        Args:
            category: Metric category (e.g., 'physical', 'datalink', 'network').
            metrics: Dictionary of metric values.
            sim_time: Simulation time for this snapshot.
        """
        entry = {
            "timestamp": sim_time if sim_time is not None else time.time() - self.start_time,
            "category": category,
            **metrics,
        }

        self.metrics_data[category].append(entry)

        # Store in typed lists for easy access
        if category == "physical":
            self.physical_metrics.append(entry)
        elif category == "datalink":
            self.datalink_metrics.append(entry)
        elif category == "network":
            self.network_metrics.append(entry)
        elif category == "system":
            self.system_metrics.append(entry)

    def record_event(self, event_type: str, details: dict = None, sim_time: float = None):
        """Record a discrete event."""
        self.event_counts[event_type] += 1
        self.metrics_data["events"].append({
            "timestamp": sim_time if sim_time is not None else time.time() - self.start_time,
            "event": event_type,
            "count": self.event_counts[event_type],
            **(details or {}),
        })

    def take_snapshot(self, sim_time: float, physical: dict, datalink: dict,
                      network: dict, system: dict):
        """
        Take a comprehensive snapshot of all metrics at a point in time.

        Args:
            sim_time: Current simulation time.
            physical: Physical layer metrics.
            datalink: Data link layer metrics.
            network: Network layer metrics.
            system: System-level metrics.
        """
        snapshot = {
            "time": sim_time,
            "physical": physical,
            "datalink": datalink,
            "network": network,
            "system": system,
        }
        self.snapshots.append(snapshot)

        # Record individual categories
        self.record("physical", physical, sim_time)
        self.record("datalink", datalink, sim_time)
        self.record("network", network, sim_time)
        self.record("system", system, sim_time)

    def get_time_series(self, category: str, metric_name: str) -> tuple:
        """
        Extract time-series data for a specific metric.

        Args:
            category: Metric category.
            metric_name: Name of the metric field.

        Returns:
            Tuple of (timestamps, values).
        """
        data = self.metrics_data.get(category, [])
        timestamps = []
        values = []
        for entry in data:
            if metric_name in entry:
                timestamps.append(entry["timestamp"])
                values.append(entry[metric_name])
        return timestamps, values

    def get_latest(self, category: str) -> Optional[dict]:
        """Get the latest metrics entry for a category."""
        data = self.metrics_data.get(category, [])
        return data[-1] if data else None

    def get_all_snapshots(self) -> List[dict]:
        """Get all snapshots."""
        return self.snapshots

    def get_event_summary(self) -> Dict[str, int]:
        """Get summary of all events."""
        return dict(self.event_counts)

    def get_metric_names(self, category: str) -> List[str]:
        """Get all metric names recorded for a category."""
        data = self.metrics_data.get(category, [])
        if not data:
            return []
        names = set()
        for entry in data:
            names.update(k for k in entry.keys() if k not in ("timestamp", "category"))
        return sorted(names)

    def export_csv(self, category: str, filepath: str):
        """Export metrics data to CSV file."""
        import csv
        data = self.metrics_data.get(category, [])
        if not data:
            return

        fieldnames = set()
        for entry in data:
            fieldnames.update(entry.keys())
        fieldnames = sorted(fieldnames)

        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

    def reset(self):
        """Reset all collected metrics."""
        self.start_time = time.time()
        self.metrics_data.clear()
        self.snapshots.clear()
        self.event_counts.clear()
        self.physical_metrics.clear()
        self.datalink_metrics.clear()
        self.network_metrics.clear()
        self.system_metrics.clear()
