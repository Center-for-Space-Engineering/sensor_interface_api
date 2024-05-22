'''
    This module handles the incoming data from the gps board, process it and then makes a packet and publishes the gps time packet.
'''
import threading
import copy
import datetime

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
import system_constants as sensor_config # pylint: disable=e0401
from logging_system_display_python_api.DTOs.print_message_dto import print_message_dto # pylint: disable=e0401

class sobj_packet_detect(sensor_parent):
    '''
        This models counts the number of each type of packet recieved.
    '''
    def __init__(self, coms):
        self.__name = 'packet_detect'
        self.__config = sensor_config.sensors_config[self.__name]
        self.__serial_line_two_data = []
        self.__data_lock = threading.Lock()
        self.__coms = coms
        self.__packet_number = 0
        self.__packet_number_lock = threading.Lock()

        self.__telemetry_packet_type_num = 17
        self.__packet_count = [0] * self.__telemetry_packet_type_num
        self.__bad_crc_count = 0
        self.__unknown_apid_count = 0

        self.__telemetry_packet_types = ['STT', 'FPP1', 'FPP2', 'FPP3', 'FPP4', 'FBP', 'SLP', 'FLP', 'TAM', 'SIP', 'TIP', 'QIP', 'PDS', 'EFS1', 'EFS2', 'EFS3', 'ECO']

        self.__start_time = datetime.datetime.now()


        # the structure here is a dict where the key is the name of the table you want to make and the value is a list of list that has your row information on each sub index.
        # the row structure is [<table name>, bit count (zero if you dont care), type (int, float, string, bool, bigint, byte)]
        self.__table_structure = {
            f'processed_data_for_{self.__name}_counts' : [['time', 0, 'string'], ['STT', 0, 'int'], ['FPP1', 0, 'int'], ['FPP2', 0, 'int'], ['FPP3', 0, 'int'], ['FPP4', 0, 'int'], ['FBP', 0, 'int'], ['SLP', 0, 'int'], ['FLP', 0, 'int'], ['TAM', 0, 'int'], ['SIP', 0, 'int'], ['TIP', 0, 'int'], ['QIP', 0, 'int'], ['PDS', 0, 'int'], ['EFS1', 0, 'int'], ['EFS2', 0, 'int'], ['EFS3', 0, 'int'], ['ECO', 0, 'int'], ['Ukwn', 0, 'int'], ['bad_crc', 0, 'int']],
            f'processed_data_for_{self.__name}_rates' : [['time', 0, 'string'], ['STT', 0, 'float'], ['FPP1', 0, 'float'], ['FPP2', 0, 'float'], ['FPP3', 0, 'float'], ['FPP4', 0, 'float'], ['FBP', 0, 'float'], ['SLP', 0, 'float'], ['FLP', 0, 'float'], ['TAM', 0, 'float'], ['SIP', 0, 'float'], ['TIP', 0, 'float'], ['QIP', 0, 'float'], ['PDS', 0, 'float'], ['EFS1', 0, 'float'], ['EFS2', 0, 'float'], ['EFS3', 0, 'float'], ['ECO', 0, 'float'], ['Ukwn', 0, 'float'], ['bad_crc', 0, 'float']],
        }

        # NOTE: if you change the table_structure, you need to clear the database/dataTypes.dtobj and database/dataTypes_backup.dtobj DO NOT delete the file, just delete everything in side the file.
        sensor_parent.__init__(self, coms=coms, config= self.__config, name=self.__name, max_data_points=00, db_name = sensor_config.database_name, table_structure=self.__table_structure)
        sensor_parent.set_sensor_status(self, 'Running')
    def process_data(self, event):
        '''
            This function gets called when one of the tap request gets any data. 

            NOTE: This function always gets called no matter with tap gets data. 
        '''
        # print(event)
        if event == 'data_received_for_serial_listener_two':
            # print("event entered")
            temp, bad_packet_detected = sensor_parent.preprocess_ccsds_data(self, sensor_parent.get_data_received(self, self.__config['tap_request'][0])) #add the received data to the list of data we have received.
            with self.__data_lock:
                # if start_partial and len(self.__serial_line_two_data) > 0: 
                #     self.__serial_line_two_data[-1] += temp[0] #append the message to the previous message (this is because partial message can be included in batches, so we are basically adding the partial messages to gether, across batches. )
                #     self.__serial_line_two_data += temp[1:]
                # else :
                self.__serial_line_two_data += temp
                # data_ready_for_processing = len(self.__serial_line_two_data) if not end_partial else len(self.__serial_line_two_data) - 1 #if the last packet is a partial pack then we are not going to process it.
                data_ready_for_processing =  len(self.__serial_line_two_data) #if the last packet is a partial pack then we are not going to process it.
                self.__coms.send_request('task_handler', ['add_thread_request_func', self.process_count_packets, f'processing data for {self.__name} ', self, [data_ready_for_processing]]) #start a thread to process data
    def process_count_packets(self, num_packets):
        '''
            This function rips apart telemetry packets and counts how many of each type there is.  
        '''
        print("starting processing")
        sensor_parent.set_thread_status(self, 'Running')
        with self.__data_lock: #get the data out of the data storage. 
            temp_data_structure = copy.deepcopy(self.__serial_line_two_data[:num_packets])

        # data to publish
        data = {key: [] for key in self.__telemetry_packet_types}

        # print("sample: ", temp_data_structure)
        # print("number of packets in sample: ", len(temp_data_structure))
        for packet in temp_data_structure:
            APID = int.from_bytes(packet[:2], 'big') & 0x07ff
            # case statement
            if 0x0010 <= APID <= 0x0020:                                                # STT to ECO packets
                if self.ccsds_crc16(packet) == 0x00:                                    # valid crc
                    self.__packet_count[APID - 0x0010] += 1                             # increment the appropriate packet count
                    data[self.__telemetry_packet_types[APID - 0x0010]].append(packet)   # add packet to list in data dictionary for publishing
                else:                                                                   # invalid crc
                    self.__bad_crc_count += 1
                    # print("packet w/ bad crc: ", packet)
                    # print("packet w/ bad crc: ", packet)
                    # print("packet length:", int.from_bytes(packet[4:6], 'big'))
                    # print("packet crc:", packet[-2:])
            else:                                                                       # Unknown packet
                self.__unknown_apid_count += 1

        current_time = datetime.datetime.now()
        elapsed_seconds = (current_time - self.__start_time).total_seconds()
        
        # Create data to save to the database
        save_data = {
            'time' : current_time,
            'STT' : self.__packet_count[0],
            'FPP1' : self.__packet_count[1],
            'FPP2' : self.__packet_count[2],
            'FPP3' : self.__packet_count[3],
            'FPP4' : self.__packet_count[4],
            'FBP' : self.__packet_count[5],
            'SLP' : self.__packet_count[6],
            'FLP' : self.__packet_count[7],
            'TAM' : self.__packet_count[8],
            'SIP' : self.__packet_count[9],
            'TIP' : self.__packet_count[10],
            'QIP' : self.__packet_count[11],
            'PDS' : self.__packet_count[12],
            'EFS1' : self.__packet_count[13],
            'EFS2' : self.__packet_count[14],
            'EFS3' : self.__packet_count[15],
            'ECO' : self.__packet_count[16],
            'Ukwn' : self.__unknown_apid_count,
            'bad_crc' : self.__bad_crc_count
        }
        #save counts
        sensor_parent.save_data(self, table=f'processed_data_for_{self.__name}_counts', data=save_data)

        print("count dict: ", save_data)

        # Create data to save to the database
        save_data = {
            'time' : current_time,
            'STT' : self.__packet_count[0]/elapsed_seconds,
            'FPP1' : self.__packet_count[1]/elapsed_seconds,
            'FPP2' : self.__packet_count[2]/elapsed_seconds,
            'FPP3' : self.__packet_count[3]/elapsed_seconds,
            'FPP4' : self.__packet_count[4]/elapsed_seconds,
            'FBP' : self.__packet_count[5]/elapsed_seconds,
            'SLP' : self.__packet_count[6]/elapsed_seconds,
            'FLP' : self.__packet_count[7]/elapsed_seconds,
            'TAM' : self.__packet_count[8]/elapsed_seconds,
            'SIP' : self.__packet_count[9]/elapsed_seconds,
            'TIP' : self.__packet_count[10]/elapsed_seconds,
            'QIP' : self.__packet_count[11]/elapsed_seconds,
            'PDS' : self.__packet_count[12]/elapsed_seconds,
            'EFS1' : self.__packet_count[13]/elapsed_seconds,
            'EFS2' : self.__packet_count[14]/elapsed_seconds,
            'EFS3' : self.__packet_count[15]/elapsed_seconds,
            'ECO' : self.__packet_count[16]/elapsed_seconds,
            'Ukwn' : self.__unknown_apid_count/elapsed_seconds,
            'bad_crc' : self.__bad_crc_count/elapsed_seconds
        }
        #save rate data
        sensor_parent.save_data(self, table=f'processed_data_for_{self.__name}_rates', data=save_data)

        print("rate dict: ", save_data)


        #now we need to publish the data NOTE: remember we are a passive sensor. 
        sensor_parent.set_publish_data(self, data=data)
        sensor_parent.publish(self)

        
        with self.__data_lock: #update the list with unprocessed packets. 
            self.__serial_line_two_data = self.__serial_line_two_data[num_packets:]

        sensor_parent.set_thread_status(self, 'Complete')
    def crc16(self, data : bytearray, offset , length):
        '''
            Make check sum for the packet.
        '''
        if data is None or offset < 0 or offset > len(data)- 1 and offset+length > len(data):
            return 0
        crc = 0xFFFF
        for i in range(0, length):
            crc ^= data[offset + i] << 8
            for _ in range(0,8):
                if (crc & 0x8000) > 0:
                    crc =(crc << 1) ^ 0x1021
                else:
                    crc = crc << 1
        return crc & 0xFFFF 
    def ccsds_crc16(self, data : bytearray):
        '''
            Make crc16/CCITT-FALSE check sum for the CCSDS packet.
        '''
        if data is None:
            return 0
        crc = 0xFFFF
        poly = 0x1021


        for byte in data:
            crc ^= byte << 8
            for _ in range(0,8):
                if (crc & 0x8000):
                    crc = (crc << 1) ^ poly
                else:
                    crc = crc << 1
        return crc & 0xFFFF 
    def makePacket(self, week, mseconds, packetNumber):
        '''
            This makes a ccsds packet from the give args. (returns byte array)
            
            TODO: add sync word
        '''
        
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
        ccsdsLinex00 =  headerAPID >> 8 | headerFlag | headerType | headerVersion
        ccsdsLinex01 =  headerAPID & 0xFF

        headerSequence = headerSequence << 6
        ccsdsLinex02 = headerPacketCount >> 8| headerSequence
        ccsdsLinex03 = headerPacketCount & 0xFF

        ccsdsLinex04 = headerDataLength >> 8
        ccsdsLinex05 = headerDataLength & 0xFF
        
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

        # checksum_pack = list(hex(ccsdsPacket >> (2 * 8), 11))
        # Convert the integer to a byte array
        checksum_pack = ccsdsPacket.to_bytes((ccsdsPacket.bit_length() + 7) // 8, 'big')

        checksum = (self.crc16(checksum_pack,0, len(checksum_pack)))
        ccsdsPacket |= ((checksum&0xff00))
        ccsdsPacket |= ((checksum&0x00ff))
        

        return ccsdsPacket
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
        gpsEpoch = datetime.datetime(1980, 1, 6, 0, 0, 0)

        utc_time = datetime.datetime(year, month, day, hour, minute, int(sec))
        utc_time += datetime.timedelta(seconds=leapSecs)

        # Calculate time difference from GPS epoch
        tdiff = utc_time - gpsEpoch

        # Extract GPS week and time of week (SOW)
        gpsWeek = tdiff.days // 7
        gpsSOW = (tdiff.days % 7) * secsInDay + tdiff.seconds + sec % 1

        # Calculate GPS day and time of day (SOD)
        gpsDay = gpsSOW // secsInDay
        gpsSOD = gpsSOW % secsInDay

        return (gpsWeek, gpsSOW, gpsDay, gpsSOD)
