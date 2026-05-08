"""
Scenario Manager
================
Defines and manages predefined simulation scenarios
for testing different VANET communication situations.
"""

from typing import Dict, List


class ScenarioManager:
    """
    Manages predefined simulation scenarios.

    Each scenario defines specific configurations, events, and
    conditions to test different aspects of the VANET system.
    """

    @staticmethod
    def get_scenario(name: str) -> dict:
        """
        Get a predefined scenario configuration.

        Args:
            name: Scenario name.

        Returns:
            Configuration dictionary for the scenario.
        """
        scenarios = {
            "basic": ScenarioManager.basic_scenario(),
            "high_traffic": ScenarioManager.high_traffic_scenario(),
            "emergency": ScenarioManager.emergency_scenario(),
            "noisy_channel": ScenarioManager.noisy_channel_scenario(),
            "multi_accident": ScenarioManager.multi_accident_scenario(),
            "stress_test": ScenarioManager.stress_test_scenario(),
        }
        return scenarios.get(name, ScenarioManager.basic_scenario())

    @staticmethod
    def list_scenarios() -> List[str]:
        """List all available scenarios."""
        return [
            "basic", "high_traffic", "emergency",
            "noisy_channel", "multi_accident", "stress_test",
        ]

    @staticmethod
    def basic_scenario() -> dict:
        """Basic scenario with moderate traffic."""
        return {
            "name": "Basic Traffic Simulation",
            "description": "Moderate traffic with normal conditions",
            "num_vehicles": 12,
            "num_signals": 4,
            "num_emergency": 1,
            "communication_range": 300.0,
            "noise_level": 0.005,
            "packet_loss_rate": 0.01,
            "max_retries": 3,
            "arq_timeout": 0.5,
            "time_step": 1.0,
            "duration": 60.0,
            "world_size": (1000, 1000),
            "accident_probability": 0.01,
            "congestion_check_interval": 5.0,
            "metrics_interval": 2.0,
        }

    @staticmethod
    def high_traffic_scenario() -> dict:
        """High traffic density scenario."""
        return {
            "name": "High Traffic Density",
            "description": "Dense traffic with many vehicles and frequent congestion",
            "num_vehicles": 30,
            "num_signals": 6,
            "num_emergency": 3,
            "communication_range": 250.0,
            "noise_level": 0.008,
            "packet_loss_rate": 0.03,
            "max_retries": 3,
            "arq_timeout": 0.5,
            "time_step": 1.0,
            "duration": 90.0,
            "world_size": (1200, 1200),
            "accident_probability": 0.015,
            "congestion_check_interval": 3.0,
            "metrics_interval": 2.0,
        }

    @staticmethod
    def emergency_scenario() -> dict:
        """Scenario focused on emergency vehicle handling."""
        return {
            "name": "Emergency Response",
            "description": "Multiple emergency vehicles with priority signaling",
            "num_vehicles": 15,
            "num_signals": 5,
            "num_emergency": 5,
            "communication_range": 350.0,
            "noise_level": 0.003,
            "packet_loss_rate": 0.005,
            "max_retries": 4,
            "arq_timeout": 0.3,
            "time_step": 1.0,
            "duration": 60.0,
            "world_size": (1000, 1000),
            "accident_probability": 0.02,
            "congestion_check_interval": 5.0,
            "metrics_interval": 2.0,
        }

    @staticmethod
    def noisy_channel_scenario() -> dict:
        """Scenario with high channel noise and packet loss."""
        return {
            "name": "Noisy Channel",
            "description": "High noise and packet loss to stress error correction",
            "num_vehicles": 10,
            "num_signals": 4,
            "num_emergency": 1,
            "communication_range": 200.0,
            "noise_level": 0.05,
            "packet_loss_rate": 0.1,
            "max_retries": 5,
            "arq_timeout": 0.8,
            "time_step": 1.0,
            "duration": 60.0,
            "world_size": (800, 800),
            "accident_probability": 0.01,
            "congestion_check_interval": 5.0,
            "metrics_interval": 2.0,
        }

    @staticmethod
    def multi_accident_scenario() -> dict:
        """Scenario with high accident probability."""
        return {
            "name": "Multi-Accident Chain",
            "description": "High accident probability to test alert broadcasting",
            "num_vehicles": 20,
            "num_signals": 4,
            "num_emergency": 3,
            "communication_range": 300.0,
            "noise_level": 0.01,
            "packet_loss_rate": 0.02,
            "max_retries": 3,
            "arq_timeout": 0.5,
            "time_step": 1.0,
            "duration": 60.0,
            "world_size": (1000, 1000),
            "accident_probability": 0.05,
            "congestion_check_interval": 5.0,
            "metrics_interval": 2.0,
        }

    @staticmethod
    def stress_test_scenario() -> dict:
        """Stress test with maximum parameters."""
        return {
            "name": "Stress Test",
            "description": "Maximum nodes, noise, and events for stress testing",
            "num_vehicles": 40,
            "num_signals": 8,
            "num_emergency": 5,
            "communication_range": 350.0,
            "noise_level": 0.03,
            "packet_loss_rate": 0.05,
            "max_retries": 3,
            "arq_timeout": 0.5,
            "time_step": 1.0,
            "duration": 120.0,
            "world_size": (1500, 1500),
            "accident_probability": 0.02,
            "congestion_check_interval": 3.0,
            "metrics_interval": 3.0,
        }
