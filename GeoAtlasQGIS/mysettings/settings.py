# -*- coding: utf-8 -*-
import os
import sys
from PyQt5.QtCore import QFileInfo, QObject
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QFileDialog
from PyQt5.QtGui import QIcon
from qgis.PyQt import QtCore

from .qgissettingmanager import *

class Settings(SettingManager):
    settings_updated = QtCore.pyqtSignal()

    def __init__(self):
        SettingManager.__init__(self, 'GeoAtlas')
        self.add_setting(String('username', Scope.Global, ''))
        self.add_setting(String('password', Scope.Global, ''))
        self.add_setting(String('role', Scope.Global, ''))
        self.add_setting(Bool('use_custom_file', Scope.Global, False))
        self.add_setting(Bool('role_checkbox', Scope.Global, False))
        path = QFileInfo(os.path.realpath(__file__)).path()
        geo_path = path + '/geo/'
        if not os.path.exists(geo_path):
            os.makedirs(geo_path)
            
        self.add_setting(String('cache_path', Scope.Global, geo_path))
        self.add_setting(String('custom_qpt_file', Scope.Global, ''))
        
    def is_set(self):
        if self.value('username') and self.value('password'):
            return True
        return False
    
    def emit_updated(self):
        self.settings_updated.emit()

    def getlayout(self):
        if self.value('use_custom_file'):
            return self.value('custom_qpt_file')
        else:
            return ''

