import urllib.parse
from .Slice_dialog import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtXml import *
from .utils import *
from qgis.gui import *
from qgis.core import *

 
MAPTYPE = "IgnoreGetFeatureInfoUrl=1&IgnoreGetMapUrl=1&contextualWMSLegend=0&crs=EPSG:25832&dpiMode=7&featureCount=10&format=image/png&layers=" #slice-kote-524 #TYPE_MODELID
URLPART1 = "https://data.geo.dk/mapv2/slice-tools?VERSION%3D1.3.0%26TRANSPARENT%3DTRUE%26LAYERS%3D" #slice_dhm #TYPE
URLPART2 = "%26viewparams%3Dmodel%3A" #30 #MODELID
URLPART3 = "%3B" #-10 #LEVEL


class SliceTool():
    def __init__(self, iface, elemtree, apiKeyGetter):
        self.iface = iface
        self.apiKeyGetter = apiKeyGetter
        self.sliceDepth = 10
        self.modelid = 2
        self.model = None
        self.wmsLayer = None
        self.dlg = None
        self.elemdict = elemtree
 
    def startSliceTool(self):
        self.wmsLayer = None # reset the selected layer
        # Preview jobs is stuff rendered around the current view.
        # The were disabled in hope of removing crashes
        # As it appears that crashes happens when changing the layer while
        # it is rendering.
        if self.iface.mapCanvas().previewJobsEnabled():
            self.iface.mapCanvas().setPreviewJobsEnabled(False)

        if self.dlg is None:
            self.make_ui()
      
        

        self.getModels()
        uri = self.build_uri(self.dlg.getSliceType(), self.dlg.getDepth(), self.modelid)
        # Create the temporary layer we can work on and get crs from
        self.wmsLayer = QgsRasterLayer(uri,self.updateLayerName(self.dlg.getSliceType(), self.dlg.getDepth()),"wms")
        QgsProject.instance().addMapLayer(self.wmsLayer, False)
        add_layer_to_group(self.wmsLayer)
        if self.wmsLayer.renderer() is not None:
            self.wmsLayer.renderer().setOpacity(0.6)
            self.show_ui()
        else:
            self.iface.messageBar().pushMessage("Error:", "Something went wrong with getting slice. Possibly a connection problem. If error persist, contact data@geo.dk",
            level=Qgis.Critical, duration=5)


    def make_ui(self):
        self.dlg = SliceDialog(self)
        self.dock = QDockWidget("Slice tool", self.iface.mainWindow()) 
        self.dock.setWidget(self.dlg)

    def show_ui(self):
        self.iface.addDockWidget( Qt.BottomDockWidgetArea, self.dock )

    def updateSlice(self):
        self.getModels()
        if self.model is not None:
            uri = self.build_uri(self.dlg.getSliceType(), self.dlg.getDepth(), self.modelid)
            self.updateDataProvider(uri, self.updateLayerName(self.dlg.getSliceType(), self.dlg.getDepth()))
            
            self.wmsLayer.triggerRepaint()
        else:
            self.wmsLayer.setName("GAL - Failed in finding models")
            self.dlg.updatelayerName("GAL - Failed in finding models")
            self.iface.messageBar().pushMessage("Warning:", "No models could be found for current area", level=Qgis.Warning, duration=5)

            

    def updateDataProvider(self, uri, layername):
        self.wmsLayer.setDataSource(uri, layername, "wms", QgsDataProvider.ProviderOptions())


    def build_uri(self, slice_type, depth, model):
        quri = QgsDataSourceUri()
        quri.setParam("IgnoreGetFeatureInfoUrl", '1') 
        quri.setParam("IgnoreGetMapUrl", '1')
        quri.setParam("contextualWMSLegend", '0')
        quri.setParam("crs", 'EPSG:25832')
        quri.setParam("dpiMode", '7')
        quri.setParam("featureCount", '10')
        quri.setParam("format", 'image/png')
        quri.setParam("layers", slice_type.replace("_", "-") + "-" + str(model))
        quri.setParam("styles", 'default')
        url = URLPART1 + slice_type 
        url += URLPART2 + str(model)
        url += URLPART3
        if slice_type == "slice_kote":
            url += "level:" + str(depth)
        if slice_type == "slice_dhm":
            url += "depth:" + str(abs(depth))
        url += "&token=" + self.apiKeyGetter.getApiKeyNoBearer()
        quri.setParam("url", url)
        uri = str(quri.encodedUri())[2:-1] #Removes "" around the string 
        debugMsg("Slice uri: " + urllib.parse.unquote(uri))
        return uri

    def updateLayerName(self, sliceType, depth):
        name = "GAL - "
        if self.model:
            name += self.model['Name']
        if sliceType == "slice_kote":
            name += ", Kote, Niveau: "
            name += str(depth) + "m"
        if sliceType == "slice_dhm":
            name += ", DHM, Dybde: "
            name += str(abs(depth)) + "m"
        self.dlg.updatelayerName(name)
        self.setDisplayedModel(self.model)
        return name

    def getModels(self):
        point = self.iface.mapCanvas().center() 
        # Get model intersecting center of screen
        self.currentModels = get_models_for_point([point.x(), point.y()], self.elemdict, self.apiKeyGetter.getApiKey())
        self.modelid = 0 
        if self.currentModels:
            try:
                #Get the currently selected model in the combobox.
                self.model = next(item for item in self.currentModels if item["Name"] == self.dlg.getModelChoice())
                
            except StopIteration as e:
                #If there is no model selected currently, then select the one with highest priority.
                highestPriority = -100
                for model in self.currentModels:
                    if model['Priority'] > highestPriority:
                        highestPriority = model['Priority']
                        self.model = model
            self.modelid = self.model['ID']
            self.dlg.setModels([item['Name'] for item in self.currentModels if 'Name' in item])

    def getBboxFromScreen(self):
        xform = QgsCoordinateTransform()
        if self.iface.activeLayer() is None:
            xform.setSourceCrs(self.iface.mapCanvas().mapSettings().destinationCrs())
        else:
            xform.setSourceCrs(self.iface.activeLayer().crs())
        xform.setDestinationCrs(QgsCoordinateReferenceSystem.fromEpsgId(25832))
        QTcord = xform.transformBoundingBox(self.iface.mapCanvas().extent())

        xMin = QTcord.xMinimum()
        xMax = QTcord.xMaximum()
        yMin = QTcord.yMinimum()
        yMax = QTcord.yMaximum()

        return GeoBoundingBox(xMin, yMin, xMax, yMax )

    def changeSelectedlayer(self):
        if self.iface.activeLayer() and isinstance(self.iface.activeLayer(), type(self.wmsLayer)) and self.iface.activeLayer().dataProvider().name() == "wms":
            self.wmsLayer = self.iface.activeLayer()
            name = self.iface.activeLayer().name()
            self.dlg.updatelayerName(name)
    
    def setDisplayedModel(self, model):
        models = [item['Name'] for item in self.currentModels if 'Name' in item]
        index = models.index(model['Name'])
        self.dlg.ModelComboBox.setCurrentIndex(index)