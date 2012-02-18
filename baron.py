# baron 0.1 2/17/12
# davidme
# 
# requires python-serial (PySerial) library
# 
# automatically reloads CODES_PATH every CODES_RELOAD_TIME seconds - will log error
# and keep old code list if there are any issues. we may want this to respond
# to a specific "reload" signal instead. please don't just restart the process to refresh.
# 

CODES_RELOAD_TIME = 10 # seconds

import threading, time, signal, sys, socket
from optparse import OptionParser
import serial
import daemon

codes = []
codes_path = ''
serial_path = ''

def chat_with_gate(message): #stolen from NB api
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    port = 30012
    try:
        s.connect(('minotaur.noise', port))
    except socket.error:
        return "Failed: Could not connect"
    data = message
    s.sendall(data)
    s.shutdown(1)
    s.settimeout(5)
    try:
        buf = s.recv(2048)
    except socket.timeout:
        buf = "Failed: No response"
    return buf

def door_loop():
    global codes, codes_path, serial_path
    while True:
        print "Waiting for input from keypad"
        try:
            keypad = serial.Serial(serial_path, 300, bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,     
                    stopbits=serial.STOPBITS_ONE, 
                    timeout=60, # restart this whole thing every 60 seconds, in case something is confused
                    xonxoff=0,              
                    rtscts=0,
                    writeTimeout=10) #writes should never timeout, but just in case...
            digits = keypad.read(1)
            if digits.isdigit():
                keypad.timeout=5 #give 5 seconds after last input
                while len(digits) < 7 and digits not in codes:
                    print "entered: " + digits
                    new_digit = keypad.read(1)
                    if new_digit.isdigit():
                        digits += new_digit
                    else: # they hit #, *, or we timed out
                        break
                if digits in codes:
                    gate_message = chat_with_gate("OPEN!")
                    if 'Acknowledged' in gate_message:                        
                        print "success, gate opening"
                        keypad.write('GH') #green led, happy sound
                    else:
                        print "error with the gate: " + gate_message
                        keypad.write('SR') #sad sound, red led
                        time.sleep(0.2)
                        keypad.write('QSR') #quiet, sad sound, red led
                        time.sleep(0.2)
                        keypad.write('QSR') #quiet, sad sound, red led
                else:
                    keypad.write('SR') #sad sound, red led
                    print "invalid code, gate not opening"
        except serial.serialutil.SerialException as err:
            print "Failed to connect to serial port " + serial_path
            time.sleep(5)
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
        f = open(codes_path, 'r')
        for line in f:
            line = line.split('#', 1)[0] # ignore comments, delineated by #
            entry = line.split(' ', 1)[0]
            if entry.isdigit() and len(entry) >= 4:
                new_codes.append(entry)
        return new_codes
    except:
        print "Retaining old code list, unknown error: ", sys.exc_info()[0]
        return None

with daemon.DaemonContext():
    parser = OptionParser()
    parser.add_option('-p', '--port', default='/dev/pts/0', dest='port',
                      help='a serial port to communicate with')
    parser.add_option('-c', '--codefile', default='codes.txt', dest='codefile',
                      help='a file containing a list of valid code numbers, separated by carriage returns.')
    (options, args) = parser.parse_args()
    serial_path = options.port
    codes_path = options.codefile
    print "Starting Baron..."                   
    reload_thread = threading.Thread(target=reload_loop)
    door_thread = threading.Thread(target=door_loop)
    reload_thread.start()
    door_thread.start()
