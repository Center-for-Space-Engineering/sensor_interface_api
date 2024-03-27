import random
import time
from datetime import datetime, timedelta
import math
import numpy as np
import threading
import copy

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
from threading_python_api.threadWrapper import threadWrapper # pylint: disable=e0401
from sensor_interface_api import system_constants as sensor_config # pylint: disable=e0401

class sobj_gps_board(sensor_parent):
    def __init__(self, coms):
        self.__name = 'gps_board'
        self.__graphs = ['num gps packets received']
        self.__config = sensor_config.sensors_config[self.__name]
        self.__serial_line_two_data = []
        self.__data_lock = threading.Lock()
        self.__coms = coms

        # the structure here is a dict where the key is the name of the table you want to make and the value is a list of list that has your row information on each sub index.
        # the row structure is [<table name>, bit count (zero if you dont care), type (int, float, string, bool, bigint, byte)]
        self.__table_structure = {
            f'processed_data_for_{self.__name}' : [['gps_packets', 0, 'string'], ['test_data', 10, 'int']],
            f'processed_data_for_{self.__name}_table_2' : [['gps_packets', 0, 'string'], ['test_data', 10, 'int']],

        }

        # NOTE: if you change the table_structure, you need to clear the database/dataTypes.dtobj and database/dataTypes_backup.dtobj DO NOT delete the file, just delete everything in side the file.
        sensor_parent.__init__(self, coms=coms, config= self.__config, name=self.__name, graphs=self.__graphs, max_data_points=100, db_name = sensor_config.database_name, table_structure=self.__table_structure)
        sensor_parent.set_sensor_status(self, 'Running')
    def process_data(self, event):
        '''
            This function gets called when one of the tap request gets any data. 

            NOTE: This function always gets called no matter with tap gets data. 
        '''
        # y = [random.random() for _ in range(100)]
        # x = [i for i in range(100)] 
        # sensor_parent.add_graph_data(self, graph=self.__graphs[0], x=x, y=y)
        # data = [[1,2,3], [4,5,6]]
        # sensor_parent.set_publish_data(self, data=data)
        # sensor_parent.publish(self)
        # print(f'Event called: {event}')
        # print(sensor_parent.get_data_received(self, self.__config['tap_request'][0]))
        # data = {
        #     'gps_packets' : ['hello', 'hello'],
        #     'test_data' : [10, 10]
        # }
        # sensor_parent.save_data(self, table = f'processed_data_for_{self.__name}', data = data)
        if event == 'data_received_for_serial_listener_two':
            temp = sensor_parent.preprocess_data(self, sensor_parent.get_data_received(self, self.__config['tap_request'][0]), delimiter=b'$') #add the received data to the list of data we have received.
            with self.__data_lock:
                if len(self.__serial_line_two_data) > 0: 
                    self.__serial_line_two_data[-1] += temp[0] #append the message to the previous message (this is because partial message can be included in batches, so we are basically adding the partial messages to gether, across batches. )
                    self.__serial_line_two_data += temp[1:]
                else :
                    self.__serial_line_two_data += temp
                self.__coms.send_request('task_handler', ['add_thread_request_func', self.process_gps_packets, f'processing data for {self.__name} for event data_received_for_serial_listener_two', self, [len(self.__serial_line_two_data)]]) #start a thread to process data
    def process_gps_packets(self, num_packets):
        '''
            This function rips apart gps packets and then saves them in the data base as ccsds packets.  
        '''
        with self.__data_lock: #get the data out of the data storage. 
            temp_data_structure = copy.deepcopy(self.__serial_line_two_data[:num_packets])

        parsestr = '$GPRMC'
        leapSeconds = 37 - 19
        packet_terminator = '\r\n'
        counter = 0

        processed_packets = 0

        for packet in temp_data_structure:
            packet = packet.decode('utf-8') #Turn our byte object into a string
            if parsestr in packet and packet_terminator in packet:
                parsedRString = packet.split(',')
                print(parsedRString)

                t = self.split_by_length(parsedRString[1],2)
                hour = int(t[0])
                minute = int(t[1])
                second = int(t[2])
                
                d = self.split_by_length(parsedRString[9],2)
                day = int(d[0])
                month = int(d[1])
                year = int(d[2])
            
                
                results = self.gpsFromUTC(year,month,day,hour,minute,second, leapSeconds)

                gpsWeek = results[0]
                gps_MSOW = int(results[1] * 1000)
                
                dataPacket = self.makePacket(gpsWeek, gps_MSOW, counter)
                print (dataPacket)

                counter+=1
                processed_packets += 1

            if packet_terminator in packet:
                processed_packets += 1
        with self.__data_lock: #update the list with unprocessed packets. 
            self.__serial_line_two_data = self.__serial_line_two_data[processed_packets:]
    def fletcher16(self, data, packet_length):
        '''
            Checksum algro 
        '''
        sum1 = 0
        sum2 = 0

        for byte in range(packet_length-2):
            sum1 = (sum1+data[byte])%255
            sum2 = (sum1 + sum2)%255

        return [sum1,sum2]
    def makePacket(self, week, mseconds, packetNumber):
        '''
            This makes a ccsds packet from the give args. (returns byte array)
            
            TODO: add sync word
        '''
        byteList = []

        
        #Create Header

        headerPacketCount = packetNumber

        #current version is "000"
        headerVersion = 0 
        #1 is command, 0 is telemetry
        headerType = 1
        #1 says there is a secondary header
        headerFlag = 0
        #APID is whatever the heck yo uwant
        headerAPID = 321
        #this is the "11" (decimal 3) meaning the data is not broken into multiple packets
        headerSequence = 3
        #ome command packet has a byte of data and two of checksum, offset = 8-1 = 7
        headerDataLength = 7

        headerFlag = headerFlag << 11
        headerType = headerType << 12
        headerVersion = headerVersion << 13
        ccsdsLinex00 =  hex(headerAPID | headerFlag | headerType | headerVersion)

        headerSequence = headerSequence << 14
        ccsdsLinex02 = hex(headerPacketCount | headerSequence)

        ccsdsLinex04 = hex(headerDataLength)
        
        #print('ccsdsLinex00--------')
        #print ccsdsLinex00
        maskapid=0xFF
        byteList.append(int(ccsdsLinex00,16)&maskapid)
        byteList.append(int(ccsdsLinex00,16)>>8)
        #print('ccsdsLinex02--------')
        #print ccsdsLinex02
        byteList.append(int(ccsdsLinex02,16)&maskapid)
        byteList.append(int(ccsdsLinex02,16)>>8)
        #print('ccsdsLinex04--------')
        #print ccsdsLinex04
        byteList.append(int(ccsdsLinex04,16)&maskapid)
        byteList.append(int(ccsdsLinex04,16)>>8)


        # convert week and mseconds

        #print(week)
        byteList.append(week&maskapid)
        byteList.append(week>>8)
        

        #print(mseconds)
        byteList.append(mseconds&maskapid)
        byteList.append((mseconds>>8)&maskapid)
        byteList.append((mseconds>>16)&maskapid)
        byteList.append(mseconds>>24)


        checksum = (self.fletcher16(byteList,14))
        byteList.append(checksum[0])
        byteList.append(checksum[1])

        return(byteList)
    def split_by_length(self, s,block_size):
        '''
            split the data. Pulling out the data and time (UTC) from gps sentence. 
        '''
        w=[]
        n=len(s)
        for i in range(0,n,block_size):
            w.append(s[i:i+block_size])
        return w
    def gpsFromUTC(self, year, month, day, hour, minute, sec, leapSecs):
        '''
            Get the gps data from UTC time.
        '''
        secsInWeek = 604800
        secsInDay = 86400
        gpsEpoch = (1980, 1, 6, 0, 0, 0)


        secFract = sec % 1
        epochTuple = gpsEpoch + (-1, -1, 0)
        t0 = time.mktime(epochTuple)
        t = time.mktime((year,month,day,hour,minute,sec,-1,-1,0))
        t = t + leapSecs
        tdiff = t - t0
        gpsSOW = (tdiff % secsInWeek) + secFract
        gpsWeek = int(math.floor(tdiff/secsInWeek))
        gpsDay = int(math.floor(gpsSOW/secsInDay))
        gpsSOD = (gpsSOW%secsInDay)
        return(gpsWeek,gpsSOW,gpsDay,gpsSOD)
