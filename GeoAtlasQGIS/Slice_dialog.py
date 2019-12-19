# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeoQGISDialog
                                 A QGIS plugin
 GeoQGIS
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2019-01-21
        git sha              : $Format:%H$
        copyright            : (C) 2019 by Geo
        email                : hmd@geo.dk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt5 import uic
from PyQt5 import QtWidgets
from .SliceTool import *

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'forms/Slice_dialoge.ui'))


class SliceDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, slicer, parent=None):
        self.slicer = slicer
        """Constructor."""
        super(SliceDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.Refresh.clicked.connect(self.slicer.updateSlice)
        self.ModelComboBox.activated.connect(self.slicer.updateSlice)
        self.dhmButton.clicked.connect(self.changeToDhmView)
        self.dhmButton.clicked.connect(self.slicer.updateSlice)
        self.levelButton.clicked.connect(self.changeToKoteView)
        self.levelButton.clicked.connect(self.slicer.updateSlice)
        self.selectLayerButton.clicked.connect(self.slicer.changeSelectedlayer)
    
    def updatelayerName(self, text):
        self.selectedLayerLabel.setText(text)

    def changeToKoteView(self):
        self.depthNumber.setMinimum(-200)
        self.depth_text.setText("kote (m)")

    def changeToDhmView(self):
        self.depthNumber.setMinimum(0)
        self.depth_text.setText("dybde (m)")

    def getModelChoice(self):
        return self.ModelComboBox.currentText()

    def setModels(self, models):
        #TODO: Add Terræn 0.4m to the models.
        current = self.ModelComboBox.currentText()
        self.ModelComboBox.clear()
        for name in models:
            self.ModelComboBox.addItem(name)
        index = self.ModelComboBox.findText(current)
        if index >= 0:
            self.ModelComboBox.setCurrentIndex(index)

    def getDepth(self):
        return self.depthNumber.value()

    def getSliceType(self):
        if self.levelButton.isChecked():
            return "slice_kote"
        if self.dhmButton.isChecked():
            return "slice_dhm"
        

