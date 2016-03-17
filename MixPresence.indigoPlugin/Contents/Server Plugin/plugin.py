#! /usr/bin/env python
# -*- coding: utf-8 -*-
#######################

import os
import sys
import indigo
import math
import decimal
import datetime
import time
from ghpu import GitHubPluginUpdater

class Plugin(indigo.PluginBase):

    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.updater = GitHubPluginUpdater(self)
            
        self.apiVersion    = "2.0"
        self.localAddress  = ""

        # create empty device list      
        self.deviceList = {}
        self.updateableList = {}
        
        self.unifiPlugin = None
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
                statusNextTime = datetime.datetime.now() - datetime.timedelta(seconds=10)
                statusInterval = 600 #device.pluginProps["statusInterval"]
                self.deviceList[device.id] = {
                 'ref':device,
                 'statusInterval':statusInterval, 
                 'statusNextTime': statusNextTime,
                 'analyze': False, 
                 'analyzeNextTime': statusNextTime, 
                 'lastSeen': 0, 
                 'firstSeen': 0, 
                 'onUnifi': False, 
                 'onPing': False,
                 'onGeo1': False,
                 'onGeo2': False,
                 'onGeo3': False
                 }       
                self.addDeviceToUpdateable(device)

    def addDeviceToUpdateable(self,device):
        unifideviceid     = int(device.pluginProps["unifidevice"])
        geofencedevice1id = int(device.pluginProps["geofencedevice1"])
        geofencedevice2id = int(device.pluginProps["geofencedevice2"])
        geofencedevice3id = int(device.pluginProps["geofencedevice3"])
        self.updateableList[unifideviceid]     = {'parentDeviceId': device.id}
        self.updateableList[geofencedevice1id] = {'parentDeviceId': device.id}
        self.updateableList[geofencedevice2id] = {'parentDeviceId': device.id}
        self.updateableList[geofencedevice3id] = {'parentDeviceId': device.id}
        
    def deleteDeviceFromList(self, device):
        if device:
            if device.id in self.deviceList:
                del self.deviceList[device.id]
                self.deleteDeviceFromUpdateable(device)

    def deleteDeviceFromUpdateable(self,device):
        unifideviceid     = int(device.pluginProps["unifidevice"])
        geofencedevice1id = int(device.pluginProps["geofencedevice1"])
        geofencedevice2id = int(device.pluginProps["geofencedevice2"])
        geofencedevice3id = int(device.pluginProps["geofencedevice3"])
        if unifideviceid in self.updateableList:
            del self.updateableList[unifideviceid]
        if geofencedevice1id in self.updateableList:
            del self.updateableList[geofencedevice1id]    
        if geofencedevice2id in self.updateableList:
            del self.updateableList[geofencedevice2id]
        if geofencedevice3id in self.updateableList:
            del self.updateableList[geofencedevice3id]

    def startup(self):
        self.loadPluginPrefs()
        self.debugLog(u"startup called")
                
        self.unifiPlugin  = indigo.server.getPlugin("com.tenallero.indigoplugin.unifi")
        self.beaconPlugin = indigo.server.getPlugin("se.furtenbach.indigo.plugin.beacon")
        
        if not self.unifiPlugin.isEnabled():
            self.errorLog (u"Error: Unifi plugin is not enabled")
        if not self.beaconPlugin.isEnabled():
            self.errorLog (u"Error: Beacon plugin is not enabled")        
        self.updater.checkForUpdate()
        indigo.devices.subscribeToChanges()

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
        menuList = []
        for dev in indigo.devices.iter(filter="com.tenallero.indigoplugin.unifi.unifiuser"):
            if dev.enabled:
                menuList.append((dev.id, dev.name))
        return menuList
           
    def menuGetDevsPing(self, filter, valuesDict, typeId, elemId):
        menuList = []
        for dev in indigo.devices.iter(filter="com.tenallero.indigoplugin.ping.pingdevice"):
            if dev.enabled:
                menuList.append((dev.id, dev.name))
        return menuList  
         
    def menuGetDevsGeofence(self, filter, valuesDict, typeId, elemId):
        menuList = []
        for dev in indigo.devices.iter(filter="se.furtenbach.indigo.plugin.beacon.beacon"):
            if dev.enabled:
                menuList.append((dev.id, dev.name))
        return menuList  

    def deviceUpdated (self, origDev, newDev):
        if origDev.id in self.updateableList:
            if not origDev.states['onOffState'] == newDev.states['onOffState']:
                parentDeviceId = int(self.updateableList[origDev.id]["parentDeviceId"])
                if parentDeviceId in self.deviceList:
                    msg = u'device "' + origDev.name + u'" has been updated. Now is '
                    if newDev.states['onOffState']:
                        msg += u'on.'                       
                    else:
                        msg += u'off.'
                    #self.debugLog(msg)
                    indigo.server.log (msg)
                    self.deviceList[parentDeviceId]['statusNextTime'] = datetime.datetime.now() - datetime.timedelta(seconds=10)
    
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
                        if self.deviceList[presenceDevice]['statusInterval'] > 0:
                            statusNextTime = self.deviceList[presenceDevice]['statusNextTime']

                            if statusNextTime <= todayNow:                            
                                statusInterval = self.deviceList[presenceDevice]['statusInterval']
                                statusNextTime = todayNow + datetime.timedelta(seconds=int(statusInterval))
                                self.deviceList[presenceDevice]['statusNextTime'] = statusNextTime                         

                                indigoDevice = self.deviceList[presenceDevice]['ref']
                                
                                self.deviceList[presenceDevice]['analyze'] = True 
                                self.deviceList[presenceDevice]['analyzeNextTime'] = todayNow + datetime.timedelta(seconds=1)    
                                self.debugLog(u'ConcurrentThread. Sent "' + indigoDevice.name + '" status request')                 
                                self.deviceRequestStatus(indigoDevice)
                                self.debugLog(u'ConcurrentThread. Received "' + indigoDevice.name + '" status')  
                        
                        if self.deviceList[presenceDevice]['analyze']:  
                            analyzeNextTime = self.deviceList[presenceDevice]['analyzeNextTime'] 
                            if analyzeNextTime <= todayNow: 
                                indigoDevice = self.deviceList[presenceDevice]['ref'] 
                                self.debugLog(u'ConcurrentThread. Analyzing "' + indigoDevice.name + '"')   
                                self.deviceList[presenceDevice]['analyze'] = False                        
                                self.deviceAnalyzeStatus(indigoDevice)
                        
                        
                except Exception,e:
                    self.errorLog (u"Error: " + str(e))
                    pass
                self.sleep(0.3)
            

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
        self.unifiPlugin.executeAction("silentStatusRequest", deviceId=unifideviceid)
 
    def deviceAnalyzeStatus(self,device):
        changeCause  = ""
        changed      = False
        changedUnifi = False
        changedGeo1  = False
        changedGeo2  = False
        changedGeo3  = False
        onOffState   = False
        
        unifideviceid     = int(device.pluginProps["unifidevice"])
        geofencedevice1id = int(device.pluginProps["geofencedevice1"])
        geofencedevice2id = int(device.pluginProps["geofencedevice2"])
        geofencedevice3id = int(device.pluginProps["geofencedevice3"])
        
        onUnifi = indigo.devices[unifideviceid].states["onOffState"]     
        onGeo1  = indigo.devices[geofencedevice1id].states["onOffState"]
        onGeo2  = indigo.devices[geofencedevice2id].states["onOffState"]
        onGeo3  = indigo.devices[geofencedevice3id].states["onOffState"]
        
        firstSeen  = int(indigo.devices[unifideviceid].states["firstSeen"])
        lastSeen   = int(indigo.devices[unifideviceid].states["lastSeen"])
       
        if device.id in self.deviceList:
            if not onUnifi == self.deviceList[device.id]['onUnifi']:
                changedUnifi = True
                changed      = True          
            if not onGeo1 == self.deviceList[device.id]['onGeo1']:
                changedGeo1 = True
                changed     = True
            if not onGeo2 == self.deviceList[device.id]['onGeo2']:
                changedGeo2 = True
                changed     = True
            if not onGeo3 == self.deviceList[device.id]['onGeo3']:
                changedGeo3 = True
                changed     = True
            if not onUnifi == self.deviceList[device.id]['onUnifi']:
                changedUnifi = True
                changed      = True
                                                                                
            self.deviceList[device.id]['onUnifi']   = onUnifi
            self.deviceList[device.id]['onGeo1']    = onGeo1
            self.deviceList[device.id]['onGeo2']    = onGeo2
            self.deviceList[device.id]['onGeo3']    = onGeo3
            self.deviceList[device.id]['firstSeen'] = firstSeen
            self.deviceList[device.id]['lastSeen']  = lastSeen  
       
        now = int(time.time())
        minutesLastSeen = (now - lastSeen) / 60
        
        onOffState = device.states['onOffState']
       
        if changed:
            if changedUnifi:
                if onUnifi:
                    onOffState = True
                    changeCause = u"#1 Se ha conectado a la WIFI"
                else:
                    onOffState = False
                    changeCause = u"#2 Se ha desconectado de la WIFI. Sin actividad durante " + str(int(minutesLastSeen)) + " min."
            elif onOffState:
                if changedGeo2 and not onGeo2:
                    onOffState = False
                    changeCause = u"#3 Ha salido de Plana Novella"
                if changedGeo3 and not onGeo3:
                    onOffState = False
                    changeCause = u"#4 Ha salido del Parque Natural"                 
            elif changedGeo1 and onGeo1 and not onUnifi and minutesLastSeen > 20:
                onOffState = True 
                changeCause = u"#5 Entra en CanTeula. No estaba conectado a la WIFI desde hace " + str(int(minutesLastSeen)) + " min."
            elif changedGeo1 and not onGeo1:
                #onOffState = False
                changeCause = u"#6 Sale de CanTeula." 
                
        else:
            if not onOffState and onUnifi and minutesLastSeen < 3:
                onOffState = True
                changeCause = u"#7 Estaba OUT. Pero, ya estaba conectado a la WIFI"
            elif onOffState and minutesLastSeen > 15:
                onOffState = False
                changeCause = u"#8 Estaba IN. Pero, sin actividad desde hace " + str(int(minutesLastSeen)) + " min."
            elif onOffState and not onUnifi and not onGeo1
                onOffState = False
                changeCause = u"#9 Estaba IN. No estaba conectado en WIFI. No estaba en Canteula." 
            elif onOffState and not onUnifi and not onGeo2 and not onGeo3
                onOffState = False
                changeCause = u"#10 Estaba IN. No estaba conectado en WIFI. No estaba en Plana Novella ni Parque Natural." 
                    
        if not onOffState == device.states['onOffState']:
            if onOffState:
                indigo.server.log (u'"' + device.name + u'" is IN  (' + changeCause + ')')        
            else:
                indigo.server.log (u'"' + device.name + u'" is OUT  (' + changeCause + ')') 
            device.updateStateOnServer(key='onOffState', value=onOffState)            
        
    ###################################################################
    # Custom Action callbacks
    ###################################################################        
       
    def actionControlSensor(self, action, dev):
        if action.sensorAction == indigo.kSensorAction.RequestStatus:
            indigo.server.log ('sent "' + dev.name + '" status request')
            self.deviceList[dev.id]['statusNextTime'] = datetime.datetime.now() - datetime.timedelta(seconds=10) 
            
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
                    