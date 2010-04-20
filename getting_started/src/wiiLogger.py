#!/usr/bin/python
'''
     Copyright 2010 by Claudio Giovanoli, ggiova@student.ethz.ch, ETH Zurich
     This programm takes the x,y data of two Wiimotes IR cams t0 run a 3D tracking of 2 IR sources attached to each other, but pointing in perpendicular directions. T
     The 3D data from two Wiimotes writes data to ./logfile.txt
'''

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

class position3d():
    def __init__(self, wiimotes):
        self.wiimotes = wiimotes
        
    def getPosition(self):
        measurements = []
        for wiiCon in self.wiimotes:
            measurements.append(wiiCon.averageIRPosition)
        position = self._calculate3DPosition(measurements)
        return position 
    
    def _calculate3DPosition(self,measurements):

        if len(measurements) < 2:
            sys.stderr.write("ERR: measurement data insufficient!")
            return
        

        point, position = zeros(3), zeros(3)
        
    
        #3D camera positions / first points for the 2 line equations
        cameraPosition = [[715.0,297.,4000.],[2800.,297.,0.]]
        #second points for the lines
        bildebene = [empty(3),empty(3)]
        # Scaling factor ot evaluate the second points
        streckung= 5.0
        
        #angle between default (pinting perpendicular on the surface) and actual pointing direction of the IR camera (rot around y axis)
        winkelwii1=math.radians(0)
        winkelwii2=math.radians(110)
        phi=([winkelwii1,winkelwii2])
        
        #intersection points of the two lines
        pa,pb = empty(3),empty(3) 
        
        #final scaling facors for the intersection points
        mua = 0.0
        mub = 0.0
        
        # estimation line equations in global coordinates
        # cam 0 (in default position))
        vt1=transformation(phi[0],measurements[0])
        bildebene[0] = cameraPosition[0] + streckung * vt1
        
        # cam 1 (rot phi about y axis )
        vt2=transformation(phi[1],measurements[1])
        bildebene[1] = cameraPosition[1] + streckung * vt2
        
        #Estimation of intersection of the two lines
        LineLineIntersect(cameraPosition[0],bildebene[0],cameraPosition[1], bildebene[1],pa,pb,mua, mub)
    
        position = pa+0.5*(pb-pa)
        return list(position)
    
    
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
    # the  poll is buggy:
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
    p13 = {0:0.0,1:0.0,2:0.0}
    p43 = {0:0.0,1:0.0,2:0.0}
    p21 = {0:0.0,1:0.0,2:0.0}

    d1343 = 0.0
    d4321 = 0.0
    d1321 = 0.0
    d4343 = 0.0
    d2121 = 0.0

    numer = 0.0
    denom = 0.0

    p13[0] = p1[0] - p3[0]
    p13[1] = p1[1] - p3[1]
    p13[2] = p1[2] - p3[2]
    p43[0] = p4[0] - p3[0]
    p43[1] = p4[1] - p3[1]
    p43[2] = p4[2] - p3[2]
    if (math.fabs(p43[0])  < EPS and math.fabs(p43[1])  < EPS and math.fabs(p43[2])  < EPS):
        return False
    p21[0] = p2[0] - p1[0]
    p21[1] = p2[1] - p1[1]
    p21[2] = p2[2] - p1[2]
    if (math.fabs(p21[0])  < EPS and math.fabs(p21[1])  < EPS and math.fabs(p21[2])  < EPS):
        return False

    d1343 = p13[0] * p43[0] + p13[1] * p43[1] + p13[2] * p43[2]
    d4321 = p43[0] * p21[0] + p43[1] * p21[1] + p43[2] * p21[2]
    d1321 = p13[0] * p21[0] + p13[1] * p21[1] + p13[2] * p21[2]
    d4343 = p43[0] * p43[0] + p43[1] * p43[1] + p43[2] * p43[2]
    d2121 = p21[0] * p21[0] + p21[1] * p21[1] + p21[2] * p21[2]

    denom = d2121 * d4343 - d4321 * d4321
    if (math.fabs(denom) < EPS):
        return False
    numer = d1343 * d4321 - d1321 * d4343

    mua = numer / denom;
    mub = (d1343 + d4321 * (mua)) / d4343

    pa[0] = p1[0] + mua * p21[0]
    pa[1] = p1[1] + mua * p21[1]
    pa[2] = p1[2] + mua * p21[2]
    pb[0] = p3[0] + mub * p43[0]
    pb[1] = p3[1] + mub * p43[1]
    pb[2] = p3[2] + mub * p43[2]

    return True


def transformation(phi,measurement):
    '''
    rechnet den Richtungsvektor der beiden geraden  in globalen koordinaten aus
    Umrechnungsfaktor pixel->mm in Bildebene L0 (aus Experiment)
    '''
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
    
    # init wii connections based on command line parameter
    wiimoteCount = len(sys.argv)-1
    print 'Put', wiimoteCount, ' Wiimote(s) in discoverable mode now (press 1+2)...'
    for wiiIndex in range(0,wiimoteCount):
        current = wiimoteConnection(sys.argv[wiiIndex+1],wiiIndex)
        wiimotes.append(current)
        current.start()
    
    # init position manager
    positionManager = position3d(wiimotes)

    lastLogTime = time.time()
    while (LoggingIsActive):
        time.sleep(0.5)
        
        # get position and delta time
        currentPosition = positionManager.getPosition()
        logTime = time.time()
        
        # print time to logfile and STDOUT
        print logTime-lastLogTime,
        logFile.write(str(logTime-lastLogTime))
         
        # print position to logfile and STDOUT
        for c in currentPosition:
            print ",", c,
            logFile.write("," + str(c))
        print
        
        logFile.write("\n")    
        
        lastLogTime = logTime
        
        
    print "shutting down system"
    for wiiCon in wiimotes:
        wiiCon.killThread()
        
    logFile.close()


if __name__ == "__main__":
    sys.exit(main())
