from qgis.gui import *
from qgis.core import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from .utils import *
from .ApiKeyGetter import *
from .virtualBoring_dialog import *
from qgis.PyQt.QtXml import QDomDocument
import os 


class ReportTool():
    def __init__(self, iface, apiKeyGetter):
        self.iface = iface
        self.apiKeyGetter = apiKeyGetter

    def testReport(self):
        dir_path = os.path.dirname(os.path.realpath(__file__)) + "/standardlayout.qpt"
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
        self.composition.setName('console')
        project.layoutManager().addLayout(self.composition)
        self.composition = project.layoutManager().layoutByName('console')
        self.iface.openLayoutDesigner(self.composition)
        
        # maybe using QgsLayoutItem???
        # layoutItem = composition.itemById("1")
