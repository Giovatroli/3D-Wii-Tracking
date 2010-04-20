#!/usr/bin/python

# modified wmdemo version for continuous 2D tracking of IR source
import cwiid
import sys
import csv


menu = '''1: toggle LED 1
2: toggle LED 2
3: toggle LED 3
4: toggle LED 4
5: toggle rumble
a: toggle accelerometer reporting
b: toggle button reporting
c: enable motionplus, if connected
e: toggle extension reporting
i: toggle ir reporting
m: toggle messages
p: print this menu
r: request status message ((t) enables callback output)
s: print current state
t: toggle status reporting
x: exit'''

def main():
    led = 0
    rpt_mode = 0
    rumble = 0
    mesg = False

    #Connect to address given on command-line, if present
    print 'Put Wiimote in discoverable mode now (press 1+2)...'
    global wiimote
    if len(sys.argv) > 1:
        wiimote = cwiid.Wiimote(sys.argv[1])
    else:
        wiimote = cwiid.Wiimote()

    wiimote.mesg_callback = callback

    print menu

    exit = 0
    while not exit:
        c = sys.stdin.read(1)
        if c == '1':
            led ^= cwiid.LED1_ON
            wiimote.led = led
        elif c == '2':
            led ^= cwiid.LED2_ON
            wiimote.led = led
        elif c == '3':
            led ^= cwiid.LED3_ON
            wiimote.led = led
        elif c == '4':
            led ^= cwiid.LED4_ON
            wiimote.led = led
        elif c == '5':
            rumble ^= 1
            wiimote.rumble = rumble
        elif c == 'a':
            rpt_mode ^= cwiid.RPT_ACC
            wiimote.rpt_mode = rpt_mode
        elif c == 'b':
            rpt_mode ^= cwiid.RPT_BTN
            wiimote.rpt_mode = rpt_mode
        elif c == 'c':
            wiimote.enable(cwiid.FLAG_MOTIONPLUS)
        elif c == 'e':
            rpt_mode ^= cwiid.RPT_EXT
            wiimote.rpt_mode = rpt_mode
        elif c == 'i':
            rpt_mode ^= cwiid.RPT_IR
            wiimote.rpt_mode = rpt_mode
        elif c == 'm':
            mesg = not mesg
            if mesg:
                wiimote.enable(cwiid.FLAG_MESG_IFC);
            else:
                wiimote.disable(cwiid.FLAG_MESG_IFC);
        elif c == 'p':
            print menu
        elif c == 'r':
            wiimote.request_status()
        elif c == 's':
            print_state(wiimote.state)
        elif c == 't':
            rpt_mode ^= cwiid.RPT_STATUS
            wiimote.rpt_mode = rpt_mode
        elif c == 'x':
            exit = -1;
        elif c == '\n':
            pass
        else:
            print 'invalid option'

    wiimote.close()

def print_state(state):
    #print 'Report Mode:',
    for r in ['STATUS', 'BTN', 'ACC', 'IR', 'NUNCHUK', 'CLASSIC']:
        if state['rpt_mode'] & eval('cwiid.RPT_' + r):
            pass
            #print r

    #print
    #print 'Active LEDs:',
    for led in ['1','2','3','4']:
        if state['led'] & eval('cwiid.LED' + led + '_ON'):
            print led,
    #print

    #print 'Rumble:', state['rumble'] and 'On' or 'Off'

    #print 'Battery:', int(100.0 * state['battery'] / cwiid.BATTERY_MAX)

    if 'buttons' in state:
        print 'Buttons:', state['buttons']

    if 'acc' in state:
        print 'Acc: x=%d y=%d z=%d' % (state['acc'][cwiid.X],
                                       state['acc'][cwiid.Y],
                                       state['acc'][cwiid.Z])

    if 'ir_src' in state:
        valid_src = False
        #print 'IR:',
        for src in state['ir_src']:
            if src:
                valid_src = True
                print src['pos'],
       #         w=csv.writer(open('distortion.csv', 'w'))
       #         w.writerow(src['pos'][0], src['pos'][1])

        if not valid_src:
            print 'no sources detected'
        else:
            print

    if state['ext_type'] == cwiid.EXT_NONE:
        pass
        #print 'No extension'
    elif state['ext_type'] == cwiid.EXT_UNKNOWN:
        print 'Unknown extension attached'
    elif state['ext_type'] == cwiid.EXT_NUNCHUK:
        if state.has_key('nunchuk'):
            print 'Nunchuk: btns=%.2X stick=%r acc.x=%d acc.y=%d acc.z=%d' % \
              (state['nunchuk']['buttons'], state['nunchuk']['stick'],
               state['nunchuk']['acc'][cwiid.X],
               state['nunchuk']['acc'][cwiid.Y],
               state['nunchuk']['acc'][cwiid.Z])
    elif state['ext_type'] == cwiid.EXT_CLASSIC:
        if state.has_key('classic'):
            print 'Classic: btns=%.4X l_stick=%r r_stick=%r l=%d r=%d' % \
              (state['classic']['buttons'],
               state['classic']['l_stick'], state['classic']['r_stick'],
               state['classic']['l'], state['classic']['r'])
    elif state['ext_type'] == cwiid.EXT_BALANCE:
        if state.has_key('balance'):
            print 'Balance: right_top=%d right_bottom=%d left_top=%d left_bottom=%d' % \
              (state['balance']['right_top'], state['balance']['right_bottom'],
               state['balance']['left_top'], state['balance']['left_bottom'])
    elif state['ext_type'] == cwiid.EXT_MOTIONPLUS:
        if state.has_key('motionplus'):
            print 'MotionPlus: angle_rate=(%d,%d,%d)' % state['motionplus']['angle_rate']

def callback(mesg_list, time):
    for mesg in mesg_list:

        if mesg[0] == cwiid.MESG_IR:
            valid_src = False
            
            for src in mesg[1]:
                if src:
                    valid_src = True              
                    print
                    print 'time: %f' % time
                    print 'x =' , src['pos'][0]
                    print 'y =' , src['pos'][1]

        elif mesg[0] ==  cwiid.MESG_ERROR:
            print "Error message received"
            global wiimote
            wiimote.close()
            exit(-1)
        else:
            #print 'Unknown Report'
            pass
main()
