# Copyright 2010 by Bastian Migge, inspire AG

#!/usr/bin/python
import cwiid
import sys
import time
import signal, os
import math
from threading import Thread
from numpy import *
import time

# wiimote 3d tracking for two cameras
# 
# - wiis defined by adress given by command line argument
# - absolute camera positions
# - camera orientation: upper left corner of camera screen relative to camera
# - one thread per camera :communication, callbacks on update, buffer of last position
# - 3d calculation with shortest line between two lines given by the camera's positions and their measured point on the cam-screen


wiimotes = []
shutdownLogger = False
LoggingIsActive = True

    
# connection thread to wiimote
class wiimoteConnection(Thread):
    def __init__ (self, btaddress, index):
        Thread.__init__(self)

        # parameter
        self.address = str(btaddress)
        self.index = index
        self.wiimote = None

        # global init
        self.shutdown = False
        self.averageIRPosition = {'x':-1,'y':-1}

        # local helper    
        rpt_mode = 0

        # connect Wiimote
        wiimote = cwiid.Wiimote(self.address)
        self.wiimote = wiimote
        # setup
        self.wiimote.led = self.index+1
        rpt_mode ^= cwiid.RPT_BTN
        rpt_mode ^= cwiid.RPT_EXT
        rpt_mode ^= cwiid.RPT_IR
        rpt_mode ^= cwiid.RPT_STATUS
        self.wiimote.rpt_mode = rpt_mode
        self.wiimote.enable(cwiid.FLAG_MESG_IFC)
        wiimote.mesg_callback = self.wiimoteCallback
        print "WiiMote ", self.index,"(", self.address,  ") connected."

    def __del__(self):
        self.wiimote.close()
        
    def run(self):
        while not self.shutdown:
            #self.updateAverageIrPosition()
            time.sleep(1)
        self.wiimote.close()

    def killThread(self):
        self.shutdown = True

    # wiimote callback (currently, we considere only the IR info)
    def wiimoteCallback(self, mesg_list, time):
        #print 'time: %f' % time

        avgPos = {'x':0,'y':0}
        validSourcesCount = 0

        for mesg in mesg_list:
            if mesg[0] == cwiid.MESG_IR:
                for src in mesg[1]:
                    if src:
                        validSourcesCount += 1
                        avgPos['x'] += int(src['pos'][0]) #add x position
                        avgPos['y'] += int(src['pos'][1]) #add y position

        # update value only if we got valuable data       
        if (validSourcesCount > 0):
            avgPos['x'] /= validSourcesCount 
            avgPos['y'] /= validSourcesCount 

            self.averageIRPosition = avgPos

        return
            
    # UPDATE: the center of all detected IR points (POLL FROM WII)
    # the fucking poll is buggy:
    # http://abstrakraft.org/cwiid/discussion/topic/19?discussion_action=set-display;display=flat-desc
    def updateAverageIrPosition(self):
        avgPos = {'x':0,'y':0}
        self.wiimote.request_status() # pull status
        state = self.wiimote.state

        validSourcesCount = 0
        if 'ir_src' in state:
            for src in state['ir_src']:
                if src:
                    validSourcesCount += 1
                    avgPos['x'] += int(src['pos'][0])
                    avgPos['y'] += int(src['pos'][1])

        # update value only if we got valuable data        
        if (validSourcesCount > 0):
            avgPos['x'] /= validSourcesCount 
            avgPos['y'] /= validSourcesCount 

            self.averageIRPosition = avgPos
        return


    def getAverageIrPosition(self):
        self.updateAverageIrPosition()
        return self.averageIRPosition
###################################################

# utils

#   Calculate the line segment PaPb that is the shortest route between
#   two lines P1P2 and P3P4. Calculate also the values of mua and mub where
#      Pa = P1 + mua (P2 - P1)
#      Pb = P3 + mub (P4 - P3)
#   Return FALSE if no solution exists.
# source: http://local.wasp.uwa.edu.au/~pbourke/geometry/lineline3d/

