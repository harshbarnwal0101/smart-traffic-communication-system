"""
Frame Structure
===============
Defines the frame format for the Data Link Layer.
Frame: [START | TYPE | SEQ | SOURCE | DEST | LENGTH | DATA | CRC | END]

Each frame carries data between adjacent nodes with error detection
and sequencing for reliable delivery.
"""

import json
from enum import Enum
from typing import Optional
from .crc import CRC16


class FrameType(Enum):
    """Types of frames in the data link protocol."""
    DATA = "DATA"
    ACK = "ACK"
    NACK = "NACK"
    BEACON = "BEACON"  # Periodic neighbor discovery


class Frame:
    """
    Data Link Layer frame with CRC error detection.

    Frame structure:
    ┌───────┬──────┬─────┬────────┬──────┬────────┬──────┬─────┬─────┐
    │ START │ TYPE │ SEQ │ SOURCE │ DEST │ LENGTH │ DATA │ CRC │ END │
    └───────┴──────┴─────┴────────┴──────┴────────┴──────┴─────┴─────┘
    """

    START_DELIMITER = "<<SOF>>"
    END_DELIMITER = "<<EOF>>"
    FIELD_SEPARATOR = "|"

    def __init__(self, frame_type: FrameType, seq_num: int,
                 source: str, destination: str, data: str = ""):
        """
        Create a new frame.

        Args:
            frame_type: Type of frame (DATA, ACK, NACK, BEACON).
            seq_num: Sequence number for ordering and ARQ.
            source: Source node ID.
            destination: Destination node ID.
            data: Payload data string.
        """
        self.frame_type = frame_type
        self.seq_num = seq_num
        self.source = source
        self.destination = destination
        self.data = data
        self.length = len(data)
        self.crc = self._compute_crc()
        self.timestamp = None
        self.hop_count = 0

    def _compute_crc(self) -> str:
        """Compute CRC for the frame's content (type + seq + source + dest + data)."""
        content = f"{self.frame_type.value}{self.seq_num}{self.source}{self.destination}{self.data}"
        return CRC16.compute(content)

    def verify_crc(self) -> bool:
        """Verify the frame's CRC checksum."""
        content = f"{self.frame_type.value}{self.seq_num}{self.source}{self.destination}{self.data}"
        return CRC16.verify(content, self.crc)

    def serialize(self) -> str:
        """
        Serialize frame to string for transmission.

        Returns:
            Serialized frame string.
        """
        fields = [
            self.START_DELIMITER,
            self.frame_type.value,
            str(self.seq_num),
            self.source,
            self.destination,
            str(self.length),
            self.data,
            self.crc,
            self.END_DELIMITER,
        ]
        return self.FIELD_SEPARATOR.join(fields)

    @classmethod
    def deserialize(cls, frame_string: str) -> Optional['Frame']:
        """
        Deserialize a frame from its string representation.

        Args:
            frame_string: Serialized frame string.

        Returns:
            Frame object or None if parsing fails.
        """
        try:
            fields = frame_string.split(cls.FIELD_SEPARATOR)

            if len(fields) < 9:
                return None
            if fields[0] != cls.START_DELIMITER or fields[-1] != cls.END_DELIMITER:
                return None

            frame_type = FrameType(fields[1])
            seq_num = int(fields[2])
            source = fields[3]
            destination = fields[4]
            # fields[5] is length
            data = fields[6]
            received_crc = fields[7]

            frame = cls(frame_type, seq_num, source, destination, data)
            frame.crc = received_crc  # Use received CRC (may be corrupted)

            return frame
        except (ValueError, IndexError, KeyError):
            return None

    def is_ack(self) -> bool:
        """Check if this is an ACK frame."""
        return self.frame_type == FrameType.ACK

    def is_nack(self) -> bool:
        """Check if this is a NACK frame."""
        return self.frame_type == FrameType.NACK

    def is_data(self) -> bool:
        """Check if this is a DATA frame."""
        return self.frame_type == FrameType.DATA

    def create_ack(self) -> 'Frame':
        """Create an ACK frame in response to this frame."""
        return Frame(FrameType.ACK, self.seq_num, self.destination, self.source, "ACK")

    def create_nack(self) -> 'Frame':
        """Create a NACK frame in response to this frame."""
        return Frame(FrameType.NACK, self.seq_num, self.destination, self.source, "NACK")

    def __repr__(self) -> str:
        return (f"Frame(type={self.frame_type.value}, seq={self.seq_num}, "
                f"src={self.source}, dst={self.destination}, "
                f"len={self.length}, crc={self.crc})")
