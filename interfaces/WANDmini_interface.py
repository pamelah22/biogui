# wandmini_interface.py

import struct
import numpy as np

packetSize: int = 67 * 2  # 67 channels × 2 bytes (uint16) = 134 bytes
"""Number of bytes in each packet."""

startSeq: list[bytes | float] = []  # No explicit start command; streaming begins on USB start
stopSeq: list[bytes | float] = []

sigInfo: dict = {"wand": {"fs": 1000, "nCh": 67}}
"""Signal metadata: 67 channels at 1000 Hz."""

def decodeFn(data: bytes) -> dict[str, np.ndarray]:
    """
    Decode a single packet from WANDmini: 67 uint16 samples.
    """
    nCh = sigInfo["wand"]["nCh"]
    nSamp = len(data) // (2 * nCh)
    arr = np.frombuffer(data, dtype=np.uint16).reshape((nSamp, nCh))
    return {"wand": arr}