def LineLineIntersect(p1,p2,p3,p4,pa,pb,mua,mub):
    EPS = 0.000001
    p13 = {'x':0.0,'y':0.0,'z':0.0}
    p43 = {'x':0.0,'y':0.0,'z':0.0}
    p21 = {'x':0.0,'y':0.0,'z':0.0}

    d1343 = 0.0
    d4321 = 0.0
    d1321 = 0.0
    d4343 = 0.0
    d2121 = 0.0

    numer = 0.0
    denom = 0.0

    p13['x'] = p1['x'] - p3['x']
    p13['y'] = p1['y'] - p3['y']
    p13['z'] = p1['z'] - p3['z']
    p43['x'] = p4['x'] - p3['x']
    p43['y'] = p4['y'] - p3['y']
    p43['z'] = p4['z'] - p3['z']
    if (math.fabs(p43['x'])  < EPS and math.fabs(p43['y'])  < EPS and math.fabs(p43['z'])  < EPS):
        return False
    p21['x'] = p2['x'] - p1['x']
    p21['y'] = p2['y'] - p1['y']
    p21['z'] = p2['z'] - p1['z']
    if (math.fabs(p21['x'])  < EPS and math.fabs(p21['y'])  < EPS and math.fabs(p21['z'])  < EPS):
        return False

    d1343 = p13['x'] * p43['x'] + p13['y'] * p43['y'] + p13['z'] * p43['z']
    d4321 = p43['x'] * p21['x'] + p43['y'] * p21['y'] + p43['z'] * p21['z']
    d1321 = p13['x'] * p21['x'] + p13['y'] * p21['y'] + p13['z'] * p21['z']
    d4343 = p43['x'] * p43['x'] + p43['y'] * p43['y'] + p43['z'] * p43['z']
    d2121 = p21['x'] * p21['x'] + p21['y'] * p21['y'] + p21['z'] * p21['z']

    denom = d2121 * d4343 - d4321 * d4321
    if (math.fabs(denom) < EPS):
        return False
    numer = d1343 * d4321 - d1321 * d4343

    mua = numer / denom;
    mub = (d1343 + d4321 * (mua)) / d4343

    pa['x'] = p1['x'] + mua * p21['x']
    pa['y'] = p1['y'] + mua * p21['y']
    pa['z'] = p1['z'] + mua * p21['z']
    pb['x'] = p3['x'] + mub * p43['x']
    pb['y'] = p3['y'] + mub * p43['y']
    pb['z'] = p3['z'] + mub * p43['z']

    return True


def transformation(phi,measurement):
    #rechnet den Richtungsvektor der beiden geraden  in globalen koordinaten aus
    #Umrechnungsfaktor pixel->mm in Bildebene L0 (aus Experiment)
    f = 0.821659482758621
    
    # Stuetzvektor zum Nullpunkt der Bildebene L= relativ zur kamera (in mm)
    v0 = array([-417.0,-312.0,1100.0])
    
    #Koordinatentrasformation R0 der wii Grundposition(senkrecht auf SB) auf die globalen (SB-) Koordinaten
    R0 = matrix([[1.0,0.0,0.0],[0.0,-1.0,0.0],[0.0,0.0,-1.0]])
    
    #Koordinatentransformation von beliebiger Position (mit Winkelabweichung phi zur gGrundposition)auf  globale (SB-) Koordinaten
    R1 = matrix([[math.cos(phi),0.0,math.sin(phi)],[0.0,1.0,0.0],[-math.sin(phi),0.0,math.cos(phi)]])*R0
    #input1 = matrix([[int(measurement['x'])],[int(measurement['y'])],[0.0]])
    input = array([int(measurement['x']),int(measurement['y']),0.0])
    vtwii=(v0+f*input)
    vt = vtwii*R1.transpose()
    vt = array(vt)[0]
    return vt 

    
