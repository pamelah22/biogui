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
import time
from typing import Callable, Union
import libusb1
from ctypes import byref, create_string_buffer, c_int, sizeof, POINTER, \
    cast, c_uint8, c_uint16, c_ubyte, string_at, c_void_p, cdll, addressof, \
    c_char
import struct
from enum import Enum

# CP2130 Specific Stuff

def cp2130_libusb_write(handle, value):
    buf = c_ubyte * 13
    write_command_buf = buf(
        0x00, 0x00,
        0x01,
        0x00,
        0x01, 0x00, 0x00, 0x00)
    # populate command buffer with value to write
    write_command_buf[8:13] = value
    bytesWritten = c_int()
    usbTimeout = 500

    error_code = libusb1.libusb_bulk_transfer(handle, 0x02, write_command_buf, sizeof(write_command_buf), byref(bytesWritten), usbTimeout)
    if error_code:
        print('Error in bulk transfer (write command)! Error # {}'.format(error_code))
        return False
    return True

def cp2130_libusb_flush_radio_fifo(handle):
    buf = c_ubyte * 13
    write_command_buf = buf(
        0x00, 0x00,
        0x01,
        0x00,
        0x05, 0x00, 0x00, 0x00,
        0xAA, 0x00, 0x00, 0x00, 0x00)
    bytesWritten = c_int()
    usbTimeout = 500

    if libusb1.libusb_bulk_transfer(handle, 0x02, write_command_buf, sizeof(write_command_buf), byref(bytesWritten), usbTimeout):
        print('Error in bulk transfer!')
        return False
    return True

def cp2130_libusb_read(handle):
    buf = c_ubyte * 8
    read_command_buf = buf(
        0x00, 0x00,
        0x00,
        0x00,
        200, 0x00, 0x00, 0x00)
    bytesWritten = c_int()
    buf = c_ubyte * 200
    read_input_buf = buf()
    bytesRead = c_int()
    usbTimeout = 500

    # print('Begin Read')
    error_code = libusb1.libusb_bulk_transfer(handle, 0x02, read_command_buf, sizeof(read_command_buf), byref(bytesWritten), usbTimeout)
    if error_code:
        print('Error in bulk transfer command= {}'.format(error_code))
        return False
    if bytesWritten.value != sizeof(read_command_buf):
        print('Error in bulk transfer write size')
        print(bytesWritten.value)
        return False
    error_code = libusb1.libusb_bulk_transfer(handle, 0x81, read_input_buf, sizeof(read_input_buf), byref(bytesRead), usbTimeout)
    if error_code:
        print(bytesRead.value)
        print('Error in bulk transfer read = {}'.format(error_code))
        return False
    return read_input_buf

def cp2130_libusb_set_spi_word(handle):
    buf = c_ubyte * 2
    control_buf_out = buf(0x00, 0x09)
    usbTimeout = 500

    error_code = libusb1.libusb_control_transfer(handle, 0x40, 0x31, 0x0000, 0x0000, control_buf_out, sizeof(control_buf_out), usbTimeout)
    if error_code != sizeof(control_buf_out):
        print('Error in bulk transfer')
        return False
    print('Successfully set value of spi_word on chip:')
    return True

def cp2130_libusb_set_usb_config(handle):
    buf = c_ubyte * 10
    control_buf_out = buf(0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80)
    usbTimeout = 500

    error_code = libusb1.libusb_control_transfer(handle, 0x40, 0x61, 0xA5F1, 0x000A, control_buf_out, sizeof(control_buf_out), usbTimeout)
    if error_code != sizeof(control_buf_out):
        print('Error in bulk transfer')
        return False
    print('Successfully set value of spi_word on chip:')
    return True


class Cmd(Enum):
    Reset = 0x01
    ClearErr = 0x02
    HvLoad = 0x03
    ImpStart = 0x04
    StimReset = 0x08
    StimStart = 0x09
    StimXfer = 0x0a

