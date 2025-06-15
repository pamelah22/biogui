# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'serial_data_source_config_widget.ui'
##
## Created by: Qt User Interface Compiler version 6.8.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSizePolicy,
    QWidget)
from . import biogui_rc

class Ui_USBDataSourceConfigWidget(object):
    def setupUi(self, USBDataSourceConfigWidget: QWidget):
        USBDataSourceConfigWidget.setObjectName("USBDataSourceConfigWidget")
        USBDataSourceConfigWidget.resize(400, 100)

        self.verticalLayout = QVBoxLayout(USBDataSourceConfigWidget)
        self.verticalLayout.setObjectName("verticalLayout")

        self.connectButton = QPushButton(USBDataSourceConfigWidget)
        self.connectButton.setObjectName("connectButton")
        self.verticalLayout.addWidget(self.connectButton)

        self.disconnectButton = QPushButton(USBDataSourceConfigWidget)
        self.disconnectButton.setObjectName("disconnectButton")
        self.verticalLayout.addWidget(self.disconnectButton)

        self.retranslateUi(USBDataSourceConfigWidget)

    def retranslateUi(self, USBDataSourceConfigWidget: QWidget):
        _translate = USBDataSourceConfigWidget.tr
        self.connectButton.setText(_translate("USBDataSourceConfigWidget", "Connect to USB"))
        self.disconnectButton.setText(_translate("USBDataSourceConfigWidget", "Disconnect"))
