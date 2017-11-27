#!/usr/bin/python
"""
Example line from hcidump.
> 04 3E 21 02 01 00 00   E3 E3 03 5B 02 00   15 02 01   1A   03   03   D8
  FE   0D   16   D8 FE   00   14   02   63 73 72 2E 63 6F 6D A7
  
Looking at:
https://github.com/AltBeacon/spec
And more importantly:
https://github.com/google/uribeacon/blob/master/specification/AdvertisingMode.md

The data can be broken up as follows:
preamble: 04
Access Address: 3E 21 02 01
PDU Header: 00 00
Adv Address: E3 E3 03 5B 02 00
Ad Flags: 15 02 01
???: 1A (Decimal 26)
Ad Length: 03
Ad Type (Service UUID's): 03
Service UUID: FE D8
Ad Lenght: 0D (decimal 13)
Ad Type (Service data): 16
Service UUID: FE D8
Flags: 00
Calibrated Tx Power: 14 (decimal 20)
Uri Scheme Prefix: 02 (maps to 'http://')
Encoded Uri: 63 73 72 2E 63 6F 6D (csr.com)
RSSI: A7 (deciaml -89)

"""

import re
import subprocess
import math
import os
import sys

import numpy as np
import json
import socket
import struct
import codecs
import binascii

def process_line(complete_line, sender):
    
    print 'complete line: ' + complete_line

    line = complete_line.strip()
    line = line.replace('>', '')
    line = line.replace(' ', '')

    print 'Line: ' + line

    mydata = bytes.fromhex(line)

    #print('unhexlify line: ')
    print(mydata)

    #if len(mydata) > 0:
    #    if mydata[0] == '>':
    #       del mydata[0]
           

    #msg = []         
    #msg = struct.pack('H', len(sender))
    #print 'Sender length: ' + str(len(sender))
    senderLengthBytes = struct.pack('H', len(sender))
    #print 'SenderBytes: ' + str(senderLengthBytes)
    #msg = codecs.decode(senderBytes, 'hex_codec')
    msg = str(senderLengthBytes)

    senderBytes = struct.pack('=' + str(len(sender)) +'s', sender)

    #print 'SenderBytes: ' + str(senderBytes)

    msg = msg + str(senderBytes)

    print 'mydata len: ' + str(len(mydata))

    dataLengthBytes = struct.pack('H', len(mydata))

    msg = msg + str(dataLengthBytes)

    #for index in range(len(mydata)):
    #  msg = msg + b'\x' + str(mydata[index])

    msg = msg + mydata

    #print 'msg: ' + str(msg)
    #msg = msg + sender
    #msg = msg + str(len(mydata))
    #for index in range(len(mydata)):
    #  msg = msg + '\x' + str(mydata[index])

    #hci_data = {}
    #hci_data['sender'] = sender
    #hci_data['data'] = complete_line
    #hci_data_json = json.dumps(hci_data)
    #print msg
    return msg
        
            
def main():
    gotOK = 0
    line = ''
    cont_line = False
    sender = ''
    host = 'localhost'
    port = 1234

    print 'Usage: bleread.sh [options]'
    print 'Program to collect ble beacon data and send it to main server.'
    print '\t-h 127.0.0.1\t\t\tIp address for server'
    print '\t-p 1234\t\t\tPort for server'

    for index in range(len(sys.argv)):
      if (sys.argv[index].startswith('-h') ):
        if (index +1 < len(sys.argv)):
          try:
            host = str(sys.argv[index+1])
          except:
            print 'Invalid argument for host.'
            sys.exit()
      if (sys.argv[index].startswith('-p') ):
        if (index +1 < len(sys.argv)):
          try:
            port = int(sys.argv[index+1])
          except:
            print 'Invalid argument for port. Must be integer'
            sys.exit()

    hcitool = subprocess.Popen(['hcitool', 'dev'], shell=False,stdout=subprocess.PIPE)
    
    while True:
      hcitoolLine = hcitool.stdout.readline()
      if(hcitoolLine != ''):
        #print hcitoolLine
        if(hcitoolLine.strip().startswith('hci')):
          deviceList = hcitoolLine.strip().split('\t')
          if(len(deviceList) == 2):
            sender = deviceList[1]
            break
      else:
        break
    
    if(sender == ''):
      print 'Error getting sender information from hcitool.'
      sys.exit()

    print 'Sending to ip:port ' + host + ':' + str(port)
    print 'Sender: ' + str(sender)
    print 'start'

    file_path = os.path.dirname(os.path.realpath(__file__))
    cmd = os.path.join(file_path, 'hcidump.sh')
    #print cmd
    reader = subprocess.Popen(cmd,
                           shell=False,
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,
                           )


    try:
      s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error:
      print 'Failed to create socket.'
      sys.exit()

    while gotOK < 50:
       reply = reader.stdout.readline()
       #print "reply:%s" % reply
       if re.match("^>.*$", reply):
           #process last line
           
          #print 'line: ' + line
          msg = process_line(line, sender)

          #msg = 

          if msg != None:
            try:
              s.sendto(msg, (host, port))
            except socket.error, msg:
              print 'Error code : ' + str(msg[0]) + ' Message ' + msg[1]
              sys.exit()
           
          line = reply.strip()
          cont_line = True
           #print 'start line: ' + line
           #gotOK += 1
          gotOK = 1
       elif re.match("^\s\s\w.*$", reply):
          header = line[:49].strip();
          linedata = line[49:].strip();
          line = line.strip() + " " + reply.strip()
          printline = header + " : " + linedata + " " + reply.strip()
           #print 'line now: ' + line
     #print 'line now: ' + printline
     #print 'line header: ' + header

    print 'end'




if __name__ == '__main__':
    try:
        main()

    except KeyboardInterrupt:
        print '\nInterrupt caught'

    finally:
        # Close opend file
        # fo.close()
        pass


