# -*- coding: utf-8 -*-

################################################################################
## Form generated manually to match Qt UI Compiler output style for CP2130
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


class Ui_Cp2130DataSourceConfigWidget(object):
    def setupUi(self, Cp2130DataSourceConfigWidget):
        if not Cp2130DataSourceConfigWidget.objectName():
            Cp2130DataSourceConfigWidget.setObjectName(u"Cp2130DataSourceConfigWidget")
        Cp2130DataSourceConfigWidget.resize(400, 84)
        self.formLayout = QFormLayout(Cp2130DataSourceConfigWidget)
        self.formLayout.setObjectName(u"formLayout")

        # Row 1: Connect button
        self.label1 = QLabel(Cp2130DataSourceConfigWidget)
        self.label1.setObjectName(u"label1")
        self.label1.setAlignment(Qt.AlignRight | Qt.AlignTrailing | Qt.AlignVCenter)
        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label1)

        self.connectButton = QPushButton(Cp2130DataSourceConfigWidget)
        self.connectButton.setObjectName(u"connectButton")
        icon = QIcon(QIcon.fromTheme(u"network-connect"))
        self.connectButton.setIcon(icon)
        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.connectButton)

        # Row 2: Wide input checkbox
        self.label2 = QLabel(Cp2130DataSourceConfigWidget)
        self.label2.setObjectName(u"label2")
        self.label2.setAlignment(Qt.AlignRight | Qt.AlignTrailing | Qt.AlignVCenter)
        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label2)

        self.wideInputCheckBox = QCheckBox(Cp2130DataSourceConfigWidget)
        self.wideInputCheckBox.setObjectName(u"wideInputCheckBox")
        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.wideInputCheckBox)

        # Tab order
        QWidget.setTabOrder(self.connectButton, self.wideInputCheckBox)

        self.retranslateUi(Cp2130DataSourceConfigWidget)
        QMetaObject.connectSlotsByName(Cp2130DataSourceConfigWidget)

    def retranslateUi(self, Cp2130DataSourceConfigWidget):
        Cp2130DataSourceConfigWidget.setWindowTitle(QCoreApplication.translate(
            "Cp2130DataSourceConfigWidget", u"CP2130 Data Source Configuration", None))
        self.label1.setText(QCoreApplication.translate(
            "Cp2130DataSourceConfigWidget", u"Connect:", None))
        self.connectButton.setToolTip(QCoreApplication.translate(
            "Cp2130DataSourceConfigWidget", u"Connect to CP2130 device", None))
        self.label2.setText(QCoreApplication.translate(
            "Cp2130DataSourceConfigWidget", u"Wide input mode:", None))
        self.wideInputCheckBox.setToolTip(QCoreApplication.translate(
            "Cp2130DataSourceConfigWidget", u"Enable wide input mode on CP2130", None))
