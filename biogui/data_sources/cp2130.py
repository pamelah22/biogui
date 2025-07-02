from __future__ import annotations

import logging
from ctypes import POINTER, byref, c_int, c_ubyte, sizeof

import libusb1
import usb1  # For device enumeration only
from PySide6.QtCore import QByteArray
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QIcon
import time
from PySide6.QtCore import QTimer
from PySide6.QtCore import QObject, Signal

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
        self.deviceList = libusb1.libusb_device_p_p()
        self.device = libusb1.libusb_device_p()
        self.cp2130Handle = libusb1.libusb_device_handle_p()

        # init libusb
        self.context = libusb1.libusb_context_p()
        if libusb1.libusb_init(byref(self.context)) != 0:
            print('Could not initialize libusb!')

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

        device = self._deviceList[index]
        self.cp2130Handle = libusb1.libusb_device_handle_p()
        kernelAttached = 0

        if libusb1.libusb_open(device, byref(self.cp2130Handle)) != 0:
            return DataSourceConfigResult(
                dataSourceType=DataSourceType.CP2130,
                dataSourceConfig={},
                isValid=False,
                errMessage="Could not open device",
            )

        if libusb1.libusb_kernel_driver_active(self.cp2130Handle, 0) != 0:
            libusb1.libusb_detach_kernel_driver(self.cp2130Handle, 0)
            kernelAttached = 1

        if libusb1.libusb_claim_interface(self.cp2130Handle, 0) != 0:
            return DataSourceConfigResult(
                dataSourceType=DataSourceType.CP2130,
                dataSourceConfig={},
                isValid=False,
                errMessage="Could not claim interface",
            )

        return DataSourceConfigResult(
            dataSourceType=DataSourceType.CP2130,
            dataSourceConfig={
                "device": device,
                "context": self.context,
                "cp2130Handle": self.cp2130Handle,
                "kernelAttached": kernelAttached,
                "deviceList": self.deviceList,
            },
            isValid=True,
            errMessage="",
        )

    def getFieldsInTabOrder(self) -> list[QWidget]:
        return [self.cp2130ComboBox, self.rescancp2130Button]

    def _rescanDevices(self) -> None:
        self.cp2130ComboBox.clear()
        self._deviceList = []

        self.context = libusb1.libusb_context_p()
        if libusb1.libusb_init(byref(self.context)) != 0:
            logging.error("Could not initialize libusb context")
            self.cp2130ComboBox.addItem("LibUSB init failed")
            return

        device_list = libusb1.libusb_device_p_p()
        device_count = libusb1.libusb_get_device_list(self.context, byref(device_list))

        if device_count <= 0:
            self.cp2130ComboBox.addItem("No CP2130 devices found")
            return

        for i in range(device_count):
            device = device_list[i]
            desc = libusb1.libusb_device_descriptor()
            if libusb1.libusb_get_device_descriptor(device, byref(desc)) == 0:
                if desc.idVendor == 0x10C4 and desc.idProduct == 0x87A0:
                    self._deviceList.append(device)
                    self.cp2130ComboBox.addItem(f"CP2130 - Device {i}")

        if not self._deviceList:
            self.cp2130ComboBox.addItem("No CP2130 devices found")

        self.deviceList = device_list  # Needed for cleanup later



class Cp2130DataSourceWorker(DataSourceWorker):
    plotDataReady = Signal(list)
    updateTime = Signal()
    errorOccurred = Signal(str)
    def __init__(
        self,
        packetSize: int,
        startSeq: list,
        stopSeq: list,
        device: usb1.USBDevice,
        cp2130Handle: POINTER(libusb1.libusb_device_handle),
        context: libusb1.libusb_context_p,
        kernelAttached: int,
        deviceList: libusb1.libusb_device_p,
    ) -> None:
        super().__init__()

        self._packetSize = packetSize
        self._startSeq = startSeq
        self._stopSeq = stopSeq

        self._device = device
        self._cp2130Handle = cp2130Handle
        self._context = context
        self._kernelAttached = kernelAttached
        self.deviceList = deviceList

        self._buffer = QByteArray()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._collectData)
        self._timer.setInterval(10)

        self.destroyed.connect(self.deleteLater)

        self.samples = 0  # optional, useful for logging
        self.numMins = 0  # optional
        self.start_time = time.time()  # optiona


    def __str__(self) -> str:
        return "CP2130 USB Device"

    @staticmethod
    def exit_cp2130(cp2130Handle, kernelAttached, context, deviceList):
        if cp2130Handle:
            libusb1.libusb_release_interface(cp2130Handle, 0)
        if kernelAttached:
            libusb1.libusb_attach_kernel_driver(cp2130Handle, 0)
        if cp2130Handle:
            libusb1.libusb_close(cp2130Handle)
        if deviceList:
            libusb1.libusb_free_device_list(deviceList, 1)
        if context:
            libusb1.libusb_exit(context)

    def startCollecting(self) -> None:
        try:
            for command in self._startSeq:
                if isinstance(command, float):
                    time.sleep(command)
                elif callable(command):
                    command(self._cp2130Handle)
            logging.info("CP2130 communication started.")

            # Start QTimer loop
            self._timer.start()


        except Exception as e:
            self.errorOccurred.emit(f"Start error: {str(e)}")
            logging.error(f"Start error: {str(e)}")

    def stopCollecting(self) -> None:
        try:
            # Stop QTimer loop
            self._timer.stop()

            for command in self._stopSeq:
                if isinstance(command, float):
                    time.sleep(command)
                elif callable(command):
                    command(self._cp2130Handle)

            self._buffer.clear()
            logging.info("CP2130 communication stopped.")
            #self.exit_cp2130(self._cp2130Handle, self._kernelAttached, self._context, self.deviceList)
        except Exception as e:
            logging.error(f"Stop error: {str(e)}")
            self.errorOccurred.emit(f"Stop error: {str(e)}")
    def _collectData(self):
        """Read data from the CP2130 via USB and emit when enough is available."""
        # Attempt USB read
        byte_data = self._cp2130_libusb_read(self._cp2130Handle)
        if byte_data is None:
            logging.warning("USB read failed.")
            return

        # Append to QByteArray buffer
        self._buffer.append(byte_data)

        # Emit full packets
        while self._buffer.size() >= self._packetSize:
            packet = self._buffer.mid(0, self._packetSize).data()
            self.dataPacketReady.emit(packet)
            self._buffer.remove(0, self._packetSize)


    def _cp2130_libusb_read(self, handle):
        """Perform a bulk read from CP2130 and return as bytes, or None on failure."""
        # Prepare read command
        read_cmd_buf = (c_ubyte * 8)(0x00, 0x00, 0x00, 0x00, 200, 0x00, 0x00, 0x00)
        bytes_written = c_int()
        usb_timeout = 500

        # Send OUT transfer (command)
        err = libusb1.libusb_bulk_transfer(
            handle, 0x02, read_cmd_buf, sizeof(read_cmd_buf), byref(bytes_written), usb_timeout
        )
        if err or bytes_written.value != sizeof(read_cmd_buf):
            print(f"Write error {err} or incorrect size {bytes_written.value}")
            return None

        # Prepare buffer for IN transfer
        buf = (c_ubyte * 200)()
        bytes_read = c_int()
        err = libusb1.libusb_bulk_transfer(
            handle, 0x81, buf, sizeof(buf), byref(bytes_read), usb_timeout
        )
        if err:
            print(f"Read error {err}")
            return None

        return bytes(buf[:bytes_read.value])
