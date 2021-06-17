from qgis.core import *
from PyQt5.QtCore import QTimer
import requests
from operator import itemgetter
from math import atan, pi, sqrt
from datetime import datetime
import xml.etree.ElementTree as ET
import tempfile
from shapely import geometry

def add_layer_to_group(layer, groupname='GAL'):
    i = QgsProject.instance()
    r = i.layerTreeRoot()
    if r.findGroup(groupname) is None:
        r.insertGroup(0, groupname)
    if layer is not None and layer.isValid():
        r.findGroup(groupname).insertChildNode(0, QgsLayerTreeLayer(layer))

def transformToProjection(projection, coords, layer):
    if layer.crs().postgisSrid() == projection:
        return coords
    
    crsDest = QgsCoordinateReferenceSystem(projection)
    xform = QgsCoordinateTransform()
    xform.setSourceCrs(layer.crs())
    xform.setDestinationCrs(QgsCoordinateReferenceSystem(crsDest))
    if isinstance(coords, list):
        coords = reduceTo2dList(coords)
    newCoords = coords
    if isinstance(coords[0], list):
        coords = reduceTo2dList(coords)
        for i, point in enumerate(coords):
            pt = xform.transform(point[0], point[1])
            newCoords[i] = [pt.x(),pt.y()]
    elif str(type(coords).__name__) == "QgsPointXY":
        newCoords = xform.transform(coords)
    else:
        pt = xform.transform(coords[0], coords[1])
        newCoords[0] = [pt.x(),pt.y()]
    return (newCoords)


def reduceTo2dList(largeList):
    #Reduces any list to a 2d list, through the zeroth element in each. 
    if not isinstance(largeList, list):
        raise ValueError('List of Coordinates was not a list as expected')
    if isinstance(largeList[0][0], list):
        return reduceTo2dList(largeList[0])
    else:
        return largeList

def debugMsg(message):
    #Puts text in the logs.
    QgsMessageLog.logMessage(str(message), tag="GeoAtlas", level = Qgis.Info)

"""https://data.geo.dk/api/v3/MapLegend?geoareaid=1&name=slice-kote&modelid=30&bbox=722482.0000000001,6174676.000000001,724221.2000000001,6175978.400000001&kote=-10"""

class GeoBoundingBox:
        def __init__(self, min_x, min_y, max_x, max_y):
                self.min_x = min_x
                self.min_y = min_y              
                self.max_x = max_x
                self.max_y = max_y

        def contains_point(self, x, y):
                return (x > self.min_x and x < self.max_x and y > self.min_y and y < self.max_y)

        def to_string(self):
            return (str(self.min_x) + ',' + str(self.min_y) + ',' + str(self.max_x) + ',' + str(self.max_y))

class GeoPoint:
        def __init__(self, x, y):
                self.x = x
                self.y = y

        def to_string(self):
            return (str(self.x) + ',' + str(self.y))

SAVEDMODELS = None

def getModelsFromCoordList(coordinates, apikey):
    # Later on using WFS models might be useful, as it allows for greater accuracy 
    global SAVEDMODELS
    if SAVEDMODELS is None:
        SAVEDMODELS = requests.get("https://data.geo.dk/api/v3/geomodel?geoareaid=1", headers={'authorization': apikey}).json()
    models = []
    #Request the models for each point
    for model in SAVEDMODELS:
        bboxdict = model['BoundingBox']
        bbox = GeoBoundingBox(bboxdict["MinX"], bboxdict["MinY"], bboxdict["MaxX"], bboxdict["MaxY"])
        insidemodel = False
        for coord in coordinates:
            if bbox.contains_point(coord[0], coord[1]):
                insidemodel = True
        if insidemodel:
            models.append(model)
    if len(models) == 0:
        debugMsg(("No models for this area: ", coordinates))
    return models
    #If there is no models in the lists, then we couldnt find any.

def get_models_for_bounding_box(bbox, apikey):
    url = "https://data.geo.dk/api/v3/geomodel?geoareaid=1&bbox=" + bbox.to_string()
    message = requests.get(url , headers={'authorization': apikey})
    return message.json()

def get_models_for_point(point, elemdict, apikey):
    url = "https://data.geo.dk/api/v3/geomodel?geoareaid=1&x=" + str(point[0]) + "&y=" + str(point[1])
    models = requests.get(url, headers={'authorization': apikey}).json()

    for model in models[:]: #Construct a polygon of each model, and see if the point is within this polygon
        elem = elemdict[str(model['ID'])]
        for e in elem:
            contained = False
            l = []
            v = e.split(';')
            for elem in v:
                x = elem.split(',')
                p = (float(x[0]), float(x[1]))
                l.append(p)
            line = geometry.LineString(l)
            geometryPoint = geometry.Point(float(point[0]), float(point[1]))
            polygon = geometry.Polygon(line)
            contained = polygon.contains(geometryPoint)
            if contained:
                break
        if not contained:
            models.remove(model)
    if len(models) == 0:
        debugMsg(("No models for this area: ", point))
    return models

def getBoundingBox(coordinates):
    minX = coordinates[0][0]
    maxX = coordinates[0][0]
    minY = coordinates[0][1]
    maxY = coordinates[0][1]
    for coord in coordinates:
        minX = min(minX, coord[0])
        minY = min(minY, coord[1])
        maxX = max(maxX, coord[0])
        maxY = max(maxY, coord[1])
    return minX, minY, maxX, maxY


#Quick maths
def getDistanceOfLine(coords):
    return sqrt((coords[-1][1]-coords[0][1])**2+(coords[-1][0]-coords[0][0])**2)

def getRotationOfLine(coords):
    return atan((coords[-1][1]-coords[0][1])/(coords[-1][0]-coords[0][0])) * 180 / pi

def layerIsVector(layer):
    if layer.type() == QgsVectorLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.LineGeometry:
        return True
    return False
    