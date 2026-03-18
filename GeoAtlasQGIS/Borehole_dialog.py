import ast
import os
import re
from urllib.parse import quote

from PyQt5 import uic
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt


EMPTY_HTML = "<html><body></body></html>"
BOREHOLE_DISPLAY_SCALE = 0.85
BOREHOLE_SOURCE_WIDTH = 170
BOREHOLE_SOURCE_HEIGHT = 500
BOREHOLE_DISPLAY_WIDTH = int(round(BOREHOLE_SOURCE_WIDTH * BOREHOLE_DISPLAY_SCALE))
BOREHOLE_DISPLAY_HEIGHT = int(round(BOREHOLE_SOURCE_HEIGHT * BOREHOLE_DISPLAY_SCALE))
MIN_BOREHOLE_WIDTH = BOREHOLE_DISPLAY_WIDTH

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'forms/Borehole_dialog_base.ui'))


class BoreholeDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(BoreholeDialog, self).__init__(parent)
        self.setupUi(self)
        self.infoLabel.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.infoLabel.setOpenExternalLinks(True)
        self.infoLabel.linkActivated.connect(self._openExternalLink)
        self._webViewLinksConfigured = False
        self._configureWebView()

        self.currentSvgHtml = ""
        self.currentLegendHtml = ""

        self.clearSvg()
        self.clearLegend()

    def _openExternalLink(self, url):
        if not url:
            return

        if isinstance(url, QtCore.QUrl):
            qurl = url
        else:
            qurl = QtCore.QUrl.fromUserInput(str(url))

        if qurl.isValid():
            QtGui.QDesktopServices.openUrl(qurl)

    def _configureWebView(self):
        if not hasattr(self, "webView"):
            return

        page = self.webView.page() if hasattr(self.webView, "page") else None
        if page is not None and not self._webViewLinksConfigured:
            if hasattr(page, "setLinkDelegationPolicy") and hasattr(page, "DelegateAllLinks"):
                page.setLinkDelegationPolicy(page.DelegateAllLinks)

            if hasattr(page, "linkClicked"):
                page.linkClicked.connect(self._openExternalLink)
                self._webViewLinksConfigured = True
            elif hasattr(self.webView, "linkClicked"):
                self.webView.linkClicked.connect(self._openExternalLink)
                self._webViewLinksConfigured = True

        frame = page.mainFrame() if page is not None and hasattr(page, "mainFrame") else None
        if frame is None or not hasattr(frame, "setScrollBarPolicy"):
            return

        frame.setScrollBarPolicy(Qt.Horizontal, Qt.ScrollBarAlwaysOff)
        frame.setScrollBarPolicy(Qt.Vertical, Qt.ScrollBarAlwaysOff)

    def setStatus(self, text):
        self.statusLabel.setText(text or "")

    def setSelectionHandler(self, handler):
        self.selectorCombo.activated.connect(handler)

    def setCandidateBoreholes(self, candidates):
        candidates = candidates or []
        self.selectorCombo.blockSignals(True)
        self.selectorCombo.clear()

        for metadata in candidates:
            self.selectorCombo.addItem(self._makeCandidateLabel(metadata), metadata)

        self.selectorCombo.blockSignals(False)
        is_visible = len(candidates) > 1
        self.selectorCombo.setVisible(is_visible)

    def setSelectedCandidate(self, metadata):
        if not metadata:
            return

        target_id = metadata.get("BoreholeId")
        target_number = metadata.get("BoreholeNumber")
        self.selectorCombo.blockSignals(True)
        for index in range(self.selectorCombo.count()):
            item = self.selectorCombo.itemData(index)
            if not isinstance(item, dict):
                continue
            if item.get("BoreholeId") == target_id and item.get("BoreholeNumber") == target_number:
                self.selectorCombo.setCurrentIndex(index)
                break
        self.selectorCombo.blockSignals(False)

    def getSelectedCandidate(self):
        return self.selectorCombo.currentData()

    def setLegendData(self, legend_data, error_message=None):
        if error_message:
            self.currentLegendHtml = self._wrap_legend_body(self._escape_html(error_message))
            self._renderCombinedHtml()
            return

        legend_data = legend_data or {}
        layers = legend_data.get("Layers", []) or []
        has_sounding = bool(legend_data.get("HasSounding"))
        has_screens = bool(legend_data.get("HasScreens"))

        if len(layers) == 0 and not has_sounding and not has_screens:
            self.clearLegend()
            return

        parts = []
        if layers:
            sorted_layers = sorted(
                [layer for layer in layers if isinstance(layer, dict)],
                key=lambda layer: layer.get("ViewOrder", 0),
            )
            for layer in sorted_layers:
                description = self._escape_html(layer.get("Description", "Unnamed layer"))
                color = self._normalize_color(layer.get("Color"))
                symbol = self._escape_html(layer.get("Symbol", ""))
                line = f"<div>{self._layer_swatch_html(color)}{description}"
                if symbol:
                    line += f" <span style=\"color:{self._get_secondary_text_color()};\">({symbol})</span>"
                line += "</div>"
                parts.append(line)

        if has_sounding:
            parts.append(f"<div>{self._sounding_icon_html()}Groundwater sounding present</div>")
        if has_screens:
            parts.append(f"<div>{self._screen_icon_html()}Screen/filter present</div>")

        self.currentLegendHtml = self._wrap_legend_body("".join(parts))
        self._renderCombinedHtml()

    def clearLegend(self):
        self.currentLegendHtml = ""
        self._renderCombinedHtml()

    def setBoreholeInfo(self, metadata, details=None):
        if not metadata:
            self.infoLabel.clear()
            return

        details = details or {}
        info_rows = self._build_info_rows(metadata, details)
        self.infoLabel.setText(self._render_info_rows(info_rows))

    def loadSvg(self, svg_content):
        if not svg_content:
            self.clearSvg()
            return

        if isinstance(svg_content, bytes):
            svg_content = svg_content.decode("utf-8", errors="replace")

        self.currentSvgHtml = self._normalize_inline_svg(svg_content)
        self._renderCombinedHtml()

    def clearSvg(self):
        self.currentSvgHtml = ""
        self._renderCombinedHtml()

    def _makeCandidateLabel(self, metadata):
        number = metadata.get("BoreholeNumber")
        borehole_id = metadata.get("BoreholeId")

        if number not in (None, "") and borehole_id not in (None, ""):
            return f"{number} (Id {borehole_id})"
        if borehole_id not in (None, ""):
            return f"Id {borehole_id}"
        if number not in (None, ""):
            return str(number)
        return "Unknown borehole"

    def _normalize_color(self, color):
        if isinstance(color, str) and len(color.strip()) == 7 and color.strip().startswith("#"):
            return color.strip()
        return "#cccccc"

    def _escape_html(self, value):
        if value is None:
            return ""
        text = str(value)
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def _clean_api_text(self, value):
        if value in (None, ""):
            return None
        text = str(value).strip()
        text = re.sub(r"\s+\[[A-Za-z]{2}\]$", "", text)
        return self._escape_html(text)

    def _format_link_or_text(self, text, href):
        safe_text = self._escape_html(text)
        resolved_href = self._extract_first_link(href)
        if resolved_href in (None, ""):
            return safe_text
        return f"<a href=\"{self._escape_html(resolved_href)}\">{safe_text}</a>"

    def _format_dgu_number_link(self, dgu_number):
        if dgu_number in (None, ""):
            return None

        dgu_text = str(dgu_number).strip()
        if dgu_text == "":
            return None

        dgu_href = "https://data.geus.dk/JupiterWWW/borerapport.jsp?dgunr=" + quote(dgu_text)
        return f"<a href=\"{self._escape_html(dgu_href)}\">{self._escape_html(dgu_text)}</a>"

    def _extract_first_link(self, value):
        if value in (None, ""):
            return None

        if isinstance(value, dict):
            for key in ("Link", "Href", "Url", "URL"):
                if key in value:
                    return self._extract_first_link(value.get(key))
            return None

        if isinstance(value, (list, tuple)):
            for item in value:
                resolved = self._extract_first_link(item)
                if resolved not in (None, ""):
                    return resolved
            return None

        if not isinstance(value, str):
            return None

        text = value.strip()
        if text == "":
            return None

        if text.startswith("[") or text.startswith("{"):
            # Some link fields come back as a stringified list/dict instead of real JSON.
            try:
                parsed = ast.literal_eval(text)
            except (ValueError, SyntaxError):
                parsed = None
            if parsed is not None:
                return self._extract_first_link(parsed)

        if "://" not in text:
            return None

        return text.replace("\\", "/")

    def _format_date(self, value):
        if value in (None, ""):
            return None
        text = str(value)
        if "T" in text:
            text = text.split("T", 1)[0]
        return self._escape_html(text)

    def _format_measurement(self, value, unit="", decimals=2):
        if value in (None, ""):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return self._escape_html(value)

        if abs(number - round(number)) < 1e-9:
            formatted = str(int(round(number)))
        else:
            formatted = f"{number:.{decimals}f}"

        if unit:
            formatted += f" {unit}"
        return self._escape_html(formatted)

    def _format_coordinate(self, coordinate, coordinate_system):
        if not isinstance(coordinate, dict):
            return None

        x_value = coordinate.get("X")
        y_value = coordinate.get("Y")
        if x_value in (None, "") or y_value in (None, ""):
            return None

        try:
            x_text = f"{float(x_value):.2f}"
            y_text = f"{float(y_value):.2f}"
        except (TypeError, ValueError):
            x_text = str(x_value)
            y_text = str(y_value)

        coord_text = f"{x_text}, {y_text}"
        if coordinate_system not in (None, ""):
            coord_text += f" ({coordinate_system})"
        return self._escape_html(coord_text)

    def _render_info_rows(self, rows):
        html_lines = []
        for label, value in rows:
            if value in (None, ""):
                continue
            html_lines.append(
                f"<div><span style=\"font-weight:600;\">{self._escape_html(label)}:</span> {value}</div>"
            )
        return "".join(html_lines)

    def _format_borehole_elevation(self, details):
        level_value = details.get("Level")
        if level_value in (None, ""):
            return None

        elevation = self._format_measurement(level_value, "m")
        vertical_ref = details.get("VerticalRefSystem")
        if vertical_ref not in (None, ""):
            elevation += f" ({self._escape_html(vertical_ref)})"
        return elevation

    def _build_primary_info_rows(self, metadata, details):
        point_value = details.get("Point") or details.get("BoreholeNumber") or metadata.get("BoreholeNumber")
        point_link = details.get("GeoArchiveBoreholeUrl") or details.get("BoreholeLink")
        drill_depth = details.get("BoreholeDepthMeters")
        if drill_depth in (None, ""):
            drill_depth = details.get("Depth")

        return [
            ("Point", self._format_link_or_text(point_value, point_link) if point_value not in (None, "") else None),
            ("Project number", self._escape_html(details.get("ProjectNumber")) if details.get("ProjectNumber") not in (None, "") else None),
            ("DGU number", self._format_dgu_number_link(details.get("DGUNumber"))),
            ("Datasource", self._escape_html(details.get("GeoDataSource")) if details.get("GeoDataSource") not in (None, "") else None),
            ("Primary coordinate (x, y)", self._format_coordinate(details.get("OriginalCoordinate"), details.get("OriginalCoordinateSystem"))),
            ("Secondary coordinate (x, y)", self._format_coordinate(details.get("Coordinate"), details.get("LocalCoordinateSystem"))),
            ("Borehole elevation", self._format_borehole_elevation(details)),
            ("Drill depth", self._format_measurement(drill_depth, "m", decimals=0)),
            ("Borehole method", self._clean_api_text(details.get("Method"))),
            ("Borehole purpose", self._clean_api_text(details.get("Purpose"))),
            ("Drill date", self._format_date(details.get("Date"))),
        ]

    def _build_fallback_info_rows(self, metadata):
        rows = []
        number = metadata.get("BoreholeNumber")
        borehole_id = metadata.get("BoreholeId")
        distance = metadata.get("DistanceToBorehole")
        datasource_id = metadata.get("DatasourceId")
        x_coord = metadata.get("X")
        y_coord = metadata.get("Y")
        epsg = metadata.get("Epsg")

        if number not in (None, ""):
            rows.append(("Borehole", self._escape_html(number)))
        if borehole_id not in (None, ""):
            rows.append(("Id", self._escape_html(borehole_id)))
        if distance not in (None, ""):
            try:
                rows.append(("Distance", self._escape_html(f"{float(distance):.1f} m")))
            except (TypeError, ValueError):
                rows.append(("Distance", self._escape_html(distance)))
        if datasource_id not in (None, ""):
            rows.append(("DatasourceId", self._escape_html(datasource_id)))
        if x_coord not in (None, "") and y_coord not in (None, ""):
            coord_text = f"{x_coord}, {y_coord}"
            if epsg not in (None, ""):
                coord_text += f" (EPSG:{epsg})"
            rows.append(("Coordinates", self._escape_html(coord_text)))

        return rows

    def _build_info_rows(self, metadata, details):
        rows = self._build_primary_info_rows(metadata, details)
        if all(value in (None, "") for _, value in rows):
            return self._build_fallback_info_rows(metadata)
        return rows

    def _wrap_svg(self, svg_text):
        return (
            f"<div class=\"borehole-panel\" style=\"width:{BOREHOLE_DISPLAY_WIDTH}px;height:{BOREHOLE_DISPLAY_HEIGHT}px;min-width:{MIN_BOREHOLE_WIDTH}px;\">"
            f"{svg_text}"
            "</div>"
        )

    def _layer_swatch_html(self, color):
        return (
            f"<span style=\"display:inline-block;width:12px;height:12px;"
            f"margin-right:6px;border:1px solid {self._get_border_color()};background:{color};\"></span>"
        )

    def _sounding_icon_html(self):
        return (
            "<svg width=\"14\" height=\"12\" viewBox=\"0 0 14 12\" "
            "style=\"display:inline-block;vertical-align:middle;margin-right:6px;overflow:visible;\">"
            f"<path d=\"M1 6 L11 1 L11 11 Z\" fill=\"#1E90FF\" stroke=\"{self._get_text_color()}\" stroke-width=\"0.7\"/>"
            "</svg>"
        )

    def _screen_icon_html(self):
        text_color = self._get_text_color()
        return (
            "<svg width=\"14\" height=\"12\" viewBox=\"0 0 14 12\" "
            "style=\"display:inline-block;vertical-align:middle;margin-right:6px;overflow:visible;\">"
            f"<rect x=\"5\" y=\"1\" width=\"4\" height=\"10\" fill=\"{text_color}\" stroke=\"{text_color}\" stroke-width=\"0.7\"/>"
            "</svg>"
        )

    def _wrap_legend_body(self, html_text):
        return (
            "<div style=\"min-width:220px;max-width:280px;font-family:Segoe UI, Arial, sans-serif;"
            f"font-size:12px;color:{self._get_text_color()};background:{self._get_background_color()};\">"
            f"{html_text}"
            "</div>"
        )

    def _get_palette_color(self, role, fallback):
        color = self.palette().color(role)
        if color.isValid():
            return color.name()
        return fallback

    def _get_background_color(self):
        return self._get_palette_color(QtGui.QPalette.Window, "#ffffff")

    def _get_text_color(self):
        return self._get_palette_color(QtGui.QPalette.WindowText, "#222222")

    def _get_secondary_text_color(self):
        return self._get_palette_color(QtGui.QPalette.Mid, "#666666")

    def _get_border_color(self):
        return self._get_palette_color(QtGui.QPalette.Mid, "#444444")

    def _normalize_inline_svg(self, svg_text):
        if not svg_text:
            return ""

        def replace_use_href(match):
            href_value = match.group(1)
            return f"xlink:href='{href_value}' href='{href_value}'"

        # QWebView is happier when inline SVG <use> tags carry both href forms.
        return re.sub(
            r"(?<!xlink:)href='([^']+)'",
            replace_use_href,
            svg_text,
        )

    def _renderCombinedHtml(self):
        if not self.currentSvgHtml and not self.currentLegendHtml:
            self.webView.setHtml(EMPTY_HTML)
            self._configureWebView()
            return

        legend_html = self.currentLegendHtml
        if legend_html:
            legend_html = f"<div class=\"legend-panel\" style=\"order:2;margin-left:12px;\">{legend_html}</div>"

        svg_html = f"<div style=\"order:1;\">{self._wrap_svg(self.currentSvgHtml)}</div>"

        html = (
            "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
            "<style>"
            "html, body { height: 100%; }"
            "body { margin: 0; padding: 0; overflow: hidden; }"
            ".layout-root { display: flex; align-items: flex-start; height: 100%; }"
            ".layout-root > div { min-height: 0; }"
            # Fix the profile size so dock resizing does not stretch the borehole itself.
            ".borehole-panel { position: relative; display: block; flex: 0 0 auto; box-sizing: border-box; overflow: hidden; }"
            f".borehole-panel > svg {{ position: absolute; left: 0; top: 0; display: block; width: {BOREHOLE_SOURCE_WIDTH}px !important; height: {BOREHOLE_SOURCE_HEIGHT}px !important; max-width: none !important; max-height: none !important; transform: scale({BOREHOLE_DISPLAY_SCALE}) !important; transform-origin: top left !important; }}"
            ".legend-panel { align-self: stretch; overflow: auto; }"
            "</style>"
            "</head>"
            f"<body style=\"background:{self._get_background_color()};color:{self._get_text_color()};\">"
            "<div class=\"layout-root\">"
            f"{legend_html}"
            f"{svg_html}"
            "</div>"
            "</body></html>"
        )
        self.webView.setHtml(html)
        self._configureWebView()
