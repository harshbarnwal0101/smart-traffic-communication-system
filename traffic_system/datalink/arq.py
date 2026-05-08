"""
ARQ (Automatic Repeat reQuest) Protocol
========================================
Implements Stop-and-Wait ARQ for reliable data transfer
in the Data Link Layer. Handles retransmission on errors
with configurable timeout and retry limits.
"""

import time
import logging
from typing import Optional, Tuple, List, Callable
from .frame import Frame, FrameType
from .crc import CRC16

logger = logging.getLogger(__name__)


class StopAndWaitARQ:
    """
    Stop-and-Wait ARQ protocol implementation.

    Protocol flow:
    1. Sender transmits frame
    2. Sender waits for ACK/NACK
    3. On ACK: send next frame
    4. On NACK or timeout: retransmit
    5. After max retries: report failure
    """

    def __init__(self, max_retries: int = 3, timeout: float = 0.5):
        """
        Initialize ARQ protocol.

        Args:
            max_retries: Maximum retransmission attempts per frame.
            timeout: Timeout in seconds before retransmission.
        """
        self.max_retries = max_retries
        self.timeout = timeout
        self.seq_num = 0

        # Metrics
        self.total_frames_sent = 0
        self.total_frames_received = 0
        self.total_retransmissions = 0
        self.total_acks_sent = 0
        self.total_nacks_sent = 0
        self.total_frames_dropped = 0
        self.successful_deliveries = 0
        self.frame_errors_detected = 0
        self.transmission_history: List[dict] = []

    def create_data_frame(self, source: str, destination: str, data: str) -> Frame:
        """
        Create a new data frame with current sequence number.

        Args:
            source: Source node ID.
            destination: Destination node ID.
            data: Payload data.

        Returns:
            New Frame object.
        """
        frame = Frame(FrameType.DATA, self.seq_num, source, destination, data)
        self.seq_num = (self.seq_num + 1) % 256  # Wrap around at 256
        return frame

    def send_with_arq(self, frame: Frame,
                      transmit_fn: Callable[[str], Optional[str]],
                      source_id: str) -> Tuple[bool, dict]:
        """
        Send a frame using Stop-and-Wait ARQ protocol.

        Args:
            frame: Frame to send.
            transmit_fn: Function that transmits serialized frame and returns
                        received response string or None if transmission failed.
            source_id: ID of the sending node.

        Returns:
            Tuple of (success: bool, stats: dict).
        """
        attempt = 0
        success = False
        stats = {
            "frame_seq": frame.seq_num,
            "source": frame.source,
            "destination": frame.destination,
            "attempts": 0,
            "retransmissions": 0,
            "final_status": "FAILED",
            "data_size": len(frame.data),
        }

        serialized = frame.serialize()

        while attempt <= self.max_retries:
            attempt += 1
            stats["attempts"] = attempt
            self.total_frames_sent += 1

            logger.debug(f"[ARQ] Sending frame seq={frame.seq_num} attempt={attempt} "
                         f"from {frame.source} to {frame.destination}")

            # Transmit the frame
            response = transmit_fn(serialized)

            if response is None:
                # Transmission failed (packet lost in physical layer)
                logger.debug(f"[ARQ] Frame seq={frame.seq_num} lost in transmission")
                if attempt <= self.max_retries:
                    self.total_retransmissions += 1
                    stats["retransmissions"] += 1
                    time.sleep(min(self.timeout * 0.01, 0.01))  # Brief wait before retry
                continue

            # Try to parse the response as a frame
            response_frame = Frame.deserialize(response)

            if response_frame is None:
                # Response corrupted
                logger.debug(f"[ARQ] Response corrupted for frame seq={frame.seq_num}")
                if attempt <= self.max_retries:
                    self.total_retransmissions += 1
                    stats["retransmissions"] += 1
                continue

            if response_frame.is_ack() and response_frame.seq_num == frame.seq_num:
                # ACK received successfully
                success = True
                self.successful_deliveries += 1
                stats["final_status"] = "DELIVERED"
                logger.debug(f"[ARQ] ACK received for frame seq={frame.seq_num}")
                break
            elif response_frame.is_nack():
                # NACK received - retransmit
                logger.debug(f"[ARQ] NACK received for frame seq={frame.seq_num}")
                self.total_nacks_sent += 1
                self.frame_errors_detected += 1
                if attempt <= self.max_retries:
                    self.total_retransmissions += 1
                    stats["retransmissions"] += 1
                continue

        if not success:
            self.total_frames_dropped += 1
            stats["final_status"] = "DROPPED"
            logger.debug(f"[ARQ] Frame seq={frame.seq_num} dropped after "
                         f"{attempt} attempts")

        self.total_retransmissions += stats["retransmissions"]
        self.transmission_history.append(stats)
        return success, stats

    def receive_frame(self, serialized_frame: str) -> Tuple[Optional[Frame], Frame]:
        """
        Receive and validate a frame, returning the data frame and response (ACK/NACK).

        Args:
            serialized_frame: Serialized frame string received from channel.

        Returns:
            Tuple of (data_frame or None, response_frame).
            data_frame is None if frame was corrupted.
        """
        self.total_frames_received += 1

        frame = Frame.deserialize(serialized_frame)

        if frame is None:
            # Frame parsing failed - create NACK
            logger.debug("[ARQ] Received corrupted frame (parse failed)")
            self.frame_errors_detected += 1
            nack = Frame(FrameType.NACK, 0, "UNKNOWN", "UNKNOWN", "PARSE_ERROR")
            self.total_nacks_sent += 1
            return None, nack

        # Verify CRC
        if not frame.verify_crc():
            logger.debug(f"[ARQ] CRC error detected in frame seq={frame.seq_num}")
            self.frame_errors_detected += 1
            nack = frame.create_nack()
            self.total_nacks_sent += 1
            return None, nack

        # Frame is valid - send ACK
        ack = frame.create_ack()
        self.total_acks_sent += 1
        logger.debug(f"[ARQ] Frame seq={frame.seq_num} received OK, sending ACK")
        return frame, ack

    def get_frame_error_rate(self) -> float:
        """Calculate Frame Error Rate."""
        if self.total_frames_received == 0:
            return 0.0
        return self.frame_errors_detected / self.total_frames_received

    def get_throughput(self, total_time: float) -> float:
        """
        Calculate throughput in frames per second.

        Args:
            total_time: Total simulation time in seconds.

        Returns:
            Throughput in frames/second.
        """
        if total_time <= 0:
            return 0.0
        return self.successful_deliveries / total_time

    def get_metrics(self) -> dict:
        """Get comprehensive ARQ metrics."""
        return {
            "total_frames_sent": self.total_frames_sent,
            "total_frames_received": self.total_frames_received,
            "successful_deliveries": self.successful_deliveries,
            "total_retransmissions": self.total_retransmissions,
            "total_frames_dropped": self.total_frames_dropped,
            "frame_errors_detected": self.frame_errors_detected,
            "frame_error_rate": self.get_frame_error_rate(),
            "total_acks": self.total_acks_sent,
            "total_nacks": self.total_nacks_sent,
            "delivery_rate": (
                self.successful_deliveries / self.total_frames_sent
                if self.total_frames_sent > 0 else 0.0
            ),
        }

    def reset_metrics(self):
        """Reset all ARQ metrics."""
        self.total_frames_sent = 0
        self.total_frames_received = 0
        self.total_retransmissions = 0
        self.total_acks_sent = 0
        self.total_nacks_sent = 0
        self.total_frames_dropped = 0
        self.successful_deliveries = 0
        self.frame_errors_detected = 0
        self.transmission_history.clear()
