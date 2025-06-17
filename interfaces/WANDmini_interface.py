"""
This module contains the CP2130 interface for sEMG data acquisition.

Copyright 2025 Mattia Orlandi, Pierangelo Maria Rapa

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import numpy as np
from biogui.utils import WANDminiComm

packetSize: int = 200  # This is the size of the buffer in cp2130_libusb_read

#x00 is a placeholder for the cp2130_libusb_flush_radio_fifo, .1s is a delay, and \x01 is the startStream placeholder.
startSeq: list[bytes | float] = [b"\x00", 0.1, b"\x01"]
#\x00 is the stopstream placeholder, and .1s is a delay
stopSeq: list[bytes | float] = [b"\x00", 0.1]
#from run function in ProcessThread class
sigInfo: dict = {"emg": {"fs": 1000, "nCh": 67}}

def decodeFn(data: bytes, cp2130Handle) -> dict[str, np.ndarray]:
    nCh = sigInfo["emg"]["nCh"]

    if data[1] == 198: #checks status byte for valid data
        raw_bytes = data[2:]  # Skip first 2 bytes (status or header)
        values = [raw_bytes[2*i + 1] << 8 | raw_bytes[2*i] for i in range(nCh)] #extracts 67 16-bit values
        emg = np.asarray(values, dtype=np.float32).reshape(1, nCh)
    else: #return empty array 
        emg = np.zeros((1, nCh), dtype=np.float32)

    return {"emg": emg}

def configureDevice(handle) -> bool:
    if not WANDminiComm.cp2130_libusb_set_usb_config(handle):
        return False
    if not WANDminiComm.cp2130_libusb_set_spi_word(handle):
        return False
    return WANDminiComm.writeReg(handle, 0, 0x0C, 1)  # Wide input mode
