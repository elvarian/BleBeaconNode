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

def mac_address(bytes):
    # bytes[13] ":" bytes[12] ":" bytes[11] ":" bytes[10] ":" bytes[9] ":" bytes[8]
    address = '{0}:{1}:{2}:{3}:{4}:{5}'.format(bytes[12], bytes[11],
                            bytes[10], bytes[9], bytes[8], bytes[7])
    return address

def packet_len(data, loc):
    return int(data[loc], 16)

def service(data):
    # Complete List of 16-Dit Service
    pass

def service_id(data):
    # Assigned Uri Service UUID
    # 0xFED8
    pass

def ad_length(data, loc):
    # Between 5 - 23
    return int(data[loc], 16)

def service_data(data):
    # 0x16
    pass

def service_id2(data):
    # Assigned Uri Service UUID
    # This one in ad content
    # 0xFED8
    pass

def uri_flags(data):
    # UriBeacons Flags
    pass

def tx_power(data, loc):
    # Reference power from beacon broadcast
    tx_power = int(data[26], 16)
    #print 'Tx Power: ' + str(tx_power)
    if tx_power & 0x80: # MSB set -> neg.
        return -((~tx_power & 0xff) + 1)
    else:
        return tx_power

def uri_scheme(data, loc):
    # Get UriBeacon Uri Scheme Prefix
    # 0x00 = http://www.
    # 0x01 = https://www.
    # 0x02 = http://
    # 0x03 = https://
    # 0x04 = urn:uuid:
    encode_scheme = {0: 'http://www.',
                     1: 'https://www.',
                     2: 'http://',
                     3: 'https://',
                     4: 'urn:uuid:'}
    return encode_scheme[int(data[loc + 6])]

def url_encoding(code):
    # UriBeacon HTTP URL encoding
    # 0 0x00  .com/
    # 1 0x01  .org/
    # 2 0x02  .edu/
    # 3 0x03  .net/
    # 4 0x04  .info/
    # 5 0x05  .biz/
    # 6 0x06  .gov/
    # 7 0x07  .com
    # 8 0x08  .org
    # 9 0x09  .edu
    # 10  0x0a  .net
    # 11  0x0b  .info
    # 12  0x0c  .biz
    # 13  0x0d  .gov
    encode_scheme = {0: '.com/',
                     1: '.org/',
                     2: '.edu/',
                     3: '.net/',
                     4: '.info/',
                     5: '.biz/',
                     6: '.gov/',
                     7: '.com',
                     8: '.org',
                     9: '.edu',
                     10: '.net',
                     11: '.info',
                     12: '.biz',
                     13: '.gov'}
    return encode_scheme[int(code)]

def encoded_uri(data, loc, length):
    start = loc + 7
    # Uri content
    val = ''
    for i in data[start:(start + length - 6)]:
        # print 'Encode: {0} - {1}'.format(i, chr(int(i, 16)))
        if int(i, 16) < 14:
            val = val + url_encoding(i)
        else:
            val = val + chr(int(i, 16))
    return val


def rssi_value(data):
    # Get recieve signal strength
    rssi = int(data[-1], 16)
    if rssi & 0x80: # MSB set -> neg.
        return -((~rssi & 0xff) + 1)
    else:
        return rssi

def pebblebee_button_data(data):
    button = int(data[-3], 16)
    return button

def has_uribeacon_service(data):
    return (data[14] == '03' and
            data[15] == '03' and
            data[16] == 'D8' and
            data[17] == 'FE')

def find_ad_start(data):
    #uri_service = ['80', '3B', '01', 'A0']
    #service_loc = [(i, i+len(uri_service)) for i in range(len(data)) if data[i:i+len(uri_service)] == uri_service]
    service_loc = [7, 11]
    return service_loc

def find_pebblebee_data(data):
    uribeacon = ['19', '00', '02', '02', '0A', '06', '09', 'FF']
    service_loc = [(i, i+len(uribeacon)) for i in range(len(data)) if data[i:i+len(uribeacon)] == uribeacon]
    return service_loc

def find_ruuvitag_data(data):
    ruuvitag = ['72', '75', '75', '2E', '76', '69', '2F', '23']
    service_loc = [(i, i+len(ruuvitag)) for i in range(len(data)) if data[i:i+len(ruuvitag)] == ruuvitag]
    return service_loc

