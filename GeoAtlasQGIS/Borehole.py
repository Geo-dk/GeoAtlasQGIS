"""Borehole map tool for QGIS.

Clicks on the map, looks for boreholes at that spot, fetches the borehole
profile/legend from GeoAtlas, and updates the dock with the result.

Flow:
1. Read the click position and convert it to the API CRS.
2. Use GetWithinGeom to find boreholes inside a small click tolerance.
3. Pick the clicked borehole, then fetch its profile SVG and legend.
4. Update the marker and refresh the dock contents.
"""

import os
import requests

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDockWidget
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsTask,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsMapToolEmitPoint

from .Borehole_dialog import BoreholeDialog
from .utils import add_layer_to_group


GEOAREA_ID = 1
TARGET_EPSG = 25832
REQUEST_TIMEOUT_SECONDS = 15
DEFAULT_BOREHOLE_SVG_ID = "nearestBorehole"
DEFAULT_BOREHOLE_WIDTH = 170
DEFAULT_BOREHOLE_HEIGHT = 500
DEFAULT_BOREHOLE_LANG = "en"
DEFAULT_CLICK_TOLERANCE_PIXELS = 8
DEFAULT_CLICK_TOLERANCE_METERS = 5
MAX_COLOCATED_CANDIDATES = 5


def layerIsPoint(layer):
    return (
        layer is not None
        and layer.type() == QgsVectorLayer.VectorLayer
        and layer.geometryType() == QgsWkbTypes.PointGeometry
    )


