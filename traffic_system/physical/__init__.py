"""
Physical Layer Module
=====================
Handles bit-level transmission, noise simulation, signal attenuation,
and channel modeling for the VANET communication system.
"""

from .channel import WirelessChannel
from .transmitter import PhysicalTransmitter

__all__ = ["WirelessChannel", "PhysicalTransmitter"]
