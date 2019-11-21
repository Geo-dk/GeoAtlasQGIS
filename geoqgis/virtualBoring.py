from qgis.gui import *
from qgis.core import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from .utils import *
from .ApiKeyGetter import *
from .virtualBoring_dialog import *

class VirtualBoringTool():
    def __init__(self, iface, apiKeyGetter):
        self.iface = iface
        self.apiKeyGetter = apiKeyGetter
        self.dlg = None
        self.dirpath = os.path.dirname(os.path.realpath(__file__))
        self.workinglayer = None
        self.boring = None
        self.DEFAULTLAYERNAME = "GAL - Virtual Boring"

    def display_point(self, pointToolCoordinates ): 
        self.iface.mapCanvas().unsetMapTool(self.pointTool)
        coords = self.transformToCorrectCRS(pointToolCoordinates)
        self.getBoring(coords)
    
    def transformToCorrectCRS(self, coords, crs = 25832):
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
        if layers is not None and len(layers) > 0 and layerIsVector(layers[0]):
            self.workinglayer = layers[0]
        else:
            self.makeLayer()
       
        self.x = coords[0]
        self.y = coords[1]
        if self.workinglayer.dataProvider().featureCount() > 0:
            self.workinglayer.dataProvider().truncate()
        self.boring = self.addBoringSpot(self.x, self.y)
        self.updateAvaibleModels(coords)
        self.updateBoring()
        self.workinglayer.triggerRepaint()

    def addBoringSpot(self, x, y):
        feat = QgsFeature(self.workinglayer.fields())
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
        (res, outFeats) = self.workinglayer.dataProvider().addFeatures([feat])
        return outFeats

    def updateBoring(self):
        self.iface.addDockWidget( Qt.RightDockWidgetArea, self.dock )
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
        return requests.get("https://data.geo.dk/api/v2/virtualboring?modelId= " + str(modelid) + "&type=bar&x=" + str(x) + "&y=" + str(y) + "&maxDepth=" + str(depth),
                               headers={'authorization': apikey})

    def makeUi(self):
        self.dlg = VirtualBoringDialog(self)
        self.dock = QDockWidget("VirtualBoring", self.iface.mainWindow())
        self.dlg.setUpdateFunction(self.updateBoring)
        self.dock.setWidget(self.dlg)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)

    def getUrlToBoring(self):
        pass

    def updateAvaibleModels(self, coords):
        self.currentModels = getModelsFromCordList([coords], self.apiKeyGetter.getApiKey())
        self.updateDisplayedModels()
        #If no models exist for this area, use the Terræn model.
        self.modelid = self.getCurrentModel()

    def getCurrentModel(self):
        if self.currentModels:
            try:
                #Get the currently selected model in the combobox.
                self.modelid = next(item for item in self.currentModels if item["Name"] == self.dlg.getModelChoice())['ID']
            except StopIteration as e:
                #If there is no model selected currently, then select the first one or zero of none exists.
                debugMsg(e)
                if self.currentModels:
                    self.modelid = self.currentModels[0]['ID'] 
                else:
                    self.modelid = 0
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
