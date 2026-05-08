"""
CRC-16 Error Detection
======================
Implements CRC-16 (CCITT) for frame error detection
in the Data Link Layer of the VANET communication system.
"""


class CRC16:
    """
    CRC-16-CCITT implementation for error detection.
    
    Uses polynomial: x^16 + x^12 + x^5 + 1 (0x1021)
    This is commonly used in communication protocols.
    """

    POLYNOMIAL = 0x1021
    INITIAL_VALUE = 0xFFFF

    @classmethod
    def compute(cls, data: str) -> str:
        """
        Compute CRC-16 checksum for given data.

        Args:
            data: Input string data.

        Returns:
            16-bit CRC as hexadecimal string (4 characters).
        """
        crc = cls.INITIAL_VALUE
        data_bytes = data.encode('utf-8', errors='replace')

        for byte in data_bytes:
            crc ^= (byte << 8)
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ cls.POLYNOMIAL) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF

        return format(crc, '04X')

    @classmethod
    def verify(cls, data: str, received_crc: str) -> bool:
        """
        Verify data integrity using CRC checksum.

        Args:
            data: Received data string.
            received_crc: CRC checksum received with the data.

        Returns:
            True if CRC matches (data is intact), False otherwise.
        """
        computed_crc = cls.compute(data)
        return computed_crc == received_crc.upper()
