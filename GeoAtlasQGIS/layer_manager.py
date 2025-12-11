from PyQt5.QtWidgets import QMenu
import requests
import urllib.parse
import xml.etree.ElementTree as ET
from qgis.core import QgsProject, QgsRasterLayer, QgsDataSourceUri

from .utils import debugMsg, add_layer_to_group

class LayerManager:
    def __init__(self, geo_qgis):
        self.geo_qgis = geo_qgis
        self._capabilities_cache = {}

    def buildLayerMenu(self, target_menu, layers, group_order):
        # boolean indicates whether the URL is "available" (unavailable is grayed out in menu, and labeled unavailable)
        # TODO: in the future these URLs and their auth status should be fetched from the GAL API
        # atm this requires manual extension and will not work with new layers.
        custom_urls = {
            '%geusurl%': ("https://data.geus.dk/geusmap/ows/25832.jsp?whoami=data@geo.dk", True),
            '%dafurl%': ("https://services.datafordeler.dk/", True),
            '%kfurl%': ("https://api.dataforsyningen.dk/", True),
            '%dkmiljoeportalurl%': ("https://arealeditering-dist-geo.miljoeportal.dk/", True),
            '%dkmiljoegisurl%': ("https://miljoegis.mim.dk/wms", True)
        }
        
        def is_layer_invalid(layername):
            if not layername:
                return True
            suffix = str(layername).split(':')[-1] if ':' in layername else layername
            invalid = suffix.lower() in ['[empty]', 'none', '']
            return invalid
        
        def count_layer_styles(layer):
            map_layer_styles = layer.get('MapLayerStyles', [])
            count = len(map_layer_styles) if map_layer_styles else 0
            style = layer.get('Style', '')
            if style:
                suffixed = str(style).strip().split(':')[-1] if ':' in style else style
                if suffixed.lower() not in ['none', '[empty]']:
                    count += 1
            return max(count, 1)
        
        def add_layer_menu_item(menu, layer):
            layername = (layer.get('LayerName', '') or '').strip()
            custom_url = layer.get('Url', None)
            url_is_available = True
            missing_auth_message = ""
            if custom_url:
                for key, (replacement_url, is_available) in custom_urls.items():
                    if key in custom_url:
                        custom_url = custom_url.replace(key, replacement_url)
                        if not is_available:
                            url_is_available = False
                            break
                
                url_is_available_auth, missing_auth_message, _ = self.check_auth_availability(custom_url)
                if not url_is_available_auth:
                    url_is_available = False
            
            if is_layer_invalid(layername) or not url_is_available:
                if not url_is_available:
                    debugMsg("Layer URL unavailable: '" + layer.get('Name', 'Unnamed Layer') + f"'{missing_auth_message}")
                #else:
                #    debugMsg("Layer name '" + layername + "' invalid for layer '" + layer.get('Name', 'Unnamed Layer') + "'. Marking as unavailable.")
                suffix = missing_auth_message or " - Utilgængelig i QGIS plugin!"
                action = menu.addAction(layer.get('Name', 'Unavngivet Lag') + suffix)
                action.setEnabled(False)
                return
            
            map_layer_styles = layer.get('MapLayerStyles', [])
            base_style = (layer.get('Style', '') or '').strip()
            has_valid_base_style = base_style and base_style.lower() not in ['none', '[empty]']
            
            if map_layer_styles:
                layer_name = layer.get('Name', 'Unavngivet Lag')
                count = len(map_layer_styles) + (1 if has_valid_base_style else 0)
                styleSubmenu = QMenu(f"{layer_name} ({count})", menu)
                
                if has_valid_base_style:
                    processed_style = base_style
                    styleSubmenu.addAction(layer_name, lambda t=layer_name, ln=layername, s=processed_style, url=custom_url: self.addLayer(t, ln, s, url))
                
                for style_entry in map_layer_styles:
                    style_title = style_entry.get('DisplayName', style_entry.get('Name', 'Unavngivet Stil'))
                    style_name = (style_entry.get('Name', '') or '').strip()
                    styleSubmenu.addAction(style_title, lambda t=style_title, ln=layername, s=style_name, url=custom_url: self.addLayer(t, ln, s, url))
                
                menu.addMenu(styleSubmenu)
            else:
                title = layer.get('Name', 'Unavngivet Lag')
                style = (layer.get('Style', '') or '').strip()
                action = menu.addAction(title, lambda t=title, ln=layername, s=style, url=custom_url: self.addLayer(t, ln, s, url))
                if custom_url and custom_url.startswith('%'):
                    action.setText(title + " - ⚠️Unfixed External Url⚠️")
                    action.setEnabled(False)
        
        layer_groups = {}
        for layer in layers:
            layer_group_id = layer.get('LayerGroup', 8)
            if layer_group_id not in layer_groups:
                layer_groups[layer_group_id] = []
            layer_groups[layer_group_id].append(layer)
        
        total_count = 0
        for group_id in group_order.keys():
            if group_id not in layer_groups:
                continue
            
            group_layers = layer_groups[group_id]
            group_name = group_order.get(group_id, str(group_id))
            
            subgroups = {}
            no_subgroup = []
            for layer in group_layers:
                group_name_attr = layer.get('GroupName')
                if group_name_attr:
                    subgroups.setdefault(group_name_attr, []).append(layer)
                else:
                    no_subgroup.append(layer)
            
            group_count = sum(count_layer_styles(l) for l in group_layers)
            total_count += group_count
            
            groupSubmenu = QMenu(f"{group_name} ({group_count})", target_menu)
            target_menu.addMenu(groupSubmenu)
            
            for layer in no_subgroup:
                add_layer_menu_item(groupSubmenu, layer)
            
            for subgroup_name, subgroup_layers in subgroups.items():
                subgroup_count = sum(count_layer_styles(l) for l in subgroup_layers)
                subgroupSubmenu = QMenu(f"{subgroup_name} ({subgroup_count})", groupSubmenu)
                groupSubmenu.addMenu(subgroupSubmenu)
                
                for layer in subgroup_layers:
                    add_layer_menu_item(subgroupSubmenu, layer)
        
        target_menu.setTitle(f"Add layers to map ({total_count})")

    def populateHydromodelsMenu(self, hydromodelsMenu):
        hydromodelsMenu.clear()
        hydromodelsMenu.setTitle('Add hydromodels to map')

        api_key = self.geo_qgis.apiKeyGetter.getApiKey()
        if api_key is None:
            action = hydromodelsMenu.addAction('Login required to load hydromodels')
            action.setEnabled(False)
            return
        
        base_url = self.geo_qgis.settings.get_geo_base_url()
        url = self._ensure_auth(f"{base_url}/mapv2/geo-hydromodels/wms")

        try:
            response = requests.get(
                f'{base_url}/api/v3/hydromodel?geoareaid=1',
                headers={'authorization': api_key},
                timeout=10
            )
        except requests.RequestException as exc:
            debugMsg(f"Failed to fetch hydromodels: {exc}")
            action = hydromodelsMenu.addAction('Unable to load hydromodel catalogue')
            action.setEnabled(False)
            return

        if response.status_code != 200:
            debugMsg("Failed to fetch hydromodels: " + str(response.status_code))
            action = hydromodelsMenu.addAction(f"Unable to load hydromodels (HTTP {response.status_code})")
            action.setEnabled(False)
            return

        try:
            payload = response.json()
        except ValueError as exc:
            debugMsg(f"Failed to parse hydromodel response: {exc}")
            action = hydromodelsMenu.addAction('Unable to parse hydromodel data')
            action.setEnabled(False)
            return

        models = payload

        grouped_entries = {}
        total_models = 0
        for model in models:
            if not isinstance(model, dict):
                continue
            group_name = (model.get('Name') or '').strip()
            if not group_name:
                group_name = 'Other hydromodels'
            long_name = (model.get('LongName') or '').strip()
            if not long_name:
                continue
            model_id = model.get('Id')
            if model_id in (None, ''):
                continue
            layer_names = []
            layer_index = 1
            while True:
                key = f'WMSLayerName{layer_index}'
                if key not in model:
                    break
                raw_name = (model.get(key) or '').strip()
                if not raw_name:
                    break
                normalized = self._normalize_layer_name(url, raw_name, silent=True) or raw_name
                if normalized and normalized not in layer_names:
                    layer_names.append(normalized)
                layer_index += 1
            if not layer_names:
                continue
            grouped_entries.setdefault(group_name, []).append((long_name, tuple(layer_names), model_id))
            total_models += 1

        if not grouped_entries:
            action = hydromodelsMenu.addAction('No hydromodel layers available')
            action.setEnabled(False)
            return

        hydromodelsMenu.setTitle(f"Add hydromodels to map ({total_models})")

        for group_name in sorted(grouped_entries.keys(), key=lambda name: name.lower()):
            group_items = grouped_entries[group_name]
            group_menu = hydromodelsMenu.addMenu(f"{group_name} ({len(group_items)})")
            for long_name, names, model_id in sorted(group_items, key=lambda item: item[0].lower()):
                group_menu.addAction(
                    long_name,
                    lambda ln=long_name, layernames=tuple(names), mid=model_id, wms_url=url: self.addHydromodelLayers(ln, list(layernames), wms_url, mid)
                )

    def addLayer(self, title, layername, style="", custom_url=None):
        if self.geo_qgis.apiKeyGetter.getApiKey() is None:
            return

        self.geo_qgis.model_manager.ensureElemDict()
        debugMsg(f"Adding layer: '{title}' | Layer: '{layername}' | Style: '{style}'")

        if ',' in layername:
            layer_names = [ln.strip() for ln in layername.split(',')]
            debugMsg(f"  Detected multiple layers: {layer_names}")
            styles = [s.strip() for s in style.split(',')] if style and ',' in style else [style] * len(layer_names)
            debugMsg(f"  Using styles: {styles}")
            
            root = QgsProject.instance().layerTreeRoot()
            gal_group = root.findGroup('GAL') or root.insertGroup(0, 'GAL')
            subgroup = gal_group.insertGroup(0, title)
            
            for layer_name, layer_style in zip(layer_names, styles):
                display_name = layer_name.split(':')[-1] if ':' in layer_name else layer_name
                uri = self.makeWmsUri(layer_name, layer_style, custom_url)
                debugMsg(f"    Adding sub-layer: '{display_name}' | Layer: '{layer_name}' | Style: '{layer_style}'")
                layer = QgsRasterLayer(uri, display_name, "wms")
                
                QgsProject.instance().addMapLayer(layer, False)
                layer_node = subgroup.addLayer(layer)
                if not layer.isValid():
                    error_msg = layer.dataProvider().error().message() if layer.dataProvider() else "No provider"
                    debugMsg(f"    Sub-layer '{display_name}' is not valid")
                    debugMsg(f"      Layer Name: {layer_name} | Style: {layer_style}")
                    debugMsg(f"      URI: {uri}")
                    if error_msg: 
                      debugMsg(f"      Provider Error: {error_msg}")
                    else: 
                      debugMsg("      No provider error message available")
                    debugMsg(f"      Check the network logger for more information.")
                    if layer_node:
                        layer_node.setItemVisibilityChecked(False)
                else:
                    debugMsg(f"      URI: {uri}")
                    debugMsg(f"    Sub-layer '{display_name}' added successfully")
                    layer.triggerRepaint()
        else:
            uri = self.makeWmsUri(layername, style, custom_url)
            layer = QgsRasterLayer(uri, title, "wms")
            
            QgsProject.instance().addMapLayer(layer, False)
            layer_node = add_layer_to_group(layer, 'GAL')
            if not layer.isValid():
                error_msg = layer.dataProvider().error().message() if layer.dataProvider() else "No provider"
                debugMsg(f"    Layer '{title}' is not valid")
                debugMsg(f"      Layer Name: {layername} | Style: {style}")
                debugMsg(f"      URI: {uri}")
                if error_msg: 
                  debugMsg(f"      Provider Error: {error_msg}")
                else: 
                  debugMsg("      No provider error message available")
                debugMsg(f"      Check the network logger for more information.")
                if layer_node:
                    layer_node.setItemVisibilityChecked(False)
            else:
                debugMsg(f"      URI: {uri}")
                debugMsg(f"Layer '{title}' added successfully")
                layer.triggerRepaint()

    def addHydromodelLayers(self, title, layer_names, custom_url, model_id):
        if self.geo_qgis.apiKeyGetter.getApiKey() is None:
            return

        layer_names = [ln for ln in (layer_names or []) if ln]
        if not layer_names:
            return

        self.geo_qgis.model_manager.ensureElemDict()
        debugMsg(f"Adding hydromodel: '{title}' | Layers: {layer_names} | ModelId: {model_id}'")

        comma_layers = ','.join(layer_names)
        self.addLayer(title, comma_layers, "", custom_url)

        root = QgsProject.instance().layerTreeRoot()
        subgroup = None
        gal_group = None
        if root:
            gal_group = root.findGroup('GAL')
            if gal_group:
                subgroup = gal_group.findGroup(title)

        parent_group = subgroup or gal_group
        # hydromodels always needs to have the corresponding points layer added
        points_param = f"ids:{model_id}"
        points_uri = self.makeWmsUri(
            'hydromodel-points',
            '',
            custom_url,
            extra_params={'viewparams': points_param}
        )
        points_display_name = 'hydromodel-points'
        debugMsg(f"    Adding hydromodel points layer with VIEWPARAMS '{points_param}'")
        points_layer = QgsRasterLayer(points_uri, points_display_name, "wms")

        QgsProject.instance().addMapLayer(points_layer, False)
        points_node = None
        if parent_group:
            points_node = parent_group.addLayer(points_layer)
        else:
            points_node = add_layer_to_group(points_layer, 'GAL')

        if not points_layer.isValid():
            error_msg = points_layer.dataProvider().error().message() if points_layer.dataProvider() else "No provider"
            debugMsg("    Hydromodel points layer is not valid")
            debugMsg(f"      URI: {points_uri}")
            if error_msg: 
                debugMsg(f"      Provider Error: {error_msg}")
            else: 
                debugMsg("      No provider error message available")
            debugMsg(f"      Check the network logger for more information.")
            if points_node:
                points_node.setItemVisibilityChecked(False)
        else:
            debugMsg(f"      URI: {points_uri}")
            debugMsg("    Hydromodel points layer added successfully")
            points_layer.triggerRepaint()

    def makeWmsUri(self, layername, style, custom_url=None, extra_params=None):
        layername = (layername or '').strip()
        style = (style or '').strip()
        extra_params = extra_params or {}

        def should_ignore_style(style_value):
            if not style_value:
                return True
            style_lower = style_value.lower()
            if ':' in style_lower:
                style_lower = style_lower.split(':', 1)[1]
            return style_lower in ['[empty]', 'none', '']

        if should_ignore_style(style):
            style = ''

        quri = QgsDataSourceUri()
        quri.setParam("IgnoreGetFeatureInfoUrl", '1')
        quri.setParam("IgnoreGetMapUrl", '1')
        quri.setParam("contextualWMSLegend", '0')
        quri.setParam("crs", 'EPSG:25832')
        quri.setParam("dpiMode", '7')
        quri.setParam("featureCount", '10')
        quri.setParam("format", 'image/png')
        quri.setParam("transparent", 'true')

        if custom_url:
            url = self._ensure_auth(custom_url)
        else:
            base_url = self.geo_qgis.settings.get_geo_base_url()
            default_url = f'{base_url}/mapv2/GEO-Services/wms?VERSION=1.3.0&CRS=EPSG%3A25832'
            url = self._ensure_auth(default_url)

        if extra_params:
            try:
                parsed_extra = urllib.parse.urlparse(url)
                query_items = urllib.parse.parse_qsl(parsed_extra.query, keep_blank_values=True)
                for key, value in extra_params.items():
                    if value in (None, ''):
                        continue
                    query_items = [item for item in query_items if item[0].lower() != str(key).lower()]
                    query_items.append((key, value))
                url = urllib.parse.urlunparse(parsed_extra._replace(query=urllib.parse.urlencode(query_items, doseq=True)))
            except ValueError:
                pass

        layername = self._normalize_layer_name(url, layername)
        style = self._normalize_layer_name(url, style) if style else ''

        quri.setParam("layers", layername)
        quri.setParam("styles", style)
        quri.setParam("url", url)
        return str(quri.encodedUri())[2:-1]

    def _ensure_auth(self, url):
        if not url:
            return url
        is_available, _, auth = self.check_auth_availability(url)
        if not is_available or not auth:
            return url
        
        parsed_url = urllib.parse.urlparse(url)
        query_items = urllib.parse.parse_qsl(parsed_url.query, keep_blank_values=True)
        for key, value in auth.items():
            if value in (None, ''):
                continue
            query_items = [item for item in query_items if item[0].lower() != key.lower()]
            query_items.append((key, value))
        if query_items:
            new_query = urllib.parse.urlencode(query_items, doseq=True)
            return urllib.parse.urlunparse(parsed_url._replace(query=new_query))
        return url

    def _normalize_layer_name(self, url, layername, silent=False):
        if not layername or not url:
            return layername

        try:
            parsed = urllib.parse.urlparse(url)
        except ValueError:
            return layername

        service_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
        query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)

        filtered_params = []
        has_service = False
        for key, value in query_pairs:
            if key.lower() == 'request':
                continue
            filtered_params.append((key, value))
            if key.lower() == 'service':
                has_service = True

        if not has_service:
            filtered_params.append(('SERVICE', 'WMS'))

        filtered_params.append(('REQUEST', 'GetCapabilities'))
        capability_query = urllib.parse.urlencode(filtered_params, doseq=True)
        capability_url = service_url
        if capability_query:
            capability_url = f"{service_url}?{capability_query}"

        available_names = self._get_capability_layer_names(capability_url)
        if not available_names:
            return layername

        target_lower = layername.lower()
        suffix_lower = target_lower.split(':', 1)[-1]

        for candidate in available_names:
            if candidate.lower() == target_lower:
                if not silent:
                    debugMsg(f"    Using capability layer name '{candidate}' for request '{layername}'")
                return candidate

        suffix_matches = []
        for candidate in available_names:
            candidate_suffix = candidate.split(':', 1)[-1]
            if candidate_suffix.lower() == suffix_lower:
                suffix_matches.append(candidate)

        if suffix_matches:
            if ':' in layername:
                original_prefix = layername.split(':', 1)[0].lower()
                for candidate in suffix_matches:
                    if ':' in candidate and candidate.split(':', 1)[0].lower() == original_prefix:
                        if not silent:
                            debugMsg(f"    Using capability layer name '{candidate}' for request '{layername}'")
                        return candidate
            suffix_matches.sort(key=len)
            chosen = suffix_matches[0]
            if not silent:
                debugMsg(f"    Using capability layer name '{chosen}' for request '{layername}'")
            return chosen

        return layername

    def _get_capability_layer_names(self, capability_url):
        cached = self._capabilities_cache.get(capability_url)
        if cached is not None:
            return cached

        try:
            response = requests.get(capability_url, timeout=10)
            response.raise_for_status()
        except requests.RequestException as exc:
            host = urllib.parse.urlparse(capability_url).netloc
            debugMsg(f"    Could not load capabilities from '{host}': {exc}")
            return []

        try:
            root = ET.fromstring(response.content)
        except ET.ParseError as exc:
            host = urllib.parse.urlparse(capability_url).netloc
            debugMsg(f"    Failed to parse capabilities from '{host}': {exc}")
            return []

        names = []
        for name_elem in root.findall('.//{*}Layer/{*}Name'):
            name_text = (name_elem.text or '').strip()
            if name_text:
                names.append(name_text)

        if names:
            host = urllib.parse.urlparse(capability_url).netloc
            debugMsg(f"    Discovered {len(names)} layer name(s) from '{host}' capabilities")

        self._capabilities_cache[capability_url] = names
        return names

    def refreshLayersMenu(self):
        debugMsg("Refreshing layer catalogue")
        if not hasattr(self.geo_qgis, 'layersMenu') or self.geo_qgis.layersMenu is None:
            debugMsg("  Layer menu handle unavailable; rebuilding full menu")
            self.geo_qgis.reloadMenu()
            return

        self.geo_qgis.layersMenu.clear()
        self.geo_qgis.layersMenu.setTitle('Add layers to map')
        self.populateLayersMenu(self.geo_qgis.layersMenu)

    def refreshHydromodelsMenu(self):
        debugMsg("Refreshing hydromodel catalogue")
        if not hasattr(self.geo_qgis, 'hydromodelsMenu') or self.geo_qgis.hydromodelsMenu is None:
            debugMsg("  Hydromodel menu handle unavailable; rebuilding full menu")
            self.geo_qgis.reloadMenu()
            return

        self.populateHydromodelsMenu(self.geo_qgis.hydromodelsMenu)

    def populateLayersMenu(self, layersMenu):
        # any layer with a group id not listed here will be skipped from the layer menu completely.
        # TODO: these should probrably also be acquired from the GAL API in the future.
        layer_group_order = {
            #0: 'Baggrundskort',
            1: 'DHM kort og kurver', 2: 'Boringer og geofysik',
            3: 'Danmarks undergrund', 4: 'Overfladenære og geotekniske kort', 5: 'Miljø',
            9: 'Terrænnært grundvand', 6: 'Vand', 10: 'Satellit', 7: 'Forvaltning',
            11: 'Andre baggrundskort', 8: 'Andre'
        }
        
        base_url = self.geo_qgis.settings.get_geo_base_url()
        configUrl = f'{base_url}/api/v3/user/config?geoAreaid=1'
        key = self.geo_qgis.apiKeyGetter.getApiKey()
        
        res = requests.get(configUrl, headers={'authorization': key})
        if res.status_code != 200:
            debugMsg("Failed to get config for layers menu: " + str(res.status_code))
            return
        
        res_json = res.json()
        layers = res_json.get('MapLayers', [])
        layers = [l for l in layers if l.get('Enabled', False)]
        
        self.buildLayerMenu(layersMenu, layers, layer_group_order)

    def check_auth_availability(self, url):
        if not url:
            return True, "", None
        try:
            parsed = urllib.parse.urlparse(url)
            host = parsed.netloc.lower()
            auth = None
            if 'geo.dk' in host:
                token = self.geo_qgis.apiKeyGetter.getApiKey()
                if not token:
                    return False, " - Missing 'GeoAtlas Live' API key", None
                auth = {"token": self.geo_qgis.apiKeyGetter.getApiKeyNoBearer()}
            elif 'dataforsyningen.dk' in host:
                token = self.geo_qgis.settings.value('dataforsyningen_token')
                if not token:
                    return False, " - Missing 'dataforsyningen' token in settings", None
                auth = {"token": token}
            elif 'datafordeler.dk' in host:
                username = self.geo_qgis.settings.value('datafordeler_username')
                password = self.geo_qgis.settings.value('datafordeler_password')
                if not username or not password:
                    return False, " - Missing 'datafordeler' credentials in settings", None
                auth = {"username": username, "password": password}
        except:
            pass
        return True, "", auth