# -*- coding: utf-8 -*-
import os
from PyQt5 import QtGui, uic
from PyQt5.QtWidgets import QFileDialog
from qgis.gui import (QgsOptionsPageWidget)
from PyQt5.QtWidgets import  QVBoxLayout
from .qgissettingmanager import *



WIDGET, BASE = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), 'settings.ui')
)

class ConfigOptionsPage(QgsOptionsPageWidget):

    def __init__(self, parent, settings):
        super(ConfigOptionsPage, self).__init__(parent)
        self.settings = settings
        self.config_widget = ConfigDialog(self.settings)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setMargin(0)
        self.setLayout(layout)
        layout.addWidget(self.config_widget)
        self.setObjectName('GeoAtlasOptions')

    def apply(self):
        self.config_widget.accept_dialog()
        self.settings.emit_updated()

class ConfigDialog(WIDGET, BASE, SettingDialog):
    def __init__(self, settings):
        super(ConfigDialog, self).__init__(None)
        self.setupUi(self)
        self.settings = settings
        
        self.use_custom_file.setChecked(self.settings.value('use_custom_file'))
        if self.settings.value('use_custom_file'):
            self.browseLocalFileButton.setEnabled(True)
        else:
            self.browseLocalFileButton.setEnabled(False)
        self.role_checkbox.setChecked(self.settings.value('role_checkbox'))
        if(self.settings.value('role_checkbox')):
            self.role.setEnabled(True)
        else:
            self.role.setEnabled(False)
            self.role.setText('')
            self.settings.set_value('role', '')

        self.browseLocalFileButton.clicked.connect(self.browseLocalFile)
        self.use_custom_file.clicked.connect(self.useLocalChanged)
        self.role_checkbox.clicked.connect(self.useCustomRoleChanged)
        
        SettingDialog.__init__(self, settings)
        
    def browseLocalFile(self):
        qpt_file, f = QFileDialog.getOpenFileName(
            self,
            "Template File",
            self.custom_qpt_file.text(),
            "qpt (*.qpt)"
        )
        if qpt_file:
            self.settings.set_value('custom_qpt_file', qpt_file)
            self.custom_qpt_file.setText(qpt_file)

    def useLocalChanged(self, checked):
        if self.use_custom_file.isChecked():
            self.settings.set_value('use_custom_file', True)
            self.browseLocalFileButton.setEnabled(True)
        else:
            self.settings.set_value('use_custom_file', False)
            self.browseLocalFileButton.setEnabled(False)

    def useCustomRoleChanged(self, checked):
        if self.role_checkbox.isChecked():
            self.settings.set_value('role_checkbox', True)
            self.role.setEnabled(True)
        else:
            self.settings.set_value('role_checkbox', False)
            self.role.setEnabled(False)
            self.role.setText('')
            self.settings.set_value('role', '')

