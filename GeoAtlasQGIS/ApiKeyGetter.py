import requests
from datetime import datetime, timedelta
import urllib.parse
import json
import base64

from qgis.core import Qgis
from qgis.gui import QgsMessageBar
from .mysettings import *
from .utils import *

class ApiKeyGetter():
    def __init__(self, iface, settings):
        self.iface = iface
        self.settings = settings
        self.apiKey = None
        self.username = self.settings.value('username')
        self.password = self.settings.value('password')
        self.role = self.settings.value('role')
        self.time_last_key = None

    def settingsHasChanged(self):
        changed = False
        if self.settings.value('username') != self.username:
            changed = True
            self.username = self.settings.value('username')
        if self.settings.value('password') != self.password:
            changed = True
            self.password = self.settings.value('password')
        if self.settings.value('role') != self.role:
            changed = True
            self.role = self.settings.value('role')
        return changed
        

    def getApiKey(self):
        if self.should_get_new_key():
            if self.settings.is_set():
                s = "https://data.geo.dk/token?username=" + urllib.parse.quote(self.username)
                s += "&password=" + urllib.parse.quote(self.password)
                s += "&role=" + urllib.parse.quote(self.role)
                debugMsg("Getting new API Key from GAL api with url: " + s)
                r = requests.get(s)
                if r.text:
                    keyNoQuote = r.text.replace('\"','')
                    tempkey = keyNoQuote.split('.')[1]
                    while len(tempkey) % 4 != 0:
                        tempkey += '='
                    decoded = base64.urlsafe_b64decode(tempkey).decode('utf-8')
                    js = json.loads(decoded)
                    if js['GAL.GeoModels'] == '':
                        self.iface.messageBar().pushMessage("Error", "No models for specified Role. Is the role correct in settings?", level=Qgis.Warning, duration=10)
                        return None
                    self.apiKey = "Bearer " + keyNoQuote #Remove quotes which surrounds the key.
                    self.time_last_key = datetime.now()
                    return self.apiKey
                else:
                    self.iface.messageBar().pushMessage("Error", "User/Password/Role is wrong. Goto menu Settings>Options>GeoAtlas", level=Qgis.Warning, duration=10)
                    return None
            else:
                if not self.settings.value('role') or not self.settings.value('password') or not self.settings.value('username'):
                    self.iface.messageBar().pushMessage("Error", "User/Password/Role is not set. Goto menu Settings>Options>GeoAtlas", level=Qgis.Warning, duration=10)
        else:
            return self.apiKey

    def printApiKey(self):
        debugMsg(self.apiKey)

    def getApiKeyNoBearer(self):
        apikey = self.getApiKey()
        if apikey is not None:
            return apikey[6:].strip()
        return None

    def should_get_new_key(self):
        if self.settingsHasChanged(): #If we changed the login. Should be the first check, since it updates the information if it is changed.
            debugMsg("Settings have changed, getting new API key.")
            return True
        if self.apiKey is None or len(self.apiKey) < 15: #If something went wrong or we didnt get a login
            debugMsg("API key is None or too short, getting new API key.")
            return True
        if self.time_last_key is None: #If the login is too old
            debugMsg("Time last key is None, getting new API key.")
            return True
        if self.time_last_key < datetime.now() - timedelta(hours=1):
            debugMsg("API key is older than 1 hour, getting new API key.")
            return True
        return False