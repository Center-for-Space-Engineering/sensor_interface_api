import random
import time
from datetime import datetime, timedelta
import math
import numpy as np
import threading
import copy

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
import system_constants as sensor_config # pylint: disable=e0401
from logging_system_display_python_api.DTOs.print_message_dto import print_message_dto # pylint: disable=e0401

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
            temp = sensor_parent.preprocess_data(self, sensor_parent.get_data_received(self, self.__config['tap_request'][0]), delimiter=self.__config['Sensor_data_tag']) #add the received data to the list of data we have received.
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
        
        sensor_parent.set_thread_status(self, 'Running')
        with self.__data_lock: #get the data out of the data storage. 
            temp_data_structure = copy.deepcopy(self.__serial_line_two_data[:num_packets])

        parsestr = '$GPRMC'
        leapSeconds = 37 - 19
        packet_terminator = '\r\n'
        counter = 0

        processed_packets = 0

        for packet in temp_data_structure:
            try :
                packet = packet.decode('utf-8') #Turn our byte object into a string
                if parsestr in packet and packet_terminator in packet:
                    print('Here')

                    parsedRString = packet.split(',')
                    # print(parsedRString)

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
                    # print (dataPacket)

                    counter+=1
                    processed_packets += 1

                if packet_terminator in packet:
                    processed_packets += 1
            except :
                #bad packet 
                dto = print_message_dto(f'Bad packet received. For {self.__name}')
                self.__coms.print_message(dto, 2)
                processed_packets += 1
        with self.__data_lock: #update the list with unprocessed packets. 
            self.__serial_line_two_data = self.__serial_line_two_data[processed_packets:]
        sensor_parent.set_thread_status(self, 'Complete')

    def crc16(data : bytearray, offset , length):
        if data is None or offset < 0 or offset > len(data)- 1 and offset+length > len(data):
            return 0
        crc = 0xFFFF
        for i in range(0, length):
            crc ^= data[offset + i] << 8
            for j in range(0,8):
                if (crc & 0x8000) > 0:
                    crc =(crc << 1) ^ 0x1021
                else:
                    crc = crc << 1
        return crc & 0xFFFF
    
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
        #APID is whatever the heck you want
        headerAPID = 276
        #this is the "11" (decimal 3) meaning the data is not broken into multiple packets
        headerSequence = 3
        #ome command packet has a byte of data and two of checksum, offset = 8-1 = 7
        headerDataLength = 7

        headerFlag = headerFlag << 3
        headerType = headerType << 4
        headerVersion = headerVersion << 5
        ccsdsLinex00 =  hex(headerAPID >> 8 | headerFlag | headerType | headerVersion)
        ccsdsLinex01 =  hex(headerAPID & 0xFF)

        headerSequence = headerSequence << 6
        ccsdsLinex02 = hex(headerPacketCount >> 8| headerSequence)
        ccsdsLinex03 = hex(headerPacketCount & 0xFF)

        ccsdsLinex04 = hex(headerDataLength >> 8)
        ccsdsLinex05 = hex(headerDataLength & 0xFF)
        
        #print('ccsdsLinex00--------')
        ccsdsPacket = ccsdsLinex00 << (13 * 8)
        ccsdsPacket |= ccsdsLinex01 << (12 * 8)
        ccsdsPacket |= ccsdsLinex02 << (11 * 8)
        ccsdsPacket |= ccsdsLinex03 << (10 * 8)
        ccsdsPacket |= ccsdsLinex04 << (9 * 8)
        ccsdsPacket |= ccsdsLinex05 << (8 * 8)
        
        # convert week and mseconds
        ccsdsPacket |= ((week&0xff00) << (6 * 8)) # NOTE:   Because we got the top 8 bits we only shift by 6.
        ccsdsPacket |= ((week&0x00ff) << (6 * 8))

        ccsdsPacket |= ((mseconds&0xff000000) << (2 * 8)) # NOTE:   Because we got the top 8 bits we only shift by 2.
        ccsdsPacket |= ((mseconds&0x00ff0000) << (2 * 8))
        ccsdsPacket |= ((mseconds&0x0000ff00) << (2 * 8))
        ccsdsPacket |= ((mseconds&0x000000ff) << (2 * 8))

        checksum_pack = list(hex(ccsdsPacket >> (2 * 8), 11))


        checksum = (self.crc16(checksum_pack,0, len(checksum_pack)))
        ccsdsPacket |= ((checksum&0xff00))
        ccsdsPacket |= ((checksum&0x00ff))

        print(ccsdsPacket)
        

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
