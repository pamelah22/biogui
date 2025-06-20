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
from ctypes import byref

import pandas as pd
from PyQt5.QtCore import QByteArray
from PyQt5.QtWidgets import QWidget, QCheckBox, QComboBox, QPushButton
from PyQt5.QtGui import QIcon
import libusb1

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

        self._deviceList = []
        self._context = None
        self._cp2130Handle = None
        self._kernelAttached = 0

        self.rescancp2130Button.clicked.connect(self._rescanDevices)
        self._rescanDevices()

    def validateConfig(self) -> DataSourceConfigResult:
        if self.cp2130ComboBox.currentIndex() < 0 or not self._deviceList:
            return DataSourceConfigResult(
                dataSourceType=DataSourceType.CP2130,
                dataSourceConfig={},
                isValid=False,
                errMessage="No CP2130 device selected.",
            )

        return DataSourceConfigResult(
            dataSourceType=DataSourceType.CP2130,
            dataSourceConfig={
                "device": self._deviceList[self.cp2130ComboBox.currentIndex()],
                "context": self._context,
                "kernelAttached": self._kernelAttached,
            },
            isValid=True,
            errMessage="",
        )

    def getFieldsInTabOrder(self) -> list[QWidget]:
        return [self.cp2130ComboBox, self.rescancp2130Button]

    def _rescanDevices(self) -> None:
        self.cp2130ComboBox.clear()
        self._deviceList = []

        context = libusb1.libusb_context_p()
        if libusb1.libusb_init(byref(context)) != 0:
            logging.error("Could not initialize libusb.")
            return

        device_list = libusb1.libusb_device_p_p()
        count = libusb1.libusb_get_device_list(context, byref(device_list))
        if count < 0:
            logging.error("Error getting USB device list.")
            libusb1.libusb_exit(context)
            return

        VID, PID = 0x10C4, 0x87A0

        for i in range(count):
            device = device_list[i]
            descriptor = libusb1.libusb_device_descriptor()
            if libusb1.libusb_get_device_descriptor(device, byref(descriptor)) == 0:
                if descriptor.idVendor == VID and descriptor.idProduct == PID:
                    self._deviceList.append(device)
                    self.cp2130ComboBox.addItem(f"CP2130 #{len(self._deviceList)}")

        if not self._deviceList:
            self.cp2130ComboBox.addItem("No CP2130 devices found")
            libusb1.libusb_free_device_list(device_list, 1)
            libusb1.libusb_exit(context)
        else:
            self._context = context


class Cp2130DataSourceWorker(DataSourceWorker):
    def __init__(self, interface, cp2130Handle) -> None:
        super().__init__()

        self._interface = interface
        self._packetSize = interface.packetSize
        self._startSeq = interface.startSeq
        self._stopSeq = interface.stopSeq
        self._decodeFn = interface.decodeFn
        self._sigInfo = interface.sigInfo
        self._cp2130Handle = cp2130Handle

        self._buffer = QByteArray()
        self._collected_data = []
        self._crc_flags = []
        self._sample_count = 0
        self._csv_file = f"data/{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"

        self.destroyed.connect(self.deleteLater)

    def __str__(self):
        return "CP2130 USB Device"

    def startCollecting(self) -> None:
        try:
            for command in self._startSeq:
                command(self._cp2130Handle)
            logging.info("DataWorker: CP2130 communication started.")
        except Exception as e:
            self.errorOccurred.emit(str(e))
            logging.error(f"DataWorker start error: {str(e)}")

    def stopCollecting(self) -> None:
        try:
            for command in self._stopSeq:
                command(self._cp2130Handle)

            if self._sample_count > 0:
                os.makedirs("data", exist_ok=True)
                channel_count = self._sigInfo["emg"]["nCh"]
                df = pd.DataFrame(self._collected_data, columns=[f"Ch{i}" for i in range(channel_count)])
                df["CRC"] = self._crc_flags
                df.to_csv(self._csv_file, index=False)
                logging.info(f"Data saved to {self._csv_file}")

            self._buffer = QByteArray()
            logging.info("DataWorker: CP2130 communication stopped.")
        except Exception as e:
            logging.error(f"DataWorker stop error: {str(e)}")

    def _collectData(self) -> None:
        try:
            data = self._interface.readData(self._cp2130Handle)
            if data:
                self._buffer.append(QByteArray(bytes(data)))
                while self._buffer.size() >= self._packetSize:
                    packet = self._buffer.mid(0, self._packetSize).data()
                    self._sample_count += 1
                    decoded = self._decodeFn(packet, self._cp2130Handle)
                    self._crc_flags.append(packet[1] != 198)
                    self._collected_data.append(decoded["emg"][0])
                    self.dataPacketReady.emit(packet)
                    self._buffer.remove(0, self._packetSize)
        except Exception as e:
            logging.error(f"Error reading from device: {str(e)}")
