#!/usr/bin/python
import cwiid
import sys


def wiimoteCallback(mesg_list, time):
    print "status geaendert"
    
    print sys.argv[0]
#connect wiimote
myWii = cwiid.Wiimote("00:1E:35:03:E3:6D")


#register callback
myWii.mesg_callback = wiimoteCallback


#getting ir information and status
rpt_mode = 0
rpt_mode ^= cwiid.RPT_BTN
rpt_mode ^= cwiid.RPT_EXT
rpt_mode ^= cwiid.RPT_IR
rpt_mode ^= cwiid.RPT_STATUS
myWii.rpt_mode = rpt_mode
myWii.enable(cwiid.FLAG_MESG_IFC)

def callback(mesg_list, time):
    for mesg in mesg_list:
        if mesg[0] == cwiid.MESG_IR:
            valid_src = False
            print 'IR Report: ',
            for src in mesg[1]:
                if src:
                    valid_src = True
                    print src['pos'],
                if not valid_src:
                    print 'no sources detected'
                else:
                    print

myWii.close()