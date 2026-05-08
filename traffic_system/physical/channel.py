"""
Wireless Channel Model
======================
Simulates a wireless communication channel with configurable noise,
signal attenuation, packet loss, and propagation delay for VANET.

Key features:
- Binary data encoding/decoding
- Gaussian noise injection with configurable BER
- Distance-based signal attenuation
- Random packet loss simulation
- Propagation delay modeling
"""

import random
import time
import math
from typing import Optional, Tuple, List


class WirelessChannel:
    """
    Models a wireless communication channel between two VANET nodes.
    
    The channel introduces realistic impairments including:
    - Bit errors (noise-induced bit flipping)
    - Packet loss (complete transmission failure)
    - Propagation delay (distance-dependent)
    - Signal attenuation (path loss model)
    """

    # Speed of light in m/s (for propagation delay)
    SPEED_OF_LIGHT = 3e8
    # Reference distance for path loss model (meters)
    REFERENCE_DISTANCE = 1.0
    # Path loss exponent for urban VANET environment
    PATH_LOSS_EXPONENT = 2.7
    # Maximum communication range in meters
    MAX_RANGE = 300.0

    def __init__(self, noise_level: float = 0.01, packet_loss_rate: float = 0.02,
                 max_range: float = 300.0):
        """
        Initialize wireless channel.

        Args:
            noise_level: Probability of flipping each bit (0.0 to 1.0).
            packet_loss_rate: Probability of losing entire packet (0.0 to 1.0).
            max_range: Maximum communication range in meters.
        """
        self.noise_level = max(0.0, min(1.0, noise_level))
        self.packet_loss_rate = max(0.0, min(1.0, packet_loss_rate))
        self.max_range = max_range

        # Metrics tracking
        self.total_bits_sent = 0
        self.total_bits_errored = 0
        self.total_packets_sent = 0
        self.total_packets_lost = 0
        self.total_packets_delivered = 0
        self.transmission_log: List[dict] = []

    @staticmethod
    def text_to_binary(text: str) -> str:
        """Convert text string to binary representation."""
        return ''.join(format(ord(c), '08b') for c in text)

    @staticmethod
    def binary_to_text(binary: str) -> str:
        """Convert binary string back to text."""
        chars = []
        for i in range(0, len(binary), 8):
            byte = binary[i:i + 8]
            if len(byte) == 8:
                chars.append(chr(int(byte, 2)))
        return ''.join(chars)

    def calculate_distance_attenuation(self, distance: float) -> float:
        """
        Calculate signal attenuation based on distance using log-distance path loss model.

        Args:
            distance: Distance between transmitter and receiver in meters.

        Returns:
            Attenuation factor (0.0 = total loss, 1.0 = no loss).
        """
        if distance <= 0:
            return 1.0
        if distance > self.max_range:
            return 0.0

        # Log-distance path loss model
        path_loss_db = 10 * self.PATH_LOSS_EXPONENT * math.log10(
            max(distance, self.REFERENCE_DISTANCE) / self.REFERENCE_DISTANCE
        )
        # Convert to linear scale and invert (higher loss = lower signal)
        attenuation = max(0.0, 1.0 - (path_loss_db / (10 * self.PATH_LOSS_EXPONENT *
                                                        math.log10(self.max_range))))
        return attenuation

    def calculate_effective_noise(self, distance: float) -> float:
        """
        Calculate effective noise level based on distance.
        Noise increases with distance due to weaker signal.

        Args:
            distance: Distance between nodes in meters.

        Returns:
            Effective noise probability per bit.
        """
        attenuation = self.calculate_distance_attenuation(distance)
        if attenuation <= 0:
            return 1.0  # Complete signal loss
        # Noise increases as signal weakens
        effective_noise = self.noise_level / attenuation
        return min(1.0, effective_noise)

    def inject_noise(self, binary_data: str, distance: float = 10.0) -> Tuple[str, int]:
        """
        Simulate noise by randomly flipping bits in binary data.

        Args:
            binary_data: Binary string to transmit.
            distance: Distance between transmitter and receiver.

        Returns:
            Tuple of (corrupted binary data, number of bit errors).
        """
        effective_noise = self.calculate_effective_noise(distance)
        corrupted = list(binary_data)
        error_count = 0

        for i in range(len(corrupted)):
            if random.random() < effective_noise:
                corrupted[i] = '0' if corrupted[i] == '1' else '1'
                error_count += 1

        return ''.join(corrupted), error_count

    def calculate_propagation_delay(self, distance: float) -> float:
        """
        Calculate propagation delay based on distance.

        Args:
            distance: Distance in meters.

        Returns:
            Delay in seconds.
        """
        # Propagation delay + processing delay (simulated)
        propagation = distance / self.SPEED_OF_LIGHT
        processing = random.uniform(0.001, 0.005)  # 1-5 ms processing
        return propagation + processing

    def transmit(self, data: str, source_id: str, dest_id: str,
                 distance: float = 10.0) -> Optional[Tuple[str, dict]]:
        """
        Transmit data through the wireless channel.

        Args:
            data: Text data to transmit.
            source_id: Source node identifier.
            dest_id: Destination node identifier.
            distance: Distance between source and destination in meters.

        Returns:
            Tuple of (received data, transmission stats) or None if packet lost.
        """
        self.total_packets_sent += 1

        # Check if nodes are in range
        if distance > self.max_range:
            stats = {
                "source": source_id,
                "destination": dest_id,
                "distance": distance,
                "status": "OUT_OF_RANGE",
                "packet_lost": True,
            }
            self.total_packets_lost += 1
            self.transmission_log.append(stats)
            return None

        # Simulate packet loss
        loss_probability = self.packet_loss_rate * (1 + distance / self.max_range)
        if random.random() < min(loss_probability, 0.5):
            stats = {
                "source": source_id,
                "destination": dest_id,
                "distance": distance,
                "status": "PACKET_LOST",
                "packet_lost": True,
            }
            self.total_packets_lost += 1
            self.transmission_log.append(stats)
            return None

        # Convert to binary
        binary_data = self.text_to_binary(data)
        original_bits = len(binary_data)
        self.total_bits_sent += original_bits

        # Inject noise
        corrupted_binary, bit_errors = self.inject_noise(binary_data, distance)
        self.total_bits_errored += bit_errors

        # Calculate delay
        delay = self.calculate_propagation_delay(distance)

        # Simulate transmission delay
        time.sleep(min(delay, 0.01))  # Cap at 10ms for simulation speed

        # Convert back to text
        received_data = self.binary_to_text(corrupted_binary)

        self.total_packets_delivered += 1

        stats = {
            "source": source_id,
            "destination": dest_id,
            "distance": distance,
            "original_bits": original_bits,
            "bit_errors": bit_errors,
            "ber": bit_errors / original_bits if original_bits > 0 else 0,
            "delay_ms": delay * 1000,
            "attenuation": self.calculate_distance_attenuation(distance),
            "status": "DELIVERED",
            "packet_lost": False,
            "data_corrupted": (data != received_data),
        }
        self.transmission_log.append(stats)

        return received_data, stats

    def get_ber(self) -> float:
        """Calculate overall Bit Error Rate."""
        if self.total_bits_sent == 0:
            return 0.0
        return self.total_bits_errored / self.total_bits_sent

    def get_packet_loss_rate(self) -> float:
        """Calculate overall Packet Loss Rate."""
        if self.total_packets_sent == 0:
            return 0.0
        return self.total_packets_lost / self.total_packets_sent

    def get_signal_reliability(self) -> float:
        """Calculate signal reliability (1 - packet_loss_rate)."""
        return 1.0 - self.get_packet_loss_rate()

    def get_metrics(self) -> dict:
        """Get comprehensive channel metrics."""
        return {
            "total_bits_sent": self.total_bits_sent,
            "total_bits_errored": self.total_bits_errored,
            "bit_error_rate": self.get_ber(),
            "total_packets_sent": self.total_packets_sent,
            "total_packets_lost": self.total_packets_lost,
            "total_packets_delivered": self.total_packets_delivered,
            "packet_loss_rate": self.get_packet_loss_rate(),
            "signal_reliability": self.get_signal_reliability(),
            "noise_level": self.noise_level,
        }

    def reset_metrics(self):
        """Reset all channel metrics."""
        self.total_bits_sent = 0
        self.total_bits_errored = 0
        self.total_packets_sent = 0
        self.total_packets_lost = 0
        self.total_packets_delivered = 0
        self.transmission_log.clear()
