from __future__ import annotations

import logging
import time

from PySide6.QtWidgets import QComboBox, QLineEdit
from PySide6.QtGui import QIntValidator
from PySide6.QtCore import QLocale
from PySide6.QtCore import QByteArray, QObject, QTimer

from .base import (
    DataSourceConfigResult,
    DataSourceConfigWidget,
    DataSourceType,
    DataSourceWorker,
)

from ..utils import detectTheme
from ..ui.usb_data_source_config_widget_ui import Ui_USBDataSourceConfigWidget

import usb.core
import usb.util


def list_cp2130_devices() -> list[dict]:
    """
    Lists all connected CP2130 USB-to-SPI bridge devices.

    Returns
    -------
    List[dict]
        List of dictionaries with 'bus', 'address', and 'serial_number' keys.
    """
    CP2130_VID = 0x10C4
    CP2130_PID = 0x87A0

    devices = usb.core.find(find_all=True, idVendor=CP2130_VID, idProduct=CP2130_PID)
    result = []

    for dev in devices:
        try:
            serial = usb.util.get_string(dev, dev.iSerialNumber) or "Unknown"
        except usb.core.USBError:
            serial = "Unavailable"

        result.append({
            "bus": dev.bus,
            "address": dev.address,
            "serial_number": serial,
        })

    return result


