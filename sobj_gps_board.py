'''
    This module handles the incoming data from the gps board, process it and then makes a packet and publishes the gps time packet.
'''
import threading
import copy
import datetime

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
import system_constants as sensor_config # pylint: disable=e0401
from logging_system_display_python_api.DTOs.print_message_dto import print_message_dto # pylint: disable=e0401

class sobj_gps_board(sensor_parent):
    '''
        This models handles incoming gps data and then makes it into a gps time packet.
    '''
    def __init__(self, coms):
        self.__name = 'gps_board'
        self.__config = sensor_config.sensors_config[self.__name]
        self.__serial_line_two_data = []
        self.__data_lock = threading.Lock()
        self.__coms = coms
        self.__packet_number = 0
        self.__packet_number_lock = threading.Lock()


        # the structure here is a dict where the key is the name of the table you want to make and the value is a list of list that has your row information on each sub index.
        # the row structure is [<table name>, bit count (zero if you dont care), type (int, float, string, bool, bigint, byte)]
        self.__table_structure = {
            f'processed_data_for_{self.__name}_ccsds_packet' : [['gps_packets', 14, 'byte']],
            f'processed_data_for_{self.__name}' : [['day', 0, 'int'], ['hour', 0, 'int'], ['minute', 0, 'int'], ['second', 0, 'int']],
        }

        # NOTE: if you change the table_structure, you need to clear the database/dataTypes.dtobj and database/dataTypes_backup.dtobj DO NOT delete the file, just delete everything in side the file.
        sensor_parent.__init__(self, coms=coms, config= self.__config, name=self.__name, max_data_points=100, db_name = sensor_config.database_name, table_structure=self.__table_structure)
        sensor_parent.set_sensor_status(self, 'Running')
    def process_data(self, event):
        '''
            This function gets called when one of the tap request gets any data. 

            NOTE: This function always gets called no matter with tap gets data. 
        '''
        if event == 'data_received_for_gps_port_listener':
            temp, start_partial, end_partial = sensor_parent.preprocess_data(self, sensor_parent.get_data_received(self, self.__config['tap_request'][0]), delimiter=self.__config['Sensor_data_tag'], terminator=self.__config['Sensor_terminator_data_tag']) #add the received data to the list of data we have received.
            if self.__data_lock.acquire(timeout=1):
                if start_partial and len(self.__serial_line_two_data) > 0: 
                    self.__serial_line_two_data[-1] += temp[0] #append the message to the previous message (this is because partial message can be included in batches, so we are basically adding the partial messages to gether, across batches. )
                    self.__serial_line_two_data += temp[1:]
                else :
                    self.__serial_line_two_data += temp
                data_ready_for_processing = len(self.__serial_line_two_data) if not end_partial else len(self.__serial_line_two_data) - 1 #if the last packet is a partial pack then we are not going to process it.
                self.__coms.send_request('task_handler', ['add_thread_request_func', self.process_gps_packets, f'processing data for {self.__name} ', self, [data_ready_for_processing]]) #start a thread to process data
                self.__data_lock.release()
            else :
                raise RuntimeError("Could not acquire data lock")
    def process_gps_packets(self, num_packets):
        '''
            This function rips apart gps packets and then saves them in the data base as ccsds packets.  
        '''
        
        sensor_parent.set_thread_status(self, 'Running')
        if self.__data_lock.acquire(timeout=1): #get the data out of the data storage. 
            temp_data_structure = copy.deepcopy(self.__serial_line_two_data[:num_packets])
            self.__data_lock.release()
        else :
            raise RuntimeError("Could not acquire data lock")

        parsestr = 'GPRMC'
        leapSeconds = 37 - 19
        packet_terminator = '\r\n'

        processed_packets = 0
        processed_packets_list = []
        day_list = []
        hour_list = []
        minute_list = []
        second_list = []

        for packet in temp_data_structure:
            try :
                packet = packet.decode('utf-8') #Turn our byte object into a string
                if parsestr in packet and packet_terminator in packet:
                    parsedRString = packet.split(',')

                    t = self.split_by_length(parsedRString[1],2)
                    hour = int(t[0])
                    minute = int(t[1])
                    second = int(t[2])
                    
                    d = self.split_by_length(parsedRString[9],2)
                    day = int(d[0])
                    month = int(d[1])
                    year = int(d[2])

                    day_list.append(day)
                    hour_list.append(hour)
                    minute_list.append(minute)
                    second_list.append(second)
                
                    
                    results = self.gpsFromUTC(year,month,day,hour,minute,second, leapSeconds)

                    gpsWeek = results[0]
                    gps_MSOW = int(results[1] * 1000)
                    
                    if self.__packet_number_lock.acquire(timeout=1):
                        copy_packet_num = self.__packet_number
                        self.__packet_number_lock.release()
                    else : 
                        raise RuntimeError('Could not acquire packet number lock')

                    dataPacket = self.makePacket(gpsWeek, gps_MSOW, copy_packet_num)

                    processed_packets_list.append(dataPacket.to_bytes((dataPacket.bit_length() + 7) // 8, 'big')) #convert int into byte list

                    if self.__packet_number_lock.acquire(timeout=1):
                        self.__packet_number+=1
                        self.__packet_number_lock.release()
                    else :
                        raise RuntimeError('Could not acquire packet number lock')
                    processed_packets += 1

                if packet_terminator in packet:
                    processed_packets += 1
            except Exception as e: # pylint: disable=w0718
                #bad packet 
                # print(f'Bad packet or partial received. For {self.__name}, Error {e}')
                dto = print_message_dto(f'Bad packet or partial received. For {self.__name}, Error {e}')
                self.__coms.print_message(dto, 2)
        if self.__data_lock.acquire(timeout=1): #update the list with unprocessed packets. 
            self.__serial_line_two_data = self.__serial_line_two_data[num_packets:]
            self.__data_lock.release()
        else :
            raise RuntimeError("Could not acquire data lock")
        
        #save the data to the database
        data = {
            'gps_packets' : processed_packets_list,
        }
        sensor_parent.save_byte_data(self, table=f'processed_data_for_{self.__name}_ccsds_packet', data=data)

        data = {
            'day' : day_list,
            'hour' : hour_list,
            'minute' : minute_list,
            'second' : second_list,
        }

        sensor_parent.save_data(self, table=f'processed_data_for_{self.__name}', data=data)
        #now we need to publish the data NOTE: remember we are a passive sensor. 
        sensor_parent.set_publish_data(self, data=data)
        sensor_parent.publish(self)

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