# CM register addresses
class Reg(Enum):
    ctrl = 0x00
    rst = 0x04
    n0d1 = 0x10
    n0d2 = 0x14
    n1d1 = 0x20
    n1d2 = 0x24
    req = 0xff
    stimExp = 0xAF

def regWr(handle, reg, value):
    cp2130_libusb_write(handle, [reg.value, *struct.pack('>I', value)])

def startStream(handle):
    regWr(handle, Reg.req, 0x0020)

def stopStream(handle):
    regWr(handle, Reg.req, 0x0010)

def writeOp(handle, nm, addr, data):
    if nm == 0:
        regWr(handle, Reg.n0d1, 1)
        regWr(handle, Reg.n0d2, addr << 16 | data)
        regWr(handle, Reg.ctrl, 0x1000)
                
    if nm == 1:
        regWr(handle, Reg.n1d1, 1)
        regWr(handle, Reg.n1d2, addr << 16 | data)
        regWr(handle, Reg.ctrl, 0x2000)

def sendCmd(handle, nm, cmd):
        # print('Send Command')
        if nm==0:
            regWr(handle, Reg.n0d2, 1<<10 | (cmd & 0x3FF))
            regWr(handle, Reg.ctrl, 0x1010)
        if nm==1:
            regWr(handle, Reg.n1d2, 1<<10 | (cmd & 0x3FF))
            regWr(handle, Reg.ctrl, 0x2020)

def readReg(handle, nm, addr):
    buf = c_ubyte*200
    d = buf()
    count = 0

    if nm == 0:
        regWr(handle, Reg.n0d1, 0)
        regWr(handle, Reg.n0d2, addr << 16 | 0)
        regWr(handle, Reg.ctrl, 0x1000)
        cp2130_libusb_flush_radio_fifo(handle)
        regWr(handle, Reg.req, 0x0100)
    else:
        regWr(handle, Reg.n1d1, 0)
        regWr(handle, Reg.n1d2, addr << 16 | 0)
        regWr(handle, Reg.ctrl, 0x2000)
        cp2130_libusb_flush_radio_fifo(handle)
        regWr(handle, Reg.req, 0x0200)

    while d[1] != 4 and count < 150:
        d = cp2130_libusb_read(handle)
        count = count + 1
    if d[1] == 4:
        add = d[2] + 256*d[3]
        val = d[4] + 256*d[5]
        if add == addr:
            # print('Register {}: {}'.format(hex(add), hex(val)))
            return val, True
        else:
            return val, False
    else:
        return 0, False

def writeReg(cp2130Handle, nm, addr, data):
    timeout = 10
    success = False
    while not success:
        timeout = timeout - 1
        if timeout == 0:
            break
        writeOp(cp2130Handle, nm, addr, data)
        readSuccess = False
        readTimeout = 10
        while not readSuccess:
            readTimeout = readTimeout - 1
            if readTimeout == 0:
                break
            val, readSuccess = readReg(cp2130Handle,0,addr)
        if readSuccess:
            success = val == data
    return success

def clearErr(cp2130Handle,nm):
    sendCmd(cp2130Handle,nm,Cmd.ClearErr.value)
    
def configureDevice(handle) -> bool:
    return (
        cp2130_libusb_set_usb_config(handle)
        and cp2130_libusb_set_spi_word(handle)
        and writeReg(handle, 0, 0x0C, 1)
    )

def _configure(handle):
    if not configureDevice(handle):
        raise RuntimeError("Device configuration failed.")


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
    cp2130_libusb_flush_radio_fifo(handle)

def _start_stream(handle):
    startStream(handle)

def _stop_stream(handle):
    stopStream(handle)

startSeq: list[Union[Callable, float]] = [
    _configure,
    _flush_fifo,
    0.1,
    _start_stream,
]

stopSeq: list[Union[Callable, float]] = [
    _stop_stream,
    0.1,
]


