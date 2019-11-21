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

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'Crosssection_dialog_base.ui'))


class CrosssectionDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, updateFunction, parent=None):
        """Constructor."""
        super(CrosssectionDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.Refresh.clicked.connect(updateFunction)
        self.ModelComboBox.activated.connect(updateFunction)
        self.depthNumber.setValue(self.depthslider.value())
        
    def setHtml(self, html):
        #Uses WebKitView as WebEngine has to be started before QGIS
        #So if WebKitView gets deprecrated completely, som fix will have to found
        self.htmlFrame.setHtml(html)

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

    def getDrillDistance(self):
        return self.drilldistance.value()


    def setSeportFunction(self, function):
        self.Report.clicked.connect(function)

    def getHtmlFrame(self):
        return self.htmlFrame

