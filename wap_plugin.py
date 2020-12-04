# -*- coding: utf-8 -*-
"""
/***************************************************************************
 WAPlugin
                                 A QGIS plugin
 Provides access to all the WaPOR data and includes it in the QGIS canvas as another raster layer, providing WaPOR data easy access to the QGIS users. Moreover, the water accounting and productivity component of the plugin will help the water management, providing the opportunity of calculating water accounting indicators, through the creation of maps and reports.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-12-01
        git sha              : $Format:%H$
        copyright            : (C) 2020 by WAP Team
        email                : waporteam17@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QDate, QTime, QDateTime, Qt
from qgis.PyQt.QtGui import QIcon 
from qgis.PyQt.QtWidgets import QAction, QApplication

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .wap_plugin_dialog import WAPluginDialog
import os.path

# from PyQt5.QtGui import *
import requests
import json
import wget
import os  

class WAPlugin:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'WAPlugin_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&WAPlugin')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

        # Path of the code Directory
        self.cwd = os.path.dirname(os.path.realpath(__file__))
        self.layer_folder_dir = os.path.join(self.cwd, "layers")

        # Default Values
        self.waterProductivityVar = "GBWP"
        self.resolutionVar = "100m"  #"250m" or "100m" , maybe "30m" works for some area
        self.startSeasonVar = "2015-01"  # "YYYY-DK" (Dekad)
        self.endSeasonVar = "2015-18"  # "YYYY-DK" (Dekad)

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('WAPlugin', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/wap_plugin/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Water Accounting and Productivity Plugin'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&WAPlugin'),
                action)
            self.iface.removeToolBarIcon(action)

    def wapor_connect(self):
        APIToken='1ba703cd638a4a473a62472d744fc3d3079e888494f9ca1ed492418a79e3f090eb1756e8284ef483'

        request_url='https://io.apps.fao.org/gismgr/api/v1/iam/sign-in/'
        request_headers = {'X-GISMGR-API-KEY': APIToken}

        resp = requests.post(
                        request_url,
                        headers=request_headers)

        print('Trying to access WaPOR Database . . .')

        resp_json = resp.json()
        if resp_json['message']=='OK':
            self.AccessToken=resp_json['response']['accessToken']
            print('SUCCESS: Access granted')
            print('Access expires in 3600s')
            self.dlg.downloadButton.setEnabled(True)

        else:
            print('Fail to get accessToken')

    def waterProductivityChange(self, i):
        if i is 0:
            print("Selected GBWP")
            self.waterProductivityVar = "GBWP"
        elif i is 1:
            print("Selected NBWP")
            self.waterProductivityVar = "NBWP"

    def resolutionListChange(self, i):
        if i is 0:
            print("Selected 30 Meters")
            self.resolutionVar = "30m"
        elif i is 1:
            print("Selected 100 Meters")
            self.resolutionVar = "100m"
        elif i is 2:
            print("Selected 200 Meters")
            self.resolutionVar = "200m"

    def onStartDateChanged(self, qDate):
        # print('{0}/{1}/{2}'.format(qDate.day(), qDate.month(), qDate.year()))
        self.startSeasonVar = str(qDate.year()) + "-" + str(qDate.day())
        print("Set Start Date: ", self.startSeasonVar)

    def onEndDateChanged(self, qDate):
        # print('{0}/{1}/{2}'.format(qDate.day(), qDate.month(), qDate.year()))
        self.endSeasonVar = str(qDate.year()) + "-" + str(qDate.day())
        print("Set End Date: ", self.endSeasonVar)

    def clickOK(self):
        self.dlg.connectLabel.setText ('OK detected')
        self.wapor_connect()

    def test(self):
        # print("Inside Test function")
        path = os.path.join(self.cwd, "json", "test.json") 
        testJsonFile = open(path,) 
        request_json = json.load(testJsonFile) 

        url=r'https://io.apps.fao.org/gismgr/api/v1/query/'

        # Update json with current settings
        # request_json["params"]["waterProductivity"] = self.waterProductivityVar
        # request_json["params"]["resolution"] = self.resolutionVar
        # request_json["params"]["startSeason"] = self.startSeasonVar
        # request_json["params"]["endSeason"] = self.endSeasonVar

        request_json = {
                        "type": "CustomWaterProductivity",
                        "params": {
                            "waterProductivity": "GBWP", #"GBWP" or "NBWP"
                            "resolution": "100m", #"250m" or "100m" , maybe "30m" works for some area
                            "startSeason": "2015-01", # "YYYY-DK" (Dekad)
                            "endSeason": "2015-18", # "YYYY-DK" (Dekad)
                            "shape": {
                            "type": "Polygon", #define coordinates of the area in geojson format
                            "coordinates": [
                                [
                                [
                                    37.20642480347329,
                                    9.879461495912246
                                ],
                                [
                                    36.49808605470977,
                                    7.56804031573655
                                ],
                                [
                                    37.84020157868276,
                                    5.219338148783827
                                ],
                                [
                                    40.0770607853044,
                                    5.293900122337882
                                ],
                                [
                                    41.97839111093279,
                                    7.232511434743303
                                ],
                                [
                                    41.68014321671657,
                                    8.313660051277097
                                ],
                                [
                                    39.89065585141926,
                                    7.605321302513577
                                ],
                                [
                                    38.5858213142233,
                                    7.344354395074386
                                ],
                                [
                                    38.51125934066925,
                                    8.649188932270341
                                ],
                                [
                                    37.20642480347329,
                                    9.879461495912246
                                ]
                                ]
                            ]
                            }
                        }
                        }

        request_headers = {
                    'Authorization': "Bearer " + self.AccessToken}

        response = requests.post(
                        url,
                        json=request_json,
                        headers=request_headers)
        response_json=response.json()
        print(response_json)

        if response_json['message']=='OK':
            job_url = response_json['response']['links'][0]['href']
        else:
            print('Fail to get job url')
            response = requests.get(
                                job_url)
            response.json()

        print('Waiting WaPOR')
        self.dlg.downloadButton.setEnabled(False)
        self.dlg.downloadLabel.setText ('Waiting WaPOR')
        while True:
            QApplication.processEvents()
            response = requests.get(job_url)
            response_json=response.json()
            if response_json['response']['status']=='COMPLETED':
                gbwp = response_json['response']['output']['bwpDownloadUrl']
                tbp = response_json['response']['output']['tbpDownloadUrl']
                aeti = response_json['response']['output']['wtrDownloadUrl']
                self.dlg.downloadLabel.setText ('Url in memory')
                break
                
        print('Link to download GBWP',gbwp)
        print('Link to download TBP',tbp)
        print('Link to download AETI',aeti)
        url= aeti
        file_name = url.rsplit('/', 1)[1]
        url_dir = os.path.join(self.cwd, "layers", file_name)
        wget.download(url, url_dir)
        while True:
            QApplication.processEvents()
            if os.path.isfile(file_name):
                self.dlg.downloadLabel.setText ('File in memory')
        self.dlg.downloadButton.setEnabled(True)
        
    
    def load(self):
        layer_dir = os.path.join(self.cwd, "layers", "L2_GBWP_1501-1518.tif")
        rlayer = self.iface.addRasterLayer(layer_dir, "layer name you like")
        if not rlayer:
            print("Layer failed to load!")

    def run(self):
        """Run method that performs all the real work"""
        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = WAPluginDialog()

            self.dlg.downloadButton.setEnabled(False)

            self.dlg.connectButton.clicked.connect(self.clickOK)
            self.dlg.downloadButton.clicked.connect(self.test)
            self.dlg.loadButton.clicked.connect(self.load)
            self.dlg.waterProductivity.currentIndexChanged.connect(self.waterProductivityChange)
            self.dlg.resolutionList.currentIndexChanged.connect(self.resolutionListChange)
            self.dlg.startDate.dateChanged.connect(self.onStartDateChanged)
            self.dlg.endDate.dateChanged.connect(self.onEndDateChanged)

            

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