class BoreholeTool():
    def __init__(self, iface, apiKeyGetter, usersettings):
        self.iface = iface
        self.apiKeyGetter = apiKeyGetter
        self.usersettings = usersettings
        self.dlg = None
        self.dock = None
        self.dock_added = False
        self.pointTool = None
        self.workinglayer = None
        self.dirpath = os.path.dirname(os.path.realpath(__file__))
        self.DEFAULTLAYERNAME = "GAL - Borehole"
        self.boreholeTask = None
        self.currentCandidateGroup = []
        self.currentBoreholeMetadata = None

    def display_point(self, pointToolCoordinates):
        self.iface.mapCanvas().unsetMapTool(self.pointTool)
        coords = self.transformToCorrectCRS(pointToolCoordinates)
        click_tolerance = self.getClickToleranceMeters(pointToolCoordinates)
        self.getBorehole(coords, click_tolerance)

    def makeCoordinateTransform(self, crs=TARGET_EPSG):
        xform = QgsCoordinateTransform()
        xform.setSourceCrs(self.iface.mapCanvas().mapSettings().destinationCrs())
        xform.setDestinationCrs(QgsCoordinateReferenceSystem.fromEpsgId(crs))
        return xform

    def transformToCorrectCRS(self, coords, crs=TARGET_EPSG):
        xform = self.makeCoordinateTransform(crs)
        x = coords.x()
        y = coords.y()
        transformed = xform.transform(x, y)
        return [transformed.x(), transformed.y()]

    def getClickToleranceMeters(self, coords, pixels=DEFAULT_CLICK_TOLERANCE_PIXELS):
        map_units_per_pixel = self.iface.mapCanvas().mapUnitsPerPixel()
        if map_units_per_pixel in (None, 0):
            return DEFAULT_CLICK_TOLERANCE_METERS
        tolerance = map_units_per_pixel * pixels
        if tolerance <= 0:
            return DEFAULT_CLICK_TOLERANCE_METERS
        return tolerance

    def resetDialogState(self, status_text):
        if self.dlg is None:
            return

        self.dlg.setStatus(status_text)
        self.dlg.setBoreholeInfo(None)
        self.dlg.setCandidateBoreholes([])
        self.dlg.clearLegend()
        self.dlg.clearSvg()

    def showError(self, message):
        self.clearMarker()
        self.resetDialogState(message)
        self.iface.messageBar().pushMessage("Warning:", message, level=Qgis.Warning, duration=5)

    def buildStatusMessage(self, metadata, source, candidate_group):
        borehole_number = metadata.get("BoreholeNumber", "Unknown")
        distance = metadata.get("DistanceToBorehole")
        status_prefix = "Loaded clicked borehole" if source == "clicked" else "Loaded borehole"
        status = f"{status_prefix}: {borehole_number}"

        if distance not in (None, ""):
            try:
                status += f" ({float(distance):.1f} m away)"
            except (TypeError, ValueError):
                status += f" ({distance} away)"

        if len(candidate_group) > 1:
            status += f" | {len(candidate_group)} boreholes share this location"

        return status

    def getBorehole(self, coords, buffer_distance):
        api_key = self.apiKeyGetter.getApiKey()
        if api_key is None:
            return

        if self.dlg is None:
            self.makeUi()

        self.ensureLayer()
        self.clearMarker()
        self.showUi()
        self.currentCandidateGroup = []
        self.currentBoreholeMetadata = None
        self.resetDialogState("Checking for a borehole at the clicked location...")

        self.boreholeTask = QgsTask.fromFunction(
            "Load clicked borehole",
            self.fetchBorehole,
            coords[0],
            coords[1],
            buffer_distance,
            api_key,
            on_finished=self.boreholecallback,
        )
        QgsApplication.taskManager().addTask(self.boreholeTask)

    def boreholecallback(self, exception, payload):
        if self.dlg is None:
            return

        if exception is not None:
            self.showError(str(exception))
            return

        if not isinstance(payload, dict):
            self.showError("Unexpected borehole response.")
            return

        if payload.get("error"):
            self.showError(payload["error"])
            return

        metadata = payload.get("metadata", {})
        details_data = payload.get("details")
        svg_content = payload.get("svg")
        legend_data = payload.get("legend")
        legend_error = payload.get("legend_error")
        borehole_x = metadata.get("X")
        borehole_y = metadata.get("Y")
        candidate_group = payload.get("candidate_group", [])
        source = payload.get("source", "clicked")

        self.currentCandidateGroup = candidate_group
        self.currentBoreholeMetadata = metadata

        self.updateBoreholeMarker(borehole_x, borehole_y)
        self.dlg.setBoreholeInfo(metadata, details_data)
        self.dlg.setCandidateBoreholes(candidate_group)
        self.dlg.setSelectedCandidate(metadata)
        self.dlg.setLegendData(legend_data, legend_error)
        self.dlg.loadSvg(svg_content)
        self.dlg.setStatus(self.buildStatusMessage(metadata, source, candidate_group))

    def fetchBorehole(self, task, x, y, buffer_distance, apikey):
        base_url = self.usersettings.get_geo_base_url()
        headers = {"authorization": apikey}
        within_geom_url = f"{base_url}/api/v3/Borehole/GetWithinGeom"
        within_geom_params = {
            "geoAreaId": GEOAREA_ID,
            "geom": f"POINT({x} {y})",
            "srid": 25832,
            "buffer": buffer_distance,
            "lang": DEFAULT_BOREHOLE_LANG,
        }

        try:
            within_geom_response = requests.get(
                within_geom_url,
                headers=headers,
                params=within_geom_params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            return {"error": f"GetWithinGeom request failed: {exc}"}

        if within_geom_response.status_code != 200:
            return {
                "error": (
                    "GetWithinGeom failed with HTTP "
                    + str(within_geom_response.status_code)
                )
            }

        try:
            within_geom_payload = within_geom_response.json()
        except ValueError as exc:
            return {"error": f"Unable to parse GetWithinGeom response: {exc}"}

        if not isinstance(within_geom_payload, list) or len(within_geom_payload) == 0:
            return {"error": "No borehole at the clicked location. Click directly on a borehole."}

        sorted_candidates = self.getCandidatesFromWithinGeom(within_geom_payload, x, y)
        if len(sorted_candidates) == 0:
            return {"error": "No borehole at the clicked location. Click directly on a borehole."}

        candidate_group = self.getCandidateGroup(sorted_candidates[:MAX_COLOCATED_CANDIDATES])
        if len(candidate_group) == 0:
            return {"error": "No borehole at the clicked location. Click directly on a borehole."}

        metadata = candidate_group[0]
        result = self.requestBoreholeSvg(metadata, apikey)
        if result.get("error"):
            return result

        result["candidate_group"] = candidate_group
        result["source"] = "clicked"
        return result

    def fetchSelectedBorehole(self, task, metadata, apikey):
        result = self.requestBoreholeSvg(metadata, apikey)
        if result.get("error"):
            return result

        result["candidate_group"] = self.currentCandidateGroup
        result["source"] = "selected"
        return result

    def requestBoreholeSvg(self, metadata, apikey):
        base_url = self.usersettings.get_geo_base_url()
        headers = {"authorization": apikey}
        borehole_id = metadata.get("BoreholeId")
        borehole_number = metadata.get("BoreholeNumber")
        if borehole_number in (None, "") and borehole_id in (None, ""):
            return {"error": "Borehole response did not contain a borehole identifier."}

        borehole_url = f"{base_url}/api/v3/borehole"
        request_variants = []
        if borehole_id not in (None, ""):
            request_variants.append(("boreholeId", borehole_id))
        if borehole_number not in (None, ""):
            request_variants.append(("boreholeNo", borehole_number))

        last_error = None
        svg_content = None
        for parameter_name, parameter_value in request_variants:
            borehole_params = {
                "geoAreaId": GEOAREA_ID,
                "format": "image/svg+xml",
                "width": DEFAULT_BOREHOLE_WIDTH,
                "height": DEFAULT_BOREHOLE_HEIGHT,
                "lang": DEFAULT_BOREHOLE_LANG,
                "svgId": self.buildSvgId(parameter_name, parameter_value),
                parameter_name: parameter_value,
            }

            try:
                borehole_response = requests.get(
                    borehole_url,
                    headers=headers,
                    params=borehole_params,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
            except requests.RequestException as exc:
                last_error = f"Borehole request failed for {parameter_name}={parameter_value}: {exc}"
                continue

            if borehole_response.status_code != 200:
                last_error = (
                    f"Borehole profile request failed for {parameter_name}={parameter_value} "
                    f"with HTTP {borehole_response.status_code}"
                )
                continue

            if not borehole_response.content:
                last_error = f"Borehole profile response was empty for {parameter_name}={parameter_value}"
                continue

            content_type = (borehole_response.headers.get("Content-Type") or "").lower()
            svg_content = borehole_response.content
            if b"<svg" not in svg_content.lower():
                preview = borehole_response.text[:200].strip()
                last_error = (
                    f"Borehole profile did not return SVG for {parameter_name}={parameter_value}. "
                    + (f"Content-Type was '{content_type}'. " if content_type else "")
                    + (f"Response started with: {preview}" if preview else "")
                ).strip()
                svg_content = None
                continue

            break

        if svg_content is None:
            return {"error": last_error or "Unable to load borehole SVG."}

        details_payload = metadata.get("_details") if isinstance(metadata, dict) else None
        if not isinstance(details_payload, dict):
            details_payload = None
        details_payload = self.addGeoArchiveLink(details_payload, metadata)
        legend_payload, legend_error = self.requestBoreholeLegend(metadata, headers)

        return {
            "metadata": metadata,
            "details": details_payload,
            "svg": svg_content,
            "legend": legend_payload,
            "legend_error": legend_error,
        }

    def addGeoArchiveLink(self, details_payload, metadata):
        if not isinstance(details_payload, dict):
            return details_payload

        borehole_id = None
        if isinstance(metadata, dict):
            borehole_id = metadata.get("BoreholeId")
        if borehole_id in (None, ""):
            borehole_id = details_payload.get("Id") or details_payload.get("BoreholeId")
        if borehole_id in (None, ""):
            return details_payload

        details_with_links = dict(details_payload)
        details_with_links["GeoArchiveBoreholeUrl"] = self.buildGeoArchiveBoreholeUrl(borehole_id)
        return details_with_links

    def buildSvgId(self, parameter_name, parameter_value):
        safe_value = str(parameter_value)
        safe_value = "".join(char if char.isalnum() else "_" for char in safe_value)
        return f"{DEFAULT_BOREHOLE_SVG_ID}_{parameter_name}_{safe_value}"

    def buildGeoArchiveBoreholeUrl(self, borehole_id):
        base_url = self.usersettings.get_geo_base_url().rstrip("/")
        return f"{base_url}/geoarchive/boreholes/{borehole_id}"

    def requestBoreholeLegend(self, metadata, headers):
        base_url = self.usersettings.get_geo_base_url()
        borehole_id = metadata.get("BoreholeId")
        borehole_number = metadata.get("BoreholeNumber")
        if borehole_number in (None, "") and borehole_id in (None, ""):
            return None, "Legend unavailable: no borehole identifier."

        legend_url = f"{base_url}/api/v3/Borehole/GetLegend"
        legend_params = {
            "geoAreaId": GEOAREA_ID,
            "lang": "en",
        }
        if borehole_id not in (None, ""):
            legend_params["boreholeId"] = borehole_id
        else:
            legend_params["boreholeNo"] = borehole_number

        try:
            legend_response = requests.get(
                legend_url,
                headers=headers,
                params=legend_params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            return None, f"Legend unavailable: {exc}"

        if legend_response.status_code != 200:
            error_message = f"Legend unavailable (HTTP {legend_response.status_code})."
            return None, error_message

        try:
            return legend_response.json(), None
        except ValueError as exc:
            return None, f"Legend unavailable: invalid JSON ({exc})"

    def getCandidatesFromWithinGeom(self, details_payload, click_x, click_y):
        candidates = []
        for details in details_payload:
            if not isinstance(details, dict):
                continue

            metadata = self.buildCandidateMetadata(details, click_x, click_y)
            if metadata is not None:
                candidates.append(metadata)

        candidates.sort(key=lambda item: item.get("DistanceToBorehole", float("inf")))
        return candidates

    def buildCandidateMetadata(self, details, click_x, click_y):
        coordinate = self.getPreferredCoordinate(details)
        if not isinstance(coordinate, dict):
            return None

        x_coord = coordinate.get("X")
        y_coord = coordinate.get("Y")
        srid = coordinate.get("SRID")
        if x_coord in (None, "") or y_coord in (None, ""):
            return None

        try:
            x_value = float(x_coord)
            y_value = float(y_coord)
        except (TypeError, ValueError):
            return None

        distance = ((x_value - click_x) ** 2 + (y_value - click_y) ** 2) ** 0.5
        borehole_id = details.get("Id") if details.get("Id") not in (None, "") else details.get("BoreholeId")
        borehole_number = (
            details.get("BoreholeNumber")
            or details.get("Point")
            or details.get("DGUNumber")
        )

        return {
            "BoreholeId": borehole_id,
            "BoreholeNumber": borehole_number,
            "X": x_value,
            "Y": y_value,
            "Epsg": srid,
            "DistanceToBorehole": distance,
            "_details": details,
        }

    def getPreferredCoordinate(self, details):
        for key in ("Coordinate", "OriginalCoordinate", "LocalCoordinate", "GlobalCoordinate"):
            coordinate = details.get(key)
            if isinstance(coordinate, dict) and coordinate.get("X") not in (None, "") and coordinate.get("Y") not in (None, ""):
                return coordinate
        return None

    def getCandidateGroup(self, candidates):
        if not candidates:
            return []

        first_key = self.getCoordinateKey(candidates[0])
        group = []
        for metadata in candidates:
            if self.getCoordinateKey(metadata) == first_key:
                group.append(metadata)
        return group

    def getCoordinateKey(self, metadata):
        try:
            return (
                round(float(metadata.get("X")), 3),
                round(float(metadata.get("Y")), 3),
            )
        except (TypeError, ValueError):
            return (metadata.get("X"), metadata.get("Y"))

    def makeLayer(self):
        self.workinglayer = QgsVectorLayer("Point?crs=epsg:25832", self.DEFAULTLAYERNAME, "memory")
        QgsProject.instance().addMapLayer(self.workinglayer, False)
        add_layer_to_group(self.workinglayer)

        style_path = os.path.join(self.dirpath, "styles", "dotstyle.qml")
        if os.path.exists(style_path):
            self.workinglayer.loadNamedStyle(style_path)

    def ensureLayer(self):
        if layerIsPoint(self.workinglayer):
            return

        layers = QgsProject.instance().mapLayersByName(self.DEFAULTLAYERNAME)
        if layers and layerIsPoint(layers[0]):
            self.workinglayer = layers[0]
        else:
            self.makeLayer()

    def clearMarker(self):
        if self.workinglayer is not None and self.workinglayer.dataProvider().featureCount() > 0:
            self.workinglayer.dataProvider().truncate()

    def updateBoreholeMarker(self, x, y):
        self.ensureLayer()
        self.clearMarker()

        if x in (None, "") or y in (None, ""):
            return

        feat = QgsFeature(self.workinglayer.fields())
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(float(x), float(y))))
        self.workinglayer.dataProvider().addFeatures([feat])
        self.workinglayer.triggerRepaint()

    def makeUi(self):
        self.dlg = BoreholeDialog()
        self.dlg.setSelectionHandler(self.selectedCandidateChanged)
        self.dock = QDockWidget("Borehole", self.iface.mainWindow())
        self.dock.setWidget(self.dlg)
        self.dock_added = False

    def showUi(self):
        if self.dock is None:
            return

        if not self.dock_added:
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
            self.dock_added = True
        else:
            self.dock.show()
            self.dock.raise_()

    def changeToBoreholeTool(self):
        if self.dlg is None:
            self.makeUi()

        self.dlg.setStatus("Click the map to open a borehole.")
        self.showUi()

        self.pointTool = QgsMapToolEmitPoint(self.iface.mapCanvas())
        self.pointTool.canvasClicked.connect(self.display_point)
        self.iface.mapCanvas().setMapTool(self.pointTool)

    def selectedCandidateChanged(self, index):
        if index < 0 or self.dlg is None:
            return

        metadata = self.dlg.getSelectedCandidate()
        if not isinstance(metadata, dict):
            return

        selected_id = metadata.get("BoreholeId")
        selected_number = metadata.get("BoreholeNumber")
        current_id = None
        current_number = None
        if isinstance(self.currentBoreholeMetadata, dict):
            current_id = self.currentBoreholeMetadata.get("BoreholeId")
            current_number = self.currentBoreholeMetadata.get("BoreholeNumber")

        if selected_id == current_id and selected_number == current_number:
            return

        api_key = self.apiKeyGetter.getApiKey()
        if api_key is None:
            return

        self.showUi()
        self.dlg.setStatus("Loading selected borehole...")
        details_payload = metadata.get("_details") if isinstance(metadata, dict) else None
        self.dlg.setBoreholeInfo(metadata, details_payload)
        self.dlg.clearLegend()
        self.dlg.clearSvg()

        self.boreholeTask = QgsTask.fromFunction(
            "Load selected colocated borehole",
            self.fetchSelectedBorehole,
            metadata,
            api_key,
            on_finished=self.selectedBoreholeCallback,
        )
        QgsApplication.taskManager().addTask(self.boreholeTask)

    def selectedBoreholeCallback(self, exception, payload):
        self.boreholecallback(exception, payload)
