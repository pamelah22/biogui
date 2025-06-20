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
import struct
import numpy as np
import time
from ..utils import WANDminiComm

packetSize: int = 200  # buffer size in cp2130_libusb_read

sigInfo: dict = {"emg": {"fs": 1000, "nCh": 67}}

def decodeFn(data: bytes, cp2130Handle) -> dict[str, np.ndarray]:
    nCh = sigInfo["emg"]["nCh"]

    if data[1] == 198:  # valid CRC byte
        raw_bytes = data[2:]
        values = [raw_bytes[2*i + 1] << 8 | raw_bytes[2*i] for i in range(nCh)]
        emg = np.asarray(values, dtype=np.float32).reshape(1, nCh)
    else:
        emg = np.zeros((1, nCh), dtype=np.float32)

    return {"emg": emg}

def _flush_fifo(handle):
    WANDminiComm.cp2130_libusb_flush_radio_fifo(handle)

def _start_stream(handle):
    WANDminiComm.startStream(handle)

def _stop_stream(handle):
    WANDminiComm.stopStream(handle)

startSeq: list[callable | float] = [
    _flush_fifo,
    0.1,
    _start_stream,
]

stopSeq: list[callable | float] = [
    _stop_stream,
    0.1,
]

def configureDevice(handle) -> bool:
    return (
        WANDminiComm.cp2130_libusb_set_usb_config(handle)
        and WANDminiComm.cp2130_libusb_set_spi_word(handle)
        and WANDminiComm.writeReg(handle, 0, 0x0C, 1)
    )

def exitDevice(handle, kernelAttached, deviceList, context):
    WANDminiComm.exit_cp2130(handle, kernelAttached, deviceList, context)
