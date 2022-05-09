from .utils import *
from .ApiKeyGetter import *
from .Crosssection_dialog import CrosssectionDialog
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtSvg import QSvgWidget, QSvgRenderer
from PyQt5.QtWebKitWidgets import QWebView
from qgis.gui import *
from qgis.core import *
from operator import itemgetter
from qgis.PyQt.QtXml import QDomDocument
import os 
from .virtualBoring_dialog import *
import math
import threading
import requests
import urllib.parse
import math
import processing
from processing.core.Processing import Processing
from qgis.analysis import QgsNativeAlgorithms
import re
Processing.initialize()
QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

DEFAULTLAYERNAME = 'GAL - Lines'

class CrosssectionSettings():
    #Used for sending settings for crosssection around. Default values here work
    def __init__(self):
        self.depth = 30
        self.width = 1000
        self.height = 150
        self.modelid = 0
        self.drilldistance = 0
        self.linepoint = 10
        self.pixelsperx = 50

class Crosssection():
    
    def __init__(self, iface, elemtree, apiKeyGetter, usersettings):
        self.iface = iface
        self.apiKeyGetter = apiKeyGetter
        self.currentModels = None
        self.svgWidget = None
        self.modelid = 0 
        self.workinglayer = None
        self.dlg = None
        self.dirpath = os.path.dirname(os.path.realpath(__file__))
        self.usersettings = usersettings
        self.elemdict = elemtree

    def vectorLineIsSelected(self):
        if layerIsVector(self.iface.activeLayer()) and self.getSelectedLine(self.iface.activeLayer()):
            return True
        return False

    def crossectionExistingLine(self): 
        # If we already have UI, we shouldnt make a new one.
        if self.dlg is None:
            self.makeUI()       
        self.chooseOrMakeAppropriateLayer()
        self.updateCrosssection()

    def createNewLineAndCrossSection(self):
        if self.dlg is None:
            self.makeUI()       
        self.chooseOrMakeAppropriateLayer()
        self.addFeatureAndSectionIt()

    def makeUI(self):
        self.dlg = CrosssectionDialog(self.updateCrosssection)
        self.dock = QDockWidget("Crosssection", self.iface.mainWindow()) 

        self.dock.setWidget(self.dlg)
        self.show_ui()
        self.dlg.setSeportFunction(self.testReport)

    def show_ui(self):
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.dock )

    def addFeatureAndSectionIt(self):
        # Go into editing mode.
        self.getworkinglayer().startEditing()
        # Change the mouse mode to adding feature.
        self.iface.actionAddFeature().trigger()
        #Make it update crossection when its done.
        # By having the tool call when feature is done.
        self.featureTool = self.iface.mapCanvas().mapTool()
        # TODO: Fix that both of these removes the connections.
        self.iface.mapCanvas().mapTool().deactivated.connect(self.removeFeatureConnect)
        self.getworkinglayer().featureAdded.connect(self.crossSectionLastAdded)
        
    def removeFeatureConnect(self):
        #TODO: Fix that this gets called without anythign to disconnect
        try:
            self.getworkinglayer().featureAdded.disconnect(self.crossSectionLastAdded)
        except:
            pass
        try:
            self.featureTool.deactivated.disconnect(self.removeFeatureConnect)
        except:
            pass

    def crossSectionLastAdded(self, fid):
        # The featureid (fid) comes from the feature being added.
        self.getworkinglayer().selectByIds([fid])
        self.iface.actionSelect().trigger()
        self.getworkinglayer().commitChanges()
        # Save the changes and update the crosssection view
        self.removeFeatureConnect()
        self.updateCrosssection()

    def getworkinglayer(self):
        if self.workinglayer is None:
            self.workinglayer = self.iface.activeLayer()
        return self.workinglayer

    def updateCrosssection(self):
        # All the ifs are to check if the line is usable for getting cordinate info out
        # Could be much prettier
        # TODO: Make pretty
        if layerIsVector(self.getworkinglayer()):
            self.line = self.getSelectedLine(self.getworkinglayer())
            if self.line and hasattr(self.line, '__geo_interface__'):
                line = self.line.__geo_interface__
                if (self.line.__geo_interface__["geometry"]["type"] is 'LineString' or self.line.__geo_interface__["geometry"]["type"] is 'MultiLineString'):
                    #Get the coordinates from selected features.
                    self.crossectionFromLine(self.line)
                else:
                    self.iface.messageBar().pushMessage("Warning:", "Selected Line is not valid", level=Qgis.Warning, duration=5)
            else:
                # Might be incorrect to call this here.
                self.addFeatureAndSectionIt()
        else:
            self.iface.messageBar().pushMessage("Warning:", "No line selected or wrong layer selected.", level=Qgis.Warning, duration=5)

    def chooseOrMakeAppropriateLayer(self):
        # Looks for a the layer to work on, so we dont clutter the project
        if layerIsVector(self.iface.activeLayer()):
            self.workinglayer = self.iface.activeLayer()
            return
        layers = QgsProject.instance().mapLayersByName(DEFAULTLAYERNAME)
        if layers is not None and len(layers) > 0 and layerIsVector(layers[0]):
            self.workinglayer = layers[0]
            self.iface.setActiveLayer(layers[0])
        else: 
            self.makeLayer()
        

    def makeLayer(self):
        layer = QgsVectorLayer("multilinestring?crs=epsg:25832", DEFAULTLAYERNAME, "memory")
        layer.renderer().symbol().setColor(QColor.fromRgb(35, 35, 255))
        layer.renderer().symbol().setWidth(1)
        QgsProject.instance().addMapLayer(layer, False)
        # The style has Colors, labels
        layer.loadNamedStyle(self.dirpath + "\\styles\\linestyle.qml")
        add_layer_to_group(layer)
        self.workinglayer = layer
        self.iface.setActiveLayer(layer)
        self.addFeatureAndSectionIt()

    def crossectionFromLine(self, line):
        #Get the coordinates from selected features.
        coords = reduceTo2dList(line.__geo_interface__["geometry"]["coordinates"])
        self.coords = transformToProjection(25832, coords, self.getworkinglayer())
        self.settings = CrosssectionSettings()
        # Height and width makes sure that the crosssection is as large as possible.
        # The "-80" keeps space for the layer legend
        self.settings.width = self.dlg.getHtmlFrame().frameGeometry().width() - 80
        self.settings.height = self.dlg.getHtmlFrame().frameGeometry().height()
        self.settings.depth = self.dlg.getDepth()
        self.settings.drilldistance = self.dlg.getDrillDistance()
        self.settings.linepoint = self.calculateLinePoint(self.line, self.settings)
        # Tasks are the only way of having working multithreading
        self.sectionTask = QgsTask.fromFunction('Update Crosssection', self.performCrosssection, self.coords, self.settings, on_finished=self.crosssectiontaskcallback)
        QgsApplication.taskManager().addTask(self.sectionTask)
        self.boreHoleBuffer(self.settings)
        

    def crosssectiontaskcallback(self, result, section):
        # Result is a required parameter for tasks to work.
        self.show_ui()
        self.updateDisplayedModels()
        try: # a bit hacky
            if section[0].lower() == "error": self.iface.messageBar().pushMessage("Warning:", section[1], level=Qgis.Warning, duration=5)
        except:
            pass
        if section:
            self.svg = self.fixSvg(section['Svg'], self.settings)
            self.html = self.createHtmlframe(self.svg, self.settings, section, "\\styles\\defaultCSS.css")
            self.updateSVGDisplayed(self.html)

    def performCrosssection(self, task, coords, settings):
        # Task is a required parameter for tasks to work and contains the current tasks
        settings.modelid = self.updateAvailableModels(coords)
        section = self.getCrosssectionFromUri(coords, settings)
        # Returned values in tasks gets send to reciever as parameters
        return section
        
    def calculateLinePoint(self, line, settings):
        # This values seems correct, but was made before the update to have auto in the api
        calculatedvalue = math.ceil(line.geometry().length()/settings.width)
        return max(calculatedvalue, 1)

    def getSelectedLine(self, layer):
        features = layer.selectedFeatures()
        line = {}
        if features:
            line = features[0]
            return line
    
    def updateAvailableModels(self, coords):
        self.currentModels = getModelsFromCoordList(coords, self.apiKeyGetter.getApiKey())
        #If no models exist for this area, use the Terræn model.
        if self.currentModels:
            try:
                #Get the currently selected model in the combobox.
                self.modelid = next(item for item in self.currentModels if item["Name"] == self.dlg.getModelChoice())['ID']
            except StopIteration as e:
                #If there is no model selected currently, then select the first one or zero of none exists.
                # debugMsg("No Models Could be found")
                if self.currentModels:
                    self.modelid = self.currentModels[0]['ID'] 
                else:
                    self.modelid = 0
        return self.modelid

    def updateDisplayedModels(self):
        if self.currentModels:
            self.dlg.setModels([item['Name'] for item in self.currentModels if 'Name' in item])

    def getCrosssectionFromUri(self, coords, settings):
        url = "https://data.geo.dk/api/v3/crosssection?geoareaid=1&path=" + str(coords).replace(" ", "") 
        url += "&geomodelid=" + str(settings.modelid)
        url += "&width=" + str(settings.width)
        url += "&height=" + str(settings.height)
        url += "&maxdepth=" + str(settings.depth)
        url += "&linepointdistance=" + str(settings.linepoint)
        if settings.drilldistance > 0:
            url += "&MaxBoringDistance=" + str(settings.drilldistance)
        # when i am debugging making large / weird crosssections 
        if os.getlogin() == 'NPA': url += "&APIStat=True"
        print(url)

        req = requests.get(url, headers={'authorization': self.apiKeyGetter.getApiKey()})
        if req.status_code == 400: # maybe change to any failure code.
            reg = re.search('(?s)(?<=<h2>)(.+?)(?=</h2>)', req.text) # Get the error
            error = re.sub('<[^>]*>', '', reg.group(1)).strip() #strip whitespace or italics/bold
            debugMsg(error) # print to debug
            return ("error", error)

        json = req.json()
        return json
    
    def fixSvg(self, svg, settings):
        # The returned SVG is missing parts to render currectly. 
        svg = svg.replace("-webkit-font-smoothing: antialiased;", "")
        s = '<svg viewBox="0 0 '
        s+= str(settings.width) + ' ' + str(settings.height)
        s+='" preserveAspectRatio="xMinYMin meet"'
        #Making the svg fit correctly by adding scaling style to it.
        svg = svg.replace('<svg',s,1)
        # v3 fix. Maybe this issue is resolved later. If colors act weird, this is probrably why.
        svg = svg.replace('signature-geounit', 'signatur-geoenhed')
        svg = svg.replace('geounit', 'geoenhed')
        return svg


    def createHtmlframe(self, svg, settings, section, cssfile):
        # The HTML helps make the SVG show more nicely by having the legend at the side
        html = '<!DOCTYPE html> <html><head>'
        html += '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />'
        html += '<title>QGIS</title> <style>'
        f=open(os.path.dirname(os.path.realpath(__file__)) + "/" + cssfile, "r")
        html += f.read()
        f.close()
        html += '</style><body><div class="flex-container">'
        html += svg
        html += self.createLegend(section)
        html += '</div></body></html>'
        return html

    def createLegendframe(self, svg, settings, section, cssfile):
        # The HTML helps make the SVG show more nicely by having the legend at the side
        html = '<!DOCTYPE html> <html><head>'
        html += '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />'
        html += '<title>QGIS</title> <style>'
        f=open(os.path.dirname(os.path.realpath(__file__)) + "/" + cssfile, "r")
        html += f.read()
        f.close()
        html += '</style><body><div class="flex-container">'
        html += self.createLegend(section)
        html += '</div></body></html>'
        return html

    def createLegend(self, section):
        # Behavior should be the same as the websites version here. 
        html = '<ul class="signatur">'
        for geounit in section['Model']['GeoUnits']:
            li = '<li data><span class="signatur-geoenhed-'
            li += str(geounit['Id']) +'">'
            li += '</span><span class="signatur-title">'
            li += str(geounit['Name'])
            li += '</span></li>'
            html += li
        html += '</ul>'
        return html

    def updateSVGDisplayed(self, svg):
        self.dlg.setHtml(svg)

    def getAvailableModels(self, coordinates):
        return getModelsFromCoordList(coordinates, self.apiKeyGetter.getApiKey())

    def boreHoleBuffer(self, settings):
        layer = self.getworkinglayer()
        outlayername = 'GAL - Borings Buffer'
        #Get the layer for buffer if one exists.
        #Else make one
        #Set the buffer to be the right size. 
        output = processing.run('native:buffer', {"INPUT": layer, "SEGMENTS": 12, "END_CAP_STYLE": 1, "JOIN_STYLE": 0, "MITER_LIMIT": 2, "DISSOLVE": False, "DISTANCE": settings.drilldistance, "OUTPUT": 'memory:' + outlayername})
        outputlayers = QgsProject.instance().mapLayersByName(outlayername)
        # If we already have a layer for buffer, use that.
        if len(outputlayers) != 0:
            outputlayer = outputlayers[0]
            #Redo all buffers to be correct width.
            with edit(outputlayer):
                listOfIds = [feat.id() for feat in outputlayer.getFeatures()]
                outputlayer.deleteFeatures(listOfIds)
            for feature in output['OUTPUT'].getFeatures():
                outputlayer.dataProvider().addFeatures([feature])
            outputlayer.triggerRepaint()
        else:
            layertoadd = output['OUTPUT']
            layertoadd.renderer().symbol().setColor(QColor.fromRgb(180,180,180))
            layertoadd.setOpacity(0.4)
            QgsProject.instance().addMapLayer(layertoadd)
        #Change the active layer back, as adding a new one changes it.
        self.iface.setActiveLayer(layer)
            


    def testReport(self):
        # Here there be dragons. 
        # TODO: Refactor this whole functions out into a seperate class.
        if self.usersettings.getlayout() is not '' and os.path.exists(self.usersettings.getlayout()):
            dir_path = self.usersettings.getlayout()
        else:
            dir_path = self.dirpath + "/standardlayout.qpt"
        project = QgsProject.instance()
        self.composition = QgsPrintLayout(project)
        self.composition.initializeDefaults()
        document = QDomDocument()
        # read template content
        template_file = open(dir_path)
        template_content = template_file.read()
        template_file.close()
        document.setContent(template_content)

        # load layout from template and add to Layout Manager
        self.composition.loadFromTemplate(document, QgsReadWriteContext())

        #Set the name to a unique name.
        name = "GeoAtlasReport"
        if project.layoutManager().layoutByName(name) is not None:
            i = 2
            while project.layoutManager().layoutByName(name + str(i)) is not None:
                i = i + 1
            name = name + str(i)
        self.composition.setName(name)
        for frame in self.composition.multiFrames():
            if frame.totalSize().width() >= 0 and frame.totalSize().height() >= 0:
                htmlframe = frame
                legendframe = frame
                break
        settings = CrosssectionSettings()
        settings.depth = self.dlg.getDepth()
        settings.drilldistance = self.dlg.getDrillDistance()
        settings.height = int(htmlframe.frames()[0].sizeWithUnits().height() * 3)#The this is just a magic value ration. 
        settings.linepoint = self.calculateLinePoint(self.line, settings)
        section = self.performCrosssection(None, self.coords, settings)
        if section:
            svg = self.fixSvg(section['Svg'], settings)
            html = self.createHtmlframe(svg, settings, section, "\\styles\\printCSS.css")
            legnd = self.createLegendframe(svg, settings, section, "\\styles\\printCSS.css")
            htmlframe.setHtml(html)
            htmlframe.refresh()

        for item in self.composition.items():
            if str(type(item).__name__) == "QgsLayoutItemMap":
                line = self.line
                bbox = line.geometry().boundingBox()
                coords = reduceTo2dList(line.__geo_interface__["geometry"]["coordinates"])
                rotation = getRotationOfLine(coords)
                bbox.scale(1.1)
                item.zoomToExtent(bbox)
                #scaleFactor = getDistanceOfLine(coords)/ item.extent().width()
                #bbox.scale(scaleFactor) #Det her kan gøres bedre, lodrette og vandrette linjer virker.
                #item.zoomToExtent(bbox)
                item.setMapRotation(rotation)
                
                item.refresh() 
                break
        #do void 	setContentMode (ContentMode mode)
        project.layoutManager().addLayout(self.composition)
        self.composition = project.layoutManager().layoutByName(name)
        self.iface.openLayoutDesigner(self.composition)

        