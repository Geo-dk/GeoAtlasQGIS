from qgis.gui import *
from qgis.core import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from .utils import *
from .ApiKeyGetter import *
from .virtualBoring_dialog import *

class VirtualBoringTool():
    def __init__(self, iface, elemtree, apiKeyGetter):
        self.iface = iface
        self.apiKeyGetter = apiKeyGetter
        self.dlg = None
        self.dirpath = os.path.dirname(os.path.realpath(__file__))
        self.workinglayer = None
        self.boring = None
        self.DEFAULTLAYERNAME = "GAL - Virtual Boring"
        self.modelid = 0
        self.elemdict = elemtree

    def display_point(self, pointToolCoordinates ): 
        # Gets the coordinates in and changes the users tool back.
        self.iface.mapCanvas().unsetMapTool(self.pointTool)
        coords = self.transformToCorrectCRS(pointToolCoordinates)
        self.getBoring(coords)
    
    def transformToCorrectCRS(self, coords, crs = "EPSG:25832"):
        xform = QgsCoordinateTransform()
        xform.setSourceCrs(self.iface.mapCanvas().mapSettings().destinationCrs())
        xform.setDestinationCrs(QgsCoordinateReferenceSystem(crs))
        x = coords.x()
        y = coords.y()
        return [xform.transform(x, y).x(), xform.transform(x,y).y()]

    def getBoring(self, coords):
        if self.dlg is None:
            self.makeUi()
        layers = QgsProject.instance().mapLayersByName(self.DEFAULTLAYERNAME)
        # If we dont make sure we operate on our layer, we might delete users data
        if layers is not None and len(layers) > 0 and layerIsVector(layers[0]):
            self.workinglayer = layers[0]
        else:
            self.makeLayer()
       
        self.x = coords[0]
        self.y = coords[1]

        #Remove all borings on layer and make a new one.
        if self.workinglayer.dataProvider().featureCount() > 0:
            self.workinglayer.dataProvider().truncate()
        self.boring = self.addBoringSpot(self.x, self.y)
        self.updateAvailableModels(coords)
        self.firstBoring()
        self.updateDisplayedModels()
        self.workinglayer.triggerRepaint()

    def addBoringSpot(self, x, y):
        feat = QgsFeature(self.workinglayer.fields())
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
        (res, outFeats) = self.workinglayer.dataProvider().addFeatures([feat])
        return outFeats

    def updateBoring(self):
        self.iface.addDockWidget( Qt.RightDockWidgetArea, self.dock )
        debugMsg("Updating the boring from dropdown")
        # Use task for multithreading
        self.sectionTask = QgsTask.fromFunction('Update Boring', self.makeBoring, self.x, self.y, self.setModel(), self.dlg.getDepth(), self.apiKeyGetter.getApiKey(), on_finished=self.boringcallback)
        QgsApplication.taskManager().addTask(self.sectionTask)

    def firstBoring(self):
        self.iface.addDockWidget( Qt.RightDockWidgetArea, self.dock )
        debugMsg("Making original boring")
        # Use task for multithreading
        self.sectionTask = QgsTask.fromFunction('Update Boring', self.makeBoring, self.x, self.y, self.getCurrentModel(), self.dlg.getDepth(), self.apiKeyGetter.getApiKey(), on_finished=self.boringcallback)
        QgsApplication.taskManager().addTask(self.sectionTask)

    def boringcallback(self, result, message):
        self.dlg.updateImage(message.content)
        

    def makeLayer(self):
        self.workinglayer = QgsVectorLayer("Point?crs=epsg:25832", self.DEFAULTLAYERNAME, "memory")
        QgsProject.instance().addMapLayer(self.workinglayer, False)
        add_layer_to_group(self.workinglayer)
        self.workinglayer.loadNamedStyle(self.dirpath + "\\styles\\dotstyle.qml")

    def makeBoring(self, task, x, y, modelid, depth, apikey):
        return requests.get("https://data.geo.dk/api/v3/virtualboring?geoareaid=1&modelId= " + str(modelid) + "&type=bar&x=" + str(x) + "&y=" + str(y) + "&maxDepth=" + str(depth),
                               headers={'authorization': apikey})

    def makeUi(self):
        self.dlg = VirtualBoringDialog(self)
        self.dock = QDockWidget("VirtualBoring", self.iface.mainWindow())
        self.dlg.setUpdateFunction(self.updateBoring)
        self.dock.setWidget(self.dlg)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)

    def getUrlToBoring(self):
        pass

    def updateAvailableModels(self, coords):
        #self.currentModels = getModelsFromCoordList([coords], self.apiKeyGetter.getApiKey())
        self.currentModels = get_models_for_point(coords, self.elemdict, self.apiKeyGetter.getApiKey())
        #If no models exist for this area, use the Terræn model.
        #self.modelid = self.getCurrentModel()

    def getCurrentModel(self):
        
        prevmodelid = self.modelid
        #debugMsg("prev: " + str(prevmodelid))
        if self.currentModels:
            # see if current selected is in currentmodels
            for model in self.currentModels:
                if model['ID'] == prevmodelid:
                    #debugMsg("found it " + str(model['ID']))
                    self.modelid = model['ID']
                    return self.modelid
            # pick the highest priority model otherwise
            highestPriority = -100
            for model in self.currentModels:
                if model['Priority'] > highestPriority:
                    highestPriority = model['Priority']
                    self.modelid = model['ID']
            #debugMsg(self.modelid)
        self.updateDisplayedModels()
        return self.modelid
        
    def setModel(self):
        if self.currentModels:
            self.modelid = next(item for item in self.currentModels if item["Name"] == self.dlg.getModelChoice())['ID'] 
        else: 
            highestPriority = -100
            for model in self.currentModels:
                if model['Priority'] > highestPriority:
                    highestPriority = model['Priority']
                    self.modelid = model['ID']
        #debugMsg(self.modelid)
        return self.modelid

    def updateDisplayedModels(self):
        if self.currentModels:
            self.dlg.setModels([item['Name'] for item in self.currentModels if 'Name' in item])

    def changeToBoringTool(self):
     # a reference to our map canvas
        # this QGIS tool emits as QgsPoint after each click on the map canvas
        self.pointTool = QgsMapToolEmitPoint(self.iface.mapCanvas())

        self.pointTool.canvasClicked.connect(self.display_point)

        self.iface.mapCanvas().setMapTool(self.pointTool)