def calc_range(rssi, txpower):
    # Alternative calculation to test, likely very similar answer!
    # rssi1m needs to be found with testing
    # Based on; http://matts-soup.blogspot.co.uk/2013/12/finding-distance-from-rssi.html

    #  Using zero for rssi1m as currently beacons are broadcasting value a 1m via txPower
    rssi1m = -40 #  tested
    path_loss = 2 #  free space
    if rssi > 0:
        rssi = 0
    #act_power = txpower + rssi1m
    act_power = -40
    pwr_loss = rssi - act_power
    num = -10 * path_loss
    den = float(pwr_loss) / float(num)
    raw_range = math.pow(10.0, den)
    return raw_range

def process_line(complete_line, sender):
    mydata = complete_line.split()

    if len(mydata) > 0:
        if mydata[0] == '>':
            del mydata[0]
            # print mydata[14]

        if len(find_pebblebee_data(mydata)) > 0:
            #if len(find_ad_start(mydata)) > 0:
      #print 'line: ' + complete_line
      #print 'mydata: ' + str(mydata)
            data_start = int(11)
      #print 'service_loc: ' + str(find_ad_start(mydata))
            #print mydata[-1]
            d_mac_address = mac_address(mydata)
            #print '  Address: {}'.format(d_mac_address)
            # print '  uri: {}{}'.format(uri_scheme(mydata, data_start),
            #                           encoded_uri(mydata, data_start, ad_length(mydata, data_start)))
            d_tx_power = tx_power(mydata, data_start)
            #print '  TX power: {}'.format(d_tx_power)
            d_rssi_value = rssi_value(mydata)
            #print '  RSSI: {}'.format(d_rssi_value)
      #distance = calc_range(d_rssi_value, d_tx_power)
            #print '  distance: {}'.format(distance)
            length = ad_length(mydata, data_start)
            #print '  Length: {}'.format(length)
            # fo.write( '{0},'.format(rssi_value(mydata)))
            #print '\n'

            button = pebblebee_button_data(mydata)

      #Device types:
      #0 = pebblebee
      #1 = ruuvitag
        if button == 0 or button == 1:
          device_data = {}
          device_data['device_type'] = 0
          device_data['mac_address'] = d_mac_address
          device_data['tx_power'] = d_tx_power
          device_data['rssi'] = d_rssi_value
        #device_data['distance'] = distance
        #device_data['length'] = length
          device_data['sender'] = sender
          device_addons = {}
          device_addons['button'] = button
          device_data['addons'] = device_addons
          device_data_json = json.dumps(device_data)
          print "Json: " + device_data_json
          return device_data_json
        elif len(find_ruuvitag_data(mydata)) > 0:
          data_start = int(11)
          d_mac_address = mac_address(mydata)
          d_tx_power = tx_power(mydata, data_start)
          d_rssi_value = rssi_value(mydata)

          device_data = {}
          device_data['device_type'] = 1
          device_data['mac_address'] = d_mac_address
          device_data['tx_power'] = d_tx_power
          device_data['rssi'] = d_rssi_value
          device_data['sender'] = sender
          device_data_json = json.dumps(device_data)
      #print 'Json: ' + device_data_json
      #print "ruuvitag not fully supported yet"
      #return device_data_json
    



def main():
    gotOK = 0
   # Open a file
   # fo = open("logging.txt", "wb")
    file_path = os.path.dirname(os.path.realpath(__file__))
    cmd = os.path.join(file_path, 'hcidump.sh')
    print cmd
    reader = subprocess.Popen(cmd,
                           shell=False,
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,
                           )

    line = ''
    cont_line = False
    sender = 0
    host = 'localhost'
    port = 1234

    print 'Usage: bleread.sh [options]'
    print 'Program to collect ble beacon data and send it to main server.'
    print '\t-s NUM\t\tsender NUM'
    print '\t-h 127.0.0.1\t\tIp address for server'
    print '\t-p 1234\t\tPort for server'

    for index in range(len(sys.argv)):
      if (sys.argv[index].startswith('-s') ):
        if (index +1 < len(sys.argv)):
          try:
            sender = int(sys.argv[index+1])
            #print 'sender: ' + str(sender)
          except:
            print 'Invalid argument for sender. Must be integer'
            sys.exit()
      if (sys.argv[index].startswith('-h') ):
        if (index +1 < len(sys.arg)):
          try:
            host = str(sys.argv[index+1])
          except:
            print 'Invalid argument for host.'
            sys.exit()
      if (sys.argv[index].startswith('-p') ):
        if (index +1 < len(sys.arg)):
          try:
            port = int(sys.argv[index+1])
          except:
            print 'Invalid argument for port. Must be integer'
            sys.exit()

    print 'Sending to ip:port ' + host + ':' + str(port)
    print 'Sender: ' + str(sender)
    print 'start'

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
           
          print 'line: ' + line
          json = process_line(line, sender)
          if json != None:
            try:
              s.sendto(json, (host, port))
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