class USBConfigWidget(DataSourceConfigWidget, Ui_USBDataSourceConfigWidget):
    """
    Widget to configure the USB (CP2130) data source.

    Parameters
    ----------
    parent : QWidget or None
        Parent QWidget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setupUi(self)
        theme = detectTheme()
        self.rescanUsbButton.setIcon(
            QIcon.fromTheme("view-refresh", QIcon(f":icons/{theme}/reload"))
        )

        self._rescanUsbDevices()
        self.rescanUsbButton.clicked.connect(self._rescanUsbDevices)

        # Setup validators
        self.packetSizeTextField.setValidator(QIntValidator(1, 10_000))
        self.spiFreqTextField.setValidator(QIntValidator(1000, 12_000_000))  # Hz

        self.destroyed.connect(self.deleteLater)

    def validateConfig(self) -> DataSourceConfigResult:
        """
        Validate the configuration.

        Returns
        -------
        DataSourceConfigResult
        """
        if self.usbDevicesComboBox.currentText() == "":
            return DataSourceConfigResult(
                dataSourceType=DataSourceType.USB,
                dataSourceConfig={},
                isValid=False,
                errMessage='The "USB device" field is empty.',
            )

        if not self.packetSizeTextField.hasAcceptableInput():
            return DataSourceConfigResult(
                dataSourceType=DataSourceType.USB,
                dataSourceConfig={},
                isValid=False,
                errMessage='The "packet size" field is invalid.',
            )

        if not self.spiFreqTextField.hasAcceptableInput():
            return DataSourceConfigResult(
                dataSourceType=DataSourceType.USB,
                dataSourceConfig={},
                isValid=False,
                errMessage='The "SPI frequency" field is invalid.',
            )

        # Parse device ID (e.g., "Bus 1 Address 4")
        try:
            selected = self.usbDevicesComboBox.currentText()
            parts = selected.split(" ")
            bus = int(parts[1])
            addr = int(parts[3])
        except Exception:
            return DataSourceConfigResult(
                dataSourceType=DataSourceType.USB,
                dataSourceConfig={},
                isValid=False,
                errMessage="Invalid device selection format.",
            )

        return DataSourceConfigResult(
            dataSourceType=DataSourceType.USB,
            dataSourceConfig={
                "bus": bus,
                "address": addr,
                "packetSize": QLocale().toInt(self.packetSizeTextField.text())[0],
                "spiFreq": QLocale().toInt(self.spiFreqTextField.text())[0],
            },
            isValid=True,
            errMessage="",
        )

    def prefill(self, config: dict) -> None:
        """Pre-fill the form with the provided configuration."""
        if "bus" in config and "address" in config:
            deviceStr = f"Bus {config['bus']} Address {config['address']}"
            self.usbDevicesComboBox.setCurrentText(deviceStr)
        if "packetSize" in config:
            self.packetSizeTextField.setText(QLocale().toString(config["packetSize"]))
        if "spiFreq" in config:
            self.spiFreqTextField.setText(QLocale().toString(config["spiFreq"]))

    def getFieldsInTabOrder(self) -> list[QWidget]:
        return [
            self.usbDevicesComboBox,
            self.rescanUsbButton,
            self.packetSizeTextField,
            self.spiFreqTextField,
        ]
    def _rescanUsbDevices(self) -> None:
        self.usbDevicesComboBox.clear()
        devices = list_cp2130_devices()
        entries = [f"Bus {d['bus']} Addr {d['address']} - SN {d['serial_number']}" for d in devices]
        self.usbDevicesComboBox.addItems(entries)
        
class USBDataSourceWorker(DataSourceWorker):
    """
    Concrete DataSourceWorker that collects data from a CP2130 USB device.

    Parameters
    ----------
    packetSize : int
        Size of each packet read from the USB.
    startSeq : list of bytes
        Sequence of commands to start the source.
    stopSeq : list of bytes
        Sequence of commands to stop the source.
    busNumber : int
        USB bus number.
    address : int
        USB device address.

    Attributes
    ----------
    _packetSize : int
        Size of each packet read from the device.
    _startSeq : list of bytes
        Start command sequence.
    _stopSeq : list of bytes
        Stop command sequence.
    _usbHandle : Any
        Handle to the CP2130 device.
    _buffer : QByteArray
        Input buffer.
    _pollTimer : QTimer
        Timer for polling new data.
    """

    def __init__(
        self,
        packetSize: int,
        startSeq: list[bytes],
        stopSeq: list[bytes],
        busNumber: int,
        address: int,
    ) -> None:
        super().__init__()

        self._packetSize = packetSize
        self._startSeq = startSeq
        self._stopSeq = stopSeq
        self._busNumber = busNumber
        self._address = address

        self._usbHandle = None
        self._buffer = QByteArray()
        self._pollTimer = QTimer()
        self._pollTimer.timeout.connect(self._collectData)

        self.destroyed.connect(self.deleteLater)

    def __str__(self):
        return f"USB device - Bus {self._busNumber}, Address {self._address}"

    def startCollecting(self) -> None:
        """Start USB communication and data collection."""
        try:
            from ..utils.cp2130 import open_cp2130, write_cp2130

            self._usbHandle = open_cp2130(self._busNumber, self._address)
        except Exception as e:
            errMsg = f"Could not open USB device: {e}"
            self.errorOccurred.emit(errMsg)
            logging.error(errMsg)
            return

        for c in self._startSeq:
            if isinstance(c, bytes):
                write_cp2130(self._usbHandle, c)
            elif isinstance(c, float):
                time.sleep(c)

        self._pollTimer.start(10)  # Poll every 10ms
        logging.info("DataWorker: USB communication started.")

    def stopCollecting(self) -> None:
        """Stop data collection and clean up the USB device."""
        self._pollTimer.stop()

        try:
            from ..utils.cp2130 import write_cp2130

            for c in self._stopSeq:
                if isinstance(c, bytes):
                    write_cp2130(self._usbHandle, c)
                elif isinstance(c, float):
                    time.sleep(c)
        except Exception as e:
            logging.warning(f"Error while sending stop sequence: {e}")

        self._buffer.clear()
        self._usbHandle = None
        logging.info("DataWorker: USB communication stopped.")

    def _collectData(self) -> None:
        """Read data from the USB device and emit packets."""
        try:
            from ..utils.cp2130 import read_cp2130

            chunk = read_cp2130(self._usbHandle, self._packetSize)
            self._buffer.append(chunk)

            while self._buffer.size() >= self._packetSize:
                data = self._buffer.mid(0, self._packetSize).data()
                self.dataPacketReady.emit(data)
                self._buffer.remove(0, self._packetSize)

        except Exception as e:
            errMsg = f"Error reading from USB device: {e}"
            self.errorOccurred.emit(errMsg)
            logging.error(errMsg)
