# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GeoQGIS
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
import requests
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtSvg import QSvgWidget, QSvgRenderer
from PyQt5.QtWebKitWidgets import QWebView
# Initialize Qt resources from file resources.py

import time
from qgis.gui import *
from qgis.core import *
from operator import itemgetter
import os
import locale
import ctypes
import urllib.parse
import tempfile
from threading import Thread, Lock
import re

from .utils import *
from .virtualBoring import *
from .ApiKeyGetter import *
from .SliceTool import *
from .resources import *
from .Crosssection import *
from .report import *
import threading


class GeoQGIS:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        # Used for finding files in the directory.
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        # Currently unused, but useful if we start translating.
        # locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'GeoQGIS_{}.qm'.format("en"))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.settings = Settings()
        self.settings.settings_updated.connect(self.reloadMenu)
        self.options_factory = OptionsFactory(self.settings)
        self.options_factory.setTitle(self.tr('GeoAtlas'))
        iface.registerOptionsWidgetFactory(self.options_factory)
        iface.mapCanvas().setPreviewJobsEnabled(False)
       

        # Declare instance attributes
        # Actions for action bar
        self.actions = []
        self.menu = self.tr(u'&GeoQGIS')
        self.currentModels = None
        
        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        self.svgWidget = None
        self.modelid = 0 
        self.apiKeyGetter = ApiKeyGetter(self.iface, self.settings)
        self.apiKey = self.apiKeyGetter.getApiKey()
        self.addModelsToMap(createonlyfile=True)
        self.elemdict = None
        self.createElemDict()
        self.virtualBoring = VirtualBoringTool(self.iface, self.elemdict, self.apiKeyGetter)
        self.sliceTool = SliceTool(self.iface, self.elemdict, self.apiKeyGetter)
        self.crosssectionTool = Crosssection(self.iface, self.elemdict, self.apiKeyGetter, self.settings)
        self.report = ReportTool(self.iface, self.apiKeyGetter)
        # Timer is used for regularly updating tokens and keeping access to 
        # wms layers as the tokens only last for 22 hours.
        self.register_timer_for_token_updater()
        self.update_GAL_layers_with_tokens()
        

        

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('GeoQGIS', message)

    def register_timer_for_token_updater(self):
        # When we load a new project, update the tokens in it.
        self.iface.projectRead.connect(self.update_token_on_project_load)
        self.timer = QTimer()
        
        self.timer.timeout.connect(self.update_GAL_layers_with_tokens)
        self.timer.start(1000 * 60 * 30) #Is in miliseconds. So runs every half hour
        # Should be okay as it last for 22 hours.

    def update_token_on_project_load(self):
        # Wait for 10 seconds before updating tokens, as it seems doing it while loading 
        # makes QGIS crash.
        self.timer.singleShot(10000, self.update_GAL_layers_with_tokens)

    def makeMenu(self):
        # Tool bar menu.
        self.menu = QMenu( "GeoAtlas", self.iface.mainWindow().menuBar() )
        actions = self.iface.mainWindow().menuBar().actions()
        lastAction = actions[-1]
        self.iface.mainWindow().menuBar().insertMenu( lastAction, self.menu )
        self.menu.addAction( 'Add models to map', self.addModelsToMap)
        #self.menu.addAction( 'Print Api Key', self.apiKeyGetter.printApiKey)
        self.menu.addAction( 'Add Boreholes to map', self.addBoreHoles)
        self.menu.addAction( 'Update Tokens', self.update_GAL_layers_with_tokens)
        self.menu.addAction( 'Help', self.helpmessagebox)
        self.menu.addAction( 'About', self.aboutmessagebox)

        self.myToolBar = self.iface.mainWindow().findChild( QToolBar, u'GeoAtlasToolBar' )
        if not self.myToolBar:
            self.myToolBar = self.iface.addToolBar( u'GeoAtlasToolBar' )
            self.myToolBar.setObjectName( u'GeoAtlasToolBar' )

        self.addActionsToActionBar()
        # add toolbar button and menu item

    def update_GAL_layers_with_tokens(self):
        debugMsg("Updating Tokens.")
        token_regex = r'(&|%26)?token([=:]|%3A|%3D)(?P<Token>[\d\w\.=+-_\/]*)'
        #Find all layers with tokens in them, which are updatable and created by us.
        for layer in self.iface.mapCanvas().layers():
            if not layer.name().startswith("GAL"):
                continue
            if not type(layer) is QgsRasterLayer:
                continue
            if not callable(getattr(layer, "dataProvider", None)):
                continue    
            if not callable(getattr(layer.dataProvider(), "dataSourceUri", None)):
                continue
            uri = layer.dataProvider().dataSourceUri()
            token =  re.search(token_regex, uri)
            if not token:
                continue
            token = token.group('Token')
            # make sure the function exists, else we crash
            if callable(getattr(layer, "setDataSource", None)):
                debugMsg("  Updated Token for layer: " + layer.name())
                uri = uri.replace(token, self.apiKeyGetter.getApiKeyNoBearer())
                layer.setDataSource(uri, layer.name(), 'wms', QgsDataProvider.ProviderOptions()) 



    def addActionsToActionBar(self):
        # The action menu bar. 
        crosstool = QAction(QIcon( self.plugin_dir + "/images/cross.png"), 'Get profile of existing line', self.iface.mainWindow())
        crosstool.triggered.connect(self.crosssectionTool.crossectionExistingLine)
        self.myToolBar.addAction(crosstool)
        crosstool2 = QAction(QIcon( self.plugin_dir + "/images/crossNew.png"), 'Get profile of new line', self.iface.mainWindow())
        crosstool2.triggered.connect(self.crosssectionTool.createNewLineAndCrossSection)
        self.myToolBar.addAction(crosstool2)
        slicetool = QAction(QIcon( self.plugin_dir + "/images/slice.png"), 'Open Slice view', self.iface.mainWindow())
        slicetool.triggered.connect(self.sliceTool.startSliceTool)
        self.myToolBar.addAction(slicetool)
        boretool = QAction(QIcon( self.plugin_dir + "/images/bore.png"), 'Make virtual borehole', self.iface.mainWindow())
        boretool.triggered.connect(self.virtualBoring.changeToBoringTool)
        self.myToolBar.addAction(boretool)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        self.makeMenu()
        # will be set False in run()
        self.first_start = True

    def unload(self):
        self.clearMenu()
        
    def helpmessagebox(self):
        msgBox = QMessageBox()
        msgBox.setWindowTitle( "Help" )
        msgBox.setTextFormat( Qt.RichText )
        msgBox.setText( "<br>We Have two manuals to help you along<br>" 
            + "GeoAtlasLive Manual: <a href='{0}'>{0}</a><br><br>".format("https://wgn.geo.dk/geodata/GeoAtlasLive_Manual.pdf")
            + "Plugin Manual: <a href='{0}'>{0}</a><br><br>".format("https://wgn.geo.dk/geodata/GeoAtlasPlugin_Manual.pdf"))

        msgBox.setStandardButtons( QMessageBox.Ok )
        msgBox.exec_() 

    def aboutmessagebox(self):
        title = "About"
        message = "QGIS implementation of GeoAtlasLive\n"
        message += "Version 1.2\n"
        message += "Copyright (c) 2019 GEO\n"
        message += "data@geo.dk"
        QMessageBox.information(self.iface.mainWindow(), title, message)

    def reloadMenu(self):
        self.clearMenu()
        self.makeMenu()
    
    def clearMenu(self):
        del self.myToolBar
        # Remove the actions and submenus
        self.menu.clear()
        # remove the menu bar item
        if self.menu:
            self.menu.deleteLater()

    def addBoreHoles(self):
        # Add boreholes with labels as a wms to current project.
        uri = self.getBoreHoleUri()
        wmsLayer = QgsRasterLayer(uri,"GAL - Boreholes","wms")
        wmsLayer.dataProvider().setDataSourceUri(uri)
        QgsProject.instance().addMapLayer(wmsLayer, False)
        add_layer_to_group(wmsLayer)
        wmsLayer.triggerRepaint()

    def getBoreHoleUri(self):
        # Build up the uri
        quri = QgsDataSourceUri()
        quri.setParam("IgnoreGetFeatureInfoUrl", '1') 
        quri.setParam("IgnoreGetMapUrl", '1')
        quri.setParam("contextualWMSLegend", '0')
        quri.setParam("crs", 'EPSG:25832')
        quri.setParam("dpiMode", '7')
        quri.setParam("featureCount", '10')
        quri.setParam("format", 'image/png')
        quri.setParam("layers", 'GEO-Services:borehole-filtered')
        quri.setParam("styles", 'GEO-Services:borehole_labels')
        url = 'https://data.geo.dk/map/GEO-Services/wms?VERSION=1.3.0&FORMAT=image%2Fpng&TRANSPARENT=true&layers=borehole-filtered&styles=borehole_labels&CRS=EPSG%3A25832&STYLES='
        url += "&token=" + str(self.apiKeyGetter.getApiKeyNoBearer())
        quri.setParam("url", url)
        uri = str(quri.encodedUri())[2:-1]
        return uri



    def addModelsToMap(self, createonlyfile = False):
        #Get the models the user has avaiable.
        #debugMsg(self.apiKeyGetter.getApiKey())
        r = requests.get("https://data.geo.dk/api/v3/geomodel?geoareaid=1", headers={'authorization': self.apiKeyGetter.getApiKey()})
        #debugMsg(r)
        models = r.json()

        #Build the string of the models.
        modelsstring = ""
        for model in models:
            modelsstring += str(model['ID']) + ","
        #-1 is used on the website
        modelsstring += "-1"
        # TODO: find a way of not using a directory. In memory should be possible
        #should be crossplatform method of saving to tempdir.
        tmppath = str(tempfile.gettempdir()) + "\\GeoAtlas\\"
        url = "https://data.geo.dk/map/GEO-Services/wfs?service=WFS&version=1.0&REQUEST=GetFeature&typeName=GEO-Services:geomodel_area&CQL_FILTER=GeoModelId%20in%20(" + modelsstring + ")"
        url += "&token=" + str(self.apiKeyGetter.getApiKeyNoBearer())
        wfs = requests.get(url)
        if not os.path.isdir(tmppath):
            os.mkdir(tmppath)
        #Save it to file, because qgsvectorlayer only works with files.
        fil = open(tmppath + "models.wfs", "wb")
        fil.write(wfs.content)
        wfspath = os.path.realpath(fil.name)
        fil.close()
        if not createonlyfile:
            vlayer = QgsVectorLayer(wfspath,"GAL - Models", "ogr")
            
            if vlayer.isValid():
                
                #Set style with: vlayer.renderer().symbol().symbolLayers()[0].
                #Documented here: https://qgis.org/api/classQgsSimpleFillSymbolLayer.html
                #Remove fill and only have outline.
                vlayer.renderer().symbol().symbolLayers()[0].setBrushStyle(0)
                QgsProject.instance().addMapLayer(vlayer, False)
                add_layer_to_group(vlayer)

    def createElemDict(self):

        tmppath = str(tempfile.gettempdir()) + "\\GeoAtlas\\"
        tree = ET.parse(tmppath + "models.wfs")

        tempList = []
        ids = []
        coords = []
        ETdict = {}

        for child in tree.getroot():
            for c in child.iter():
                tempId = c.find('{www.geo.dk/Services/1.0.0}GeoModelId')
                if tempId is not None:
                    ids.append(tempId.text)
                p = c.find('{http://www.opengis.net/gml}MultiPolygon')
                if p:
                    tempList.append(p)
                    break
                p = c.find('{http://www.opengis.net/gml}Polygon')
                tempList.append(p)

        for y in tempList:
            if y is not None:
                if y.tag == '{http://www.opengis.net/gml}MultiPolygon':
                    l = []
                    for x in y.iter('{http://www.opengis.net/gml}coordinates'):
                        l.append(x.text)
                    coords.append(l)
                elif y.tag == '{http://www.opengis.net/gml}Polygon':
                    for p in y.iter('{http://www.opengis.net/gml}coordinates'):
                        coords.append([p.text])
                        break

        for i in range(len(ids)):
            l = []
            for y in coords[i]:
                l.append(y.replace(" ", ";"))
            ETdict[ids[i]] = l
        
        self.elemdict = ETdict