def get3DPosition(measurements):

    if len(measurements) < 2:
        sys.stderr.write("ERR: measurement data insufficient!")
        return
    
    point = {'x':0,'y':0,'z':0}
    position = {'x':0,'y':0,'z':0}

    # 3D kamera position phia. angle between default and actual direction of the IR camera (rot around y axis)
    cameraPosition = [{'x':715,'y':297,'z':4000},{'x':2800,'y':297,'z':0}]
    winkelwii1=math.radians(0)
    winkelwii2=math.radians(110)
    phi=([winkelwii1,winkelwii2])
    
    # zwei weit entfernte (ca 10 m) punkte auf der geraden durch die messung und die camera:
    bildebene = [{'x':None,'y':None,'z':None},{'x':None,'y':None,'z':None}]
    #bildebene = [empty(3),empty(3)]
    
    #helper
    #schnittpunkte
    pa  = {'x':None,'y':None,'z':None}
    pb = {'x':None,'y':None,'z':None}
    # Streckfaktor zur Evaluation  des 2. Punkts fuer die Geradengleichung
    streckung= 5.0
    mua = 0.0
    mub = 0.0
    
    
    # cam 0 (in Grundposition)
    vt1=transformation(phi[0],measurements[0])
    #bildebene[0] = cameraPosition[0] + streckung * vt1
    bildebene[0]['x'] = cameraPosition[0]['x'] + streckung * vt1[0]
    bildebene[0]['y'] = cameraPosition[0]['y'] + streckung * vt1[1]
    bildebene[0]['z'] = cameraPosition[0]['z'] + streckung * vt1[2]
    
    # cam 1 (seite)
    vt2=transformation(phi[1],measurements[1])
    bildebene[1]['x'] = cameraPosition[1]['x'] + streckung * vt2[0]
    bildebene[1]['y'] = cameraPosition[1]['y'] + streckung * vt2[1]
    bildebene[1]['z'] = cameraPosition[1]['z'] + streckung * vt2[2]
    
  
    LineLineIntersect(cameraPosition[0],bildebene[0],cameraPosition[1], bildebene[1],pa,pb,mua, mub)

    position['x'] = pa['x']+0.5*(pb['x']-pa['x'])
    position['y'] = pa['y']+0.5*(pb['y']-pa['y'])
    position['z'] = pa['z']+0.5*(pb['z']-pa['z'])
    return position

def signalHandler(signum, frame):
    global LoggingIsActive
    print 'Signal handler called with signal', signum
    LoggingIsActive = False
    
#####################################
def main():
    global wiimotes
    global shutdownLogger
    global LoggingIsActive
    
    if len(sys.argv) < 1:
        print "no wiimote address given"
        sys.exit(1)

    signal.signal(signal.SIGALRM, signalHandler)

    # open logfile
    logFile = open('logfile.txt', 'w')

    wiimoteCount = len(sys.argv)-1
    print 'Put', wiimoteCount, ' Wiimote(s) in discoverable mode now (press 1+2)...'
    for wiiIndex in range(0,wiimoteCount):
        current = wiimoteConnection(sys.argv[wiiIndex+1],wiiIndex)
        wiimotes.append(current)
        current.start()
    
    lastLogTime = time.time()
    while (LoggingIsActive):
        time.sleep(0.5)
        measurements = []
        for wiiCon in wiimotes:
            measurements.append(wiiCon.averageIRPosition)
        #print measurements
        position = get3DPosition(measurements)
        logTime = time.time()
        
        print logTime-lastLogTime,
        logFile.write(str(logTime-lastLogTime))
         
        lastLogTime = logTime
        for c in position.values():
            print ",", c,
            logFile.write("," + str(c))
        print
        logFile.write("\n")    
        
    print "shutting down system"
    for wiiCon in wiimotes:
        wiiCon.killThread()
        
    logFile.close()


if __name__ == "__main__":
    sys.exit(main())
