import requests
import tempfile
import os
import json
from qgis.core import QgsProject, QgsVectorLayer, QgsCoordinateReferenceSystem

from .utils import debugMsg, add_layer_to_group

class ModelManager:
    def __init__(self, geo_qgis):
        self.geo_qgis = geo_qgis
        self.elemdict = None

    def addModelsToMap(self, createonlyfile=False):
        if createonlyfile:
            debugMsg("Creating models.json file")
        else:
            debugMsg("Adding models to map")
        base_url = self.geo_qgis.settings.get_geo_base_url()
        r = requests.get(f"{base_url}/api/v3/geomodel?geoareaid=1&format=geojson", headers={'authorization': self.geo_qgis.apiKeyGetter.getApiKey()})
        json_content = r.content.decode('utf-8').replace('\\"', '"')[1:-1]
        
        tmppath = str(tempfile.gettempdir()) + os.sep + "GeoAtlas" + os.sep
        if not os.path.exists(tmppath):
            os.makedirs(tmppath)

        file = open(tmppath + "models.json", "w")
        file.write(json_content)
        jsonpath = os.path.realpath(file.name)
        file.close()

        if not createonlyfile:
            vlayer = QgsVectorLayer(jsonpath, "GAL - Models", "ogr")
            vlayer.setCrs(QgsCoordinateReferenceSystem("EPSG:25832"))  # needs to be done to make sure its not displayed in some other default CRS
            
            if vlayer.isValid():
                # Set style with: vlayer.renderer().symbol().symbolLayers()[0].
                # Documented here: https://qgis.org/api/classQgsSimpleFillSymbolLayer.html
                # Remove fill and only have outline.
                vlayer.renderer().symbol().symbolLayers()[0].setBrushStyle(0)
                QgsProject.instance().addMapLayer(vlayer, False)
                add_layer_to_group(vlayer)
        if self.elemdict is None:
            self.createElemDict()

    def createElemDict(self):
        tmppath = str(tempfile.gettempdir()) + os.sep + "GeoAtlas" + os.sep
        if not os.path.exists(tmppath):
            os.makedirs(tmppath)
        
        fh = open(tmppath + 'models.json', encoding='utf-8')
        tree = json.load(fh)
        ETdict = {}

        for child in tree["features"]:
            id = child['properties']['Id']
            type = child['geometry']['type']
            coordlist = child['geometry']['coordinates']
            if type == 'MultiPolygon':
                coordlist = [item for sublist in coordlist for item in sublist]  # flatten one level
            ETdict[id] = coordlist
        
        self.elemdict = ETdict
        fh.close()

    def ensureElemDict(self):
        if self.geo_qgis.apiKeyGetter.getApiKey() is None:
            return

        model_path = str(tempfile.gettempdir()) + os.sep + "GeoAtlas" + os.sep + 'models.json'
        if not os.path.exists(model_path) or os.path.getsize(model_path) < 5000:
            # update models if doesn't exist or under 5kb
            self.addModelsToMap(createonlyfile=True)
        if self.elemdict is None and os.path.getsize(model_path) > 5000:
            # create if doesn't exist and model.json is larger than 5kb
            self.createElemDict()