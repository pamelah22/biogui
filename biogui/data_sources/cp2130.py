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
import pandas as pd
import os
from PySide6.QtCore import QByteArray, QIODevice
from PySide6.QtWidgets import QWidget, QCheckBox
from biogui.utils import detectTheme

from ..ui.cp2130_data_source_config_widget_ui import Ui_Cp2130DataSourceConfigWidget
from .base import (
    DataSourceConfigResult,
    DataSourceConfigWidget,
    DataSourceType,
    DataSourceWorker,
)


class Cp2130ConfigWidget(DataSourceConfigWidget, Ui_Cp2130DataSourceConfigWidget):
    """
    Widget to configure the CP2130 USB source.

    Parameters
    ----------
    parent : QWidget or None, default=None
        Parent QWidget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Setup UI
        self.setupUi(self)
        theme = detectTheme()
        self.connectButton.setIcon(
            QIcon.fromTheme("network-connect", QIcon(f":icons/{theme}/connect"))
        )

        self.connectButton.clicked.connect(self._checkDevice)
        self._checkDevice()

        self.destroyed.connect(self.deleteLater)

    def validateConfig(self) -> DataSourceConfigResult:
        """
        Validate the configuration.

        Returns
        -------
        DataSourceConfigResult
            Configuration result.
        """
        if not hasattr(self, "_cp2130Handle") or not self._cp2130Handle:
            return DataSourceConfigResult(
                dataSourceType=DataSourceType.CP2130,
                dataSourceConfig={},
                isValid=False,
                errMessage="No CP2130 device connected.",
            )

        return DataSourceConfigResult(
            dataSourceType=DataSourceType.CP2130,
            dataSourceConfig={
                "cp2130Handle": self._cp2130Handle,
                "kernelAttached": self._kernelAttached,
                "deviceList": self._deviceList,
                "context": self._context,
                "wideInput": self.wideInputCheckBox.isChecked(),
            },
            isValid=True,
            errMessage="",
        )

    def prefill(self, config: dict) -> None:
        """
        Pre-fill the form with the provided configuration.

        Parameters
        ----------
        config : dict
            Dictionary with the configuration.
        """
        if "wideInput" in config:
            self.wideInputCheckBox.setChecked(config["wideInput"])

    def getFieldsInTabOrder(self) -> list[QWidget]:
        """
        Get the list of fields in tab order.

        Returns
        -------
        list of QWidgets
            List of the QWidgets in tab order.
        """
        return [self.connectButton, self.wideInputCheckBox]

    def _checkDevice(self) -> None:
        """
        Check for CP2130 device and attempt to connect.
        """
        try:
            self._cp2130Handle, self._kernelAttached, self._deviceList, self._context = WANDminiComm.open_cp2130()
            if not cp2130_interface.configureDevice(self._cp2130Handle):
                raise Exception("Failed to configure CP2130 device.")
            self.connectButton.setText("Connected")
            self.connectButton.setEnabled(False)
        except Exception as e:
            self._cp2130Handle = None
            self.connectButton.setText("Connect")
            self.connectButton.setEnabled(True)
            logging.error(f"Failed to connect to CP2130: {str(e)}")


class Cp2130DataSourceWorker(DataSourceWorker):
    """
    DataSourceWorker for CP2130 USB devices using a provided interface.

    Parameters
    ----------
    interface : object
        Interface module or object with attributes:
            - packetSize : int
            - startSeq : list[bytes | float]
            - stopSeq : list[bytes | float]
            - decodeFn(data: bytes, handle) -> dict[str, np.ndarray]
            - sigInfo : dict describing signal metadata
    cp2130Handle : libusb1.libusb_device_handle_p
        Handle to the CP2130 device.
    kernelAttached : bool
        Whether the kernel driver was attached.
    deviceList : libusb1.libusb_device_p_p
        List of USB devices.
    context : libusb1.libusb_context_p
        USB context.
    wideInput : bool
        Whether wide input mode is enabled.
    """

    def __init__(
        self,
        interface,
        cp2130Handle,
        kernelAttached: bool,
        deviceList,
        context,
        wideInput: bool,
    ) -> None:
        super().__init__()

        # Interface abstraction
        self._interface = interface
        self._packetSize = interface.packetSize
        self._startSeq = interface.startSeq
        self._stopSeq = interface.stopSeq
        self._decodeFn = interface.decodeFn
        self._sigInfo = interface.sigInfo

        # USB
        self._cp2130Handle = cp2130Handle
        self._kernelAttached = kernelAttached
        self._deviceList = deviceList
        self._context = context
        self._wideInput = wideInput

        # Data buffer and logging
        self._buffer = QByteArray()
        self._collected_data = []
        self._crc_flags = []
        self._sample_count = 0
        self._crc_count = 0
        self._csv_file = f"data/{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.csv"

        self.destroyed.connect(self.deleteLater)

    def __str__(self):
        return "CP2130 USB Device"

    def startCollecting(self) -> None:
        """Begin streaming data from the device."""

        if self._wideInput:
            if not WANDminiComm.writeReg(self._cp2130Handle, 0, 0x0C, 1):
                errMsg = "Failed to enable wide input mode."
                self.errorOccurred.emit(errMsg)
                logging.error(f"DataWorker: {errMsg}")
                return

        for command in self._startSeq:
            if isinstance(command, bytes):
                if command == b"\x00":
                    WANDminiComm.cp2130_libusb_flush_radio_fifo(self._cp2130Handle)
                elif command == b"\x01":
                    WANDminiComm.startStream(self._cp2130Handle)
            elif isinstance(command, float):
                time.sleep(command)

        self._sample_count = 0
        self._crc_count = 0
        logging.info("DataWorker: CP2130 communication started.")

    def stopCollecting(self) -> None:
        """Stop data streaming and clean up."""

        for command in self._stopSeq:
            if isinstance(command, bytes):
                if command == b"\x00":
                    WANDminiComm.stopStream(self._cp2130Handle)
            elif isinstance(command, float):
                time.sleep(command)

        if self._sample_count > 0:
            logging.info(f"DataWorker: Streamed {self._sample_count} samples, {self._crc_count} CRC errors.")
            os.makedirs("data", exist_ok=True)
            channel_count = self._sigInfo["emg"]["nCh"]
            df = pd.DataFrame(self._collected_data, columns=[f"Ch{i}" for i in range(channel_count)])
            df["CRC"] = self._crc_flags
            df.to_csv(self._csv_file, index=False)
            logging.info(f"Data saved to {self._csv_file}")

        WANDminiComm.exit_cp2130(self._cp2130Handle, self._kernelAttached, self._deviceList, self._context)
        self._buffer = QByteArray()
        logging.info("DataWorker: CP2130 communication stopped.")

    def _collectData(self) -> None:
        """Fill input buffer when data is ready."""
        data = WANDminiComm.cp2130_libusb_read(self._cp2130Handle)
        if data:
            self._buffer.append(QByteArray(bytes(data)))
            if self._buffer.size() >= self._packetSize:
                packet = self._buffer.mid(0, self._packetSize).data()
                self._sample_count += 1
                decoded = self._decodeFn(packet, self._cp2130Handle)
                if packet[1] != 198:  # CRC error
                    self._crc_count += 1
                if not hasattr(self, "_collected_data"):
                    self._collected_data = []
                    self._crc_flags = []
                self._collected_data.append(decoded["emg"][0])
                self._crc_flags.append(packet[1] != 198)
                self.dataPacketReady.emit(packet)
                self._buffer.remove(0, self._packetSize)
