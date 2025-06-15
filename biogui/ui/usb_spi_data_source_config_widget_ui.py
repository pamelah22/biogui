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
    def setupUi(self, USBDataSourceConfigWidget):
        if not USBDataSourceConfigWidget.objectName():
            USBDataSourceConfigWidget.setObjectName("USBDataSourceConfigWidget")
        USBDataSourceConfigWidget.resize(400, 300)

        self.verticalLayout = QVBoxLayout(USBDataSourceConfigWidget)
        self.verticalLayout.setObjectName("verticalLayout")

        self.groupBox = QGroupBox(USBDataSourceConfigWidget)
        self.groupBox.setObjectName("groupBox")

        self.formLayout = QFormLayout(self.groupBox)
        self.formLayout.setObjectName("formLayout")

        self.deviceLabel = QLabel(self.groupBox)
        self.deviceLabel.setObjectName("deviceLabel")
        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.deviceLabel)

        self.deviceComboBox = QComboBox(self.groupBox)
        self.deviceComboBox.setObjectName("deviceComboBox")
        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.deviceComboBox)

        self.autoConnectCheckBox = QCheckBox(self.groupBox)
        self.autoConnectCheckBox.setObjectName("autoConnectCheckBox")
        self.formLayout.setWidget(1, QFormLayout.SpanningRole, self.autoConnectCheckBox)

        self.verticalLayout.addWidget(self.groupBox)

        self.retranslateUi(USBDataSourceConfigWidget)
        QMetaObject.connectSlotsByName(USBDataSourceConfigWidget)

    def retranslateUi(self, USBDataSourceConfigWidget):
        USBDataSourceConfigWidget.setWindowTitle(QCoreApplication.translate("USBDataSourceConfigWidget", "USB Data Source Config"))
        self.groupBox.setTitle(QCoreApplication.translate("USBDataSourceConfigWidget", "USB Device Settings"))
        self.deviceLabel.setText(QCoreApplication.translate("USBDataSourceConfigWidget", "Device:"))
        self.autoConnectCheckBox.setText(QCoreApplication.translate("USBDataSourceConfigWidget", "Automatically connect to device"))
