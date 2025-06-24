"""
Classes for the CP2130 USB data source.

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

from __future__ import annotations

import logging
import time
import os
import datetime

import pandas as pd

from PySide6.QtCore import QByteArray
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QIcon

import usb1  # Python libusb wrapper

from biogui.utils import detectTheme
from ..ui.cp2130_data_source_config_widget_ui import Ui_Cp2130ConfigWidget
from .base import (
    DataSourceConfigResult,
    DataSourceConfigWidget,
    DataSourceType,
    DataSourceWorker,
)


class Cp2130ConfigWidget(DataSourceConfigWidget, Ui_Cp2130ConfigWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setupUi(self)
        theme = detectTheme()
        self.rescancp2130Button.setIcon(QIcon.fromTheme("view-refresh", QIcon(f":icons/{theme}/reload")))

        self._context: usb1.USBContext | None = None
        self._deviceList: list[usb1.USBDevice] = []
        self._cp2130Handle: usb1.USBDeviceHandle | None = None
        self._kernelAttached = 0

        self.rescancp2130Button.clicked.connect(self._rescanDevices)
        self._rescanDevices()

    def validateConfig(self) -> DataSourceConfigResult:
        index = self.cp2130ComboBox.currentIndex()
        if index < 0 or index >= len(self._deviceList):
            return DataSourceConfigResult(
                dataSourceType=DataSourceType.CP2130,
                dataSourceConfig={},
                isValid=False,
                errMessage="No CP2130 device selected.",
            )


        return DataSourceConfigResult(
            dataSourceType=DataSourceType.CP2130,
            dataSourceConfig={
                "device": self._deviceList[index],
                "context": self._context,
                "cp2130Handle": self._deviceList[index].open(),
                "kernelAttached": self._kernelAttached,
            },
            isValid=True,
            errMessage="",
        )`

    def getFieldsInTabOrder(self) -> list[QWidget]:
        return [self.cp2130ComboBox, self.rescancp2130Button]

    def _rescanDevices(self) -> None:
        self.cp2130ComboBox.clear()
        self._deviceList.clear()

        try:
            self._context = usb1.USBContext()
            VID, PID = 0x10C4, 0x87A0

            for device in self._context.getDeviceList(skip_on_error=True):
                if device.getVendorID() == VID and device.getProductID() == PID:
                    self._deviceList.append(device)
                    self.cp2130ComboBox.addItem(
                        f"CP2130 - Bus {device.getBusNumber()} Addr {device.getDeviceAddress()}"
                    )

            if not self._deviceList:
                self.cp2130ComboBox.addItem("No CP2130 devices found")
        except usb1.USBError as e:
            logging.error(f"USB error during device scan: {e}")
            self.cp2130ComboBox.addItem("USB scan error")



class Cp2130DataSourceWorker(DataSourceWorker):
    def __init__(
        self,
        packetSize: int,
        startSeq: list[Callable],
        stopSeq: list[Callable],
        device: usb1.USBDevice,
        cp2130Handle: usb1.USBDeviceHandle,
        context: usb1.USBContext | None = None,
        kernelAttached: int | None = None,
    ) -> None:
        super().__init__()

        self._packetSize = packetSize
        self._startSeq = startSeq
        self._stopSeq = stopSeq
        
        self._device = device
        self._cp2130Handle = cp2130Handle
        self._context = context
        self._kernelAttached = kernelAttached

        self._buffer = QByteArray()

        self.destroyed.connect(self.deleteLater)

    def __str__(self) -> str:
        return "CP2130 USB Device"
   
    @staticmethod   
    def exit_cp2130(cp2130Handle, kernelAttached, context):
        if cp2130Handle:
            libusb1.libusb_release_interface(cp2130Handle, 0)
        if kernelAttached:
            libusb1.libusb_attach_kernel_driver(cp2130Handle,0)
        if cp2130Handle:
            libusb1.libusb_close(cp2130Handle)
        if context:
            libusb1.libusb_exit(context)
        exit()

    def startCollecting(self) -> None:
        try:
            for command in self._startSeq:
                command(self._cp2130Handle)
            logging.info("CP2130 communication started.")
        except Exception as e:
            self.errorOccurred.emit(f"Start error: {str(e)}")
            logging.error(f"Start error: {str(e)}")

    def stopCollecting(self) -> None:
        try:
            for command in self._stopSeq:
                command(self._cp2130Handle)

            self._buffer.clear()
            logging.info("CP2130 communication stopped.")
            exit_cp2130(self._cp2130Handle, self._kernelAttached, self._context)
        except Exception as e:
            logging.error(f"Stop error: {str(e)}")

def _collectData(self) -> None:
    try:
        # Prepare read command buffer (only if your device requires it)
        read_command_buf = (c_ubyte * 8)(
            0x00, 0x00,
            0x00,
            0x00,
            self._packetSize, 0x00, 0x00, 0x00
        )
        bytesWritten = c_int()
        usbTimeout = 500

        # Send read command
        err = libusb1.libusb_bulk_transfer(
            self._cp2130Handle.handle,
            0x02,
            read_command_buf,
            sizeof(read_command_buf),
            byref(bytesWritten),
            usbTimeout,
        )
        if err or bytesWritten.value != sizeof(read_command_buf):
            raise RuntimeError(f"Failed to send read command. Code: {err}")

        # Read data from device
        read_input_buf = (c_ubyte * self._packetSize)()
        bytesRead = c_int()
        err = libusb1.libusb_bulk_transfer(
            self._cp2130Handle.handle,
            0x81,
            read_input_buf,
            sizeof(read_input_buf),
            byref(bytesRead),
            usbTimeout,
        )
        if err:
            raise RuntimeError(f"Failed to read input buffer. Code: {err}")

        # Append incoming data to buffer
        data_bytes = bytes(read_input_buf[:bytesRead.value])
        self._buffer.append(data_bytes)

        # While buffer has full packets, emit them
        while self._buffer.size() >= self._packetSize:
            packet = self._buffer.mid(0, self._packetSize).data()
            self.dataPacketReady.emit(packet)
            self._buffer.remove(0, self._packetSize)

    except Exception as e:
        msg = f"Error reading from device: {str(e)}"
        logging.error(msg)
        self.errorOccurred.emit(msg)
