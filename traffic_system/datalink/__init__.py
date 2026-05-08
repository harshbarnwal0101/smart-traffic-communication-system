"""
Data Link Layer Module
======================
Implements framing, CRC error detection, acknowledgment system,
and ARQ retransmission protocol for reliable data transfer.
"""

from .frame import Frame, FrameType
from .crc import CRC16
from .arq import StopAndWaitARQ

__all__ = ["Frame", "FrameType", "CRC16", "StopAndWaitARQ"]
