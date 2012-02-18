# baron 0.1 2/17/12
# davidme - initial version, properly does stuff
#
# requires PySerial
# 
# automatically reloads CODES_PATH every CODES_RELOAD_TIME seconds - will log error
# and keep old code list if there are any issues. we may want this to respond
# to a specific signal instead. please don't just restart the process to refresh.
# 

CODES_RELOAD_TIME = 10
CODES_PATH = 'codes.txt'
SERIAL_PORT = '/dev/ttyS0'

import threading, time, signal, sys, serial
codes = []

def door_loop():
    global codes
    while True:
        print "Waiting for door"
        try:
            keypad = serial.Serial(SERIAL_PORT, 9600, bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,     
                    stopbits=serial.STOPBITS_ONE, 
                    timeout=60, # restart this whole thing every 60 seconds, in case something is confused
                    xonxoff=0,              
                    rtscts=0,
                    interCharTimeout=None,
                    writeTimeout=10) #writes should never timeout, but just in case...
            digits = keypad.read(1)
            if digits.isdigit():
                keypad.timeout=5 #give 5 seconds after last input
                while len(digits) < 7 and digits not in codes:
                    print digits
                    new_digit = keypad.read(1)
                    if new_digit.isdigit():
                        digits += new_digit
                if digits in codes:
                    try:
                        subprocess.call('curl -fX POST -d open=True http://api.noisebridge.net/gate/')
                        print "success, door opening"
                        keypad.write('G') #green led
                        keypad.write('H') #happy sound!                                                
                    except CalledProcessError:
                        print "error with the door API"
                        keypad.write('S') #sad sound :(
                        keypad.write('R') #red led
                        time.sleep(0.2)
                        keypad.write('Q') #red led
                        keypad.write('S') #sad sound :(
                        keypad.write('R') #red led
                        time.sleep(0.2)
                        keypad.write('Q') #red led
                        keypad.write('S') #sad sound :(
                        keypad.write('R') #red led
                    print "success, door opening"
                    keypad.write('G') #green led
                    keypad.write('H') #happy sound!
                else:
                    keypad.write('S') #sad sound :(
                    keypad.write('R') #red led
        except: #gotta catch 'em all
            print "Unknown keypad exception, restarting: ", sys.exc_info()[0]
            time.sleep(5)

def reload_loop():
    global codes
    while True:
        time.sleep(CODES_RELOAD_TIME) #reload 
        new_codes = load_codes()
        if new_codes:
            codes = new_codes

def load_codes():
    try:
        # file format: all lines starting with a 4 digit or greater number,
        # ignoring whitespace. anything after # is ignored.
        new_codes = []
        f = open(CODES_PATH, 'r')
        for line in f:
            line = line.split('#', 1)[0] # ignore comments, delineated by #
            entry = line.split(' ', 1)[0]
            if entry.isdigit() and len(entry) >= 4:
                new_codes.append(entry)
        return new_codes
    except:
        print "Retaining old code list, unknown error: ", sys.exc_info()[0]
        return None

new_codes = load_codes()
if new_codes is None:
    print "No codes available"
    sys.exit()
codes = new_codes
door_thread = threading.Thread(target=door_loop)
reload_thread = threading.Thread(target=reload_loop)
door_thread.start()
reload_thread.start()
print "Baron is running"