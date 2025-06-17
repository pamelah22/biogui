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
            - startSeq : list[Callable[[], None] or Callable[[Any], None]]
            - stopSeq : list[Callable[[], None] or Callable[[Any], None]]
            - decodeFn(data: bytes, handle) -> dict[str, np.ndarray]
            - sigInfo : dict describing signal metadata
    cp2130Handle : libusb1.libusb_device_handle_p
        Handle to the CP2130 device.
    """

    def __init__(
        self,
        interface,
        cp2130Handle,
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

        # Buffer and log
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
        try:
            for command in self._startSeq:
                command(self._cp2130Handle)
            logging.info("DataWorker: CP2130 communication started.")
        except Exception as e:
            self.errorOccurred.emit(str(e))
            logging.error(f"DataWorker start error: {str(e)}")

    def stopCollecting(self) -> None:
        """Stop data streaming and clean up."""
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

            # Also optional: self._interface.cleanup(self._cp2130Handle) if included
            self._buffer = QByteArray()
            logging.info("DataWorker: CP2130 communication stopped.")
        except Exception as e:
            logging.error(f"DataWorker stop error: {str(e)}")

    def _collectData(self) -> None:
        """Fill input buffer when data is ready."""
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

