# usb_spi_data_source.py

import logging
import time
from queue import Queue, Empty
from typing import Optional

import usb1
from PySide6.QtCore import QByteArray, QIODevice, QLocale, QObject, QTimer, QThread, Signal

from . import wandmini_interface as interface
from .base import DataSourceConfigWidget, DataSourceConfigResult, DataSourceWorker, DataSourceType
from ..ui.usb_spi_data_source_config_widget_ui import Ui_USBSpiDataSourceConfigWidget
from ..utils import detectTheme

sampleQueue = Queue()

def list_wandmini_devices() -> list[dict]:
    """List all WANDmini CP2130 devices via USB."""
    with usb1.USBContext() as ctx:
        devices = ctx.getDeviceList(skip_on_error=True)
        result = []
        for dev in devices:
            if dev.getVendorID() == 0x10C4 and dev.getProductID() == 0x87A0:
                try:
                    serial = dev.getSerialNumber()
                except Exception:
                    serial = "Unknown"
                result.append({
                    "bus": dev.getBusNumber(),
                    "address": dev.getDeviceAddress(),
                    "serial_number": serial,
                })
        return result

class USBSpiConfigWidget(DataSourceConfigWidget, Ui_USBSpiDataSourceConfigWidget):
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.setupUi(self)
        theme = detectTheme()
        self.rescanButton.setIcon(QIcon.fromTheme("view-refresh", QIcon(f":icons/{theme}/reload")))
        self._rescan()
        self.rescanButton.clicked.connect(self._rescan)

    def _rescan(self):
        self.deviceCombo.clear()
        for d in list_wandmini_devices():
            self.deviceCombo.addItem(f"Bus {d['bus']} Addr {d['address']} – SN {d['serial_number']}")

    def validateConfig(self):
        txt = self.deviceCombo.currentText()
        if not txt:
            return DataSourceConfigResult(DataSourceType.USB_SPI, {}, False, 'No USB device selected')
        parts = txt.split()
        return DataSourceConfigResult(
            DataSourceType.USB_SPI,
            {"bus": int(parts[1]), "address": int(parts[3])},
            True, "")

    def prefill(self, config):
        if "bus" in config:
            self.deviceCombo.setCurrentText(f"Bus {config['bus']} Addr {config['address']}")

    def getFieldsInTabOrder(self):
        return [self.deviceCombo, self.rescanButton]

class CP2130Reader(QThread):
    errorOccurred = Signal(str)

    def __init__(self, handle):
        super().__init__()
        self.handle = handle
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            try:
                data = self.handle.bulkWrite(0x02, bytes([0]*8))  # Placeholder for real read
                data = self.handle.bulkRead(0x81, interface.packetSize, 500)
                if data:
                    sampleQueue.put(bytes(data))
            except Exception as e:
                self.errorOccurred.emit(str(e))
                break

    def stop(self):
        self._running = False
        self.wait()

class USBSpiDataSourceWorker(DataSourceWorker):
    dataPacketReady = Signal(bytes)
    errorOccurred = Signal(str)

    def __init__(self, bus, address):
        super().__init__()
        self.handle = None
        self.thread = None
        self.buffer = QByteArray()
        self.bus = bus
        self.address = address
        self.pollTimer = QTimer()
        self.pollTimer.timeout.connect(self._collectData)

    def __str__(self):
        return f"WANDmini USB SPI (bus={self.bus}, addr={self.address})"

    def startCollecting(self):
        try:
            ctx = usb1.USBContext()
            dev = ctx.openByBusAndAddress(self.bus, self.address)
            dev.claimInterface(0)
            # Add CP2130 init writes here if needed
            self.handle = dev
            self.thread = CP2130Reader(dev)
            self.thread.errorOccurred.connect(self.errorOccurred)
            self.thread.start()
            self.pollTimer.start(1)
        except Exception as e:
            msg = f"Failed to open WANDmini USB SPI: {e}"
            self.errorOccurred.emit(msg)
            logging.error(msg)

    def stopCollecting(self):
        if self.thread:
            self.thread.stop()
        if self.handle:
            try:
                self.handle.releaseInterface(0)
            except Exception:
                pass
            self.handle = None
        self.pollTimer.stop()
        self.buffer.clear()

    def _collectData(self):
        try:
            while not sampleQueue.empty():
                data = sampleQueue.get_nowait()
                self.buffer.append(data)
            pkg_size = interface.packetSize
            while self.buffer.size() >= pkg_size:
                packet = self.buffer.mid(0, pkg_size).data()
                self.dataPacketReady.emit(packet)
                self.buffer.remove(0, pkg_size)
        except Empty:
            pass
