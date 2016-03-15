#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################

import os
import sys
import indigo
import math
import decimal
import datetime
from ghpu import GitHubPluginUpdater

class Plugin(indigo.PluginBase):

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.updater = GitHubPluginUpdater('tenallero', 'Indigo-MixPresence', self)
            
        self.apiVersion    = "2.0"
        self.localAddress  = ""

        # create empty device list      
        self.deviceList = {}
        
        self.unifiPlugin = None
        self.pingPlugin = None
        self.beaconPlugin = None
        
    def __del__(self):
        indigo.PluginBase.__del__(self)     

    ###################################################################
    # Plugin
    ###################################################################

    def deviceStartComm(self, device):
        self.debugLog(u"Started device: " + device.name)
        device.stateListOrDisplayStateIdChanged()
        self.addDeviceToList (device)

    def deviceStopComm(self,device):
        if device.id in self.deviceList:
            self.debugLog("Stoping device: " + device.name)
            self.deleteDeviceFromList(device)

    def deviceCreated(self, device):
        indigo.server.log (u"Created new device \"%s\" of type \"%s\"" % (device.name, device.deviceTypeId))
        pass
        
    def deviceDeleted(self, device):
        indigo.server.log (u"Deleted device \"%s\" of type \"%s\"" % (device.name, device.deviceTypeId))
        if device.id in self.deviceList:
             del self.deviceList[device.id]

    def addDeviceToList(self,device):
        if device:        
            if device.id not in self.deviceList:   
                
                checkNextTime = datetime.datetime.now() - datetime.timedelta(seconds=10)
                checkInterval = 15 #device.pluginProps["checkInterval"]
                self.deviceList[device.id] = {'ref':device, 'checkInterval':checkInterval, 'checkNextTime': checkNextTime, 'lastSeen': None, 'firstSeen': None}       

    def deleteDeviceFromList(self, device):
        if device:
            if device.id in self.deviceList:
                del self.deviceList[device.id]

    def startup(self):
        self.loadPluginPrefs()
        self.debugLog(u"startup called")
                
        self.unifiPlugin  = indigo.server.getPlugin("com.tenallero.indigoplugin.unifi")
        self.pingPlugin   = indigo.server.getPlugin("com.tenallero.indigoplugin.ping")
        self.beaconPlugin = indigo.server.getPlugin("se.furtenbach.indigo.plugin.beacon")
        
        if not self.unifiPlugin.isEnabled():
            self.errorLog (u"Error: Unifi plugin is not enabled")
        if not self.pingPlugin.isEnabled():
            self.errorLog (u"Error: Ping plugin is not enabled")
        if not self.beaconPlugin.isEnabled():
            self.errorLog (u"Error: Beacon plugin is not enabled")        
        self.updater.checkForUpdate()
        

    def shutdown(self):
        self.debugLog(u"shutdown called")

    def getDeviceConfigUiValues(self, pluginProps, typeId, devId):
        valuesDict = pluginProps
        errorMsgDict = indigo.Dict()           
        return (valuesDict, errorMsgDict)

    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        self.debugLog(u"validating device Prefs called") 
        return (True, valuesDict)

    def validatePrefsConfigUi(self, valuesDict):        
        return (True, valuesDict)

    def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
        if userCancelled is False:
            indigo.server.log ("Device preferences were updated.")
            device = indigo.devices[devId]
            self.deleteDeviceFromList (device)
            self.addDeviceToList (device)

    def closedPrefsConfigUi ( self, valuesDict, UserCancelled):
        #   If the user saves the preferences, reload the preferences
        if UserCancelled is False:
            indigo.server.log ("Preferences were updated, reloading Preferences...")
            self.loadPluginPrefs()

    def loadPluginPrefs(self):
        # set debug option
        if 'debugEnabled' in self.pluginPrefs:
            self.debug = self.pluginPrefs['debugEnabled']
        else:
            self.debug = False        
  
    
    def menuGetDevsUnifi(self, filter, valuesDict, typeId, elemId):
        #self.debugLog(u"menuGetDevsUnifi ... ")
        menuList = []
        for dev in indigo.devices.iter(filter="com.tenallero.indigoplugin.unifi.unifiuser"):
            if dev.enabled:
                menuList.append((dev.id, dev.name))
        return menuList
           
    def menuGetDevsPing(self, filter, valuesDict, typeId, elemId):
        #self.debugLog(u"menuGetDevsPing ... ")
        menuList = []
        for dev in indigo.devices.iter(filter="com.tenallero.indigoplugin.ping.pingdevice"):
            #self.debugLog(u"menuGetDevsPing ... " + dev.name)
            if dev.enabled:
                menuList.append((dev.id, dev.name))
        return menuList  
         
    def menuGetDevsGeofence(self, filter, valuesDict, typeId, elemId):
        #self.debugLog(u"menuGetDevsGeofence ... ")
        menuList = []
        for dev in indigo.devices.iter(filter="se.furtenbach.indigo.plugin.beacon.beacon"):
            if dev.enabled:
                menuList.append((dev.id, dev.name))
        return menuList  
               
    
    
    
    ###################################################################
    # Concurrent Thread.
    ###################################################################

    def runConcurrentThread(self):

        self.debugLog(u"Starting Concurrent Thread")
        
        try:
            while self.stopThread == False: 
                indigoDevice = None
                try:
                    todayNow = datetime.datetime.now()
                    for presenceDevice in self.deviceList:
                        checkNextTime = self.deviceList[presenceDevice]['checkNextTime']

                        if checkNextTime <= todayNow:                            
                            checkInterval = self.deviceList[presenceDevice]['checkInterval']
                            checkNextTime = todayNow + datetime.timedelta(seconds=int(checkInterval))
                            self.deviceList[presenceDevice]['checkNextTime'] = checkNextTime                         

                            indigoDevice = self.deviceList[presenceDevice]['ref']                           
                            self.deviceRequestStatus(indigoDevice)
                            
                except Exception,e:
                    self.errorLog (u"Error: " + str(e))
                    pass
                self.sleep(1)
            

        except self.StopThread:
            pass

        except Exception, e:
            self.errorLog (u"Error: " + str(e))
            pass    

    def stopConcurrentThread(self):
        self.stopThread = True
        self.debugLog(u"stopConcurrentThread called")
    
    ###################################################################
    # Presence logic
    ###################################################################

    def deviceRequestStatus(self,device):
        unifideviceid     = int(device.pluginProps["unifidevice"])
        pingdeviceid      = int(device.pluginProps["pingdevice"])

        self.unifiPlugin.executeAction("silentStatusRequest", deviceId=unifideviceid)
        self.pingPlugin.executeAction ("silentStatusRequest", deviceId=pingdeviceid)

        #indigo.device.statusRequest(unifideviceid,     suppressLogging=True)
        #indigo.device.statusRequest(pingdeviceid,      suppressLogging=True)

        self.deviceAnalyzeStatus(device)

    def deviceAnalyzeStatus(self,device):

        unifideviceid     = int(device.pluginProps["unifidevice"])
        pingdeviceid      = int(device.pluginProps["pingdevice"])
        geofencedevice1id = int(device.pluginProps["geofencedevice1"])
        geofencedevice2id = int(device.pluginProps["geofencedevice2"])
        geofencedevice3id = int(device.pluginProps["geofencedevice3"])
        
        onUnifi = indigo.devices[unifideviceid].states["onOffState"]
        onPing  = indigo.devices[pingdeviceid].states["onOffState"]
        onGeo1  = indigo.devices[geofencedevice1id].states["onOffState"]
        onGeo2  = indigo.devices[geofencedevice2id].states["onOffState"]
        onGeo3  = indigo.devices[geofencedevice3id].states["onOffState"]
        newValue = False
        
        
        
        
        
        if not newValue == device.states['onOffState']:
           device.updateStateOnServer(key='onOffState', value=newValue)
           if newValue:
                indigo.server.log (device.name + u" is detected")        
           else:
                indigo.server.log (device.name + u" is out!")        
           pass        
        
        
        
    ###################################################################
    # Custom Action callbacks
    ###################################################################        
       
    def actionControlSensor(self, action, dev):
        if action.sensorAction == indigo.kSensorAction.RequestStatus:
            self.deviceRequestStatus(dev)
            indigo.server.log ('sent "' + dev.name + '" status request')
            pass
            
            
    ########################################
    # Menu Methods
    ########################################
    def toggleDebugging(self):
        if self.debug:
            indigo.server.log("Turning off debug logging")
            self.pluginPrefs["debugEnabled"] = False                
        else:
            indigo.server.log("Turning on debug logging")
            self.pluginPrefs["debugEnabled"] = True
        self.debug = not self.debug
        return

    def checkForUpdates(self):
        update = self.updater.checkForUpdate() 
        if (update != None):
            pass
        return    

    def updatePlugin(self):
        self.updater.update()
                    