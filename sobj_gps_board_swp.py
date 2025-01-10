'''
    This module handles the incoming data from the gps board, process it and then makes a packet and publishes the gps time packet.
'''
import threading
import copy
import datetime
import traceback

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
import system_constants as sensor_config # pylint: disable=e0401
from logging_system_display_python_api.DTOs.print_message_dto import print_message_dto # pylint: disable=e0401
import system_constants # pylint: disable=e0401
from command_packets.functions import ccsds_crc16 # pylint: disable=e0401


class sobj_gps_board_swp(sensor_parent):
    '''
        This models handles incoming gps data and then makes it into a gps time packet.
    '''
    def __init__(self, coms):
        self.__name = 'gps_board_swp'
        self.__config = sensor_config.sensors_config[self.__name]
        self.__serial_line_two_data = []
        self.__data_lock = threading.Lock()
        self.__coms = coms
        self.__packet_number = 0
        self.__packet_number_lock = threading.Lock()


        # the structure here is a dict where the key is the name of the table you want to make and the value is a list of list that has your row information on each sub index.
        # the row structure is [<table name>, bit count (zero if you dont care), type (int, float, string, bool, bigint, byte)]
        self.__table_structure = {
            f'processed_data_for_{self.__name}' : [['gps_packets', 13, 'byte']],
        }

        # NOTE: if you change the table_structure, you need to clear the database/dataTypes.dtobj and database/dataTypes_backup.dtobj DO NOT delete the file, just delete everything in side the file.
        sensor_parent.__init__(self, coms=coms, config= self.__config, name=self.__name, max_data_points=100, db_name = '', table_structure=self.__table_structure)
        sensor_parent.set_sensor_status(self, 'Running')
    def process_data(self, event):
        '''
            This function gets called when one of the tap request gets any data. 

            NOTE: This function always gets called no matter with tap gets data. 
        '''
        temp, start_partial, end_partial = sensor_parent.preprocess_data(self, [sensor_parent.get_data_received(self, self.__config['tap_request'][0])], delimiter=self.__config['Sensor_data_tag'], terminator=self.__config['Sensor_terminator_data_tag']) #add the received data to the list of data we have received.
        with self.__data_lock:
            if start_partial and len(self.__serial_line_two_data) > 0: 
                self.__serial_line_two_data[-1] += temp[0] #append the message to the previous message (this is because partial message can be included in batches, so we are basically adding the partial messages to gether, across batches. )
                self.__serial_line_two_data += temp[1:]
            else :
                self.__serial_line_two_data += temp
            data_ready_for_processing = len(self.__serial_line_two_data) if not end_partial else len(self.__serial_line_two_data) - 1 #if the last packet is a partial pack then we are not going to process it.  
            self.__coms.send_request('task_handler', ['add_thread_request_func', self.process_gps_packets, f'processing data for {self.__name} ', self, [data_ready_for_processing]]) #start a thread to process data
    def process_gps_packets(self, num_packets):
        '''
            This function rips apart gps packets and then saves them in the data base as ccsds packets.  
        '''
        
        sensor_parent.set_thread_status(self, 'Running')
        with self.__data_lock: #get the data out of the data storage. 
            temp_data_structure = copy.deepcopy(self.__serial_line_two_data[:num_packets])

        parsestr = 'GPRMC'
        leapSeconds = 37 - 19
        packet_terminator = '\r\n'

        processed_packets = 0
        processed_packets_list = []

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

                    results = self.gpsFromUTC(year,month,day,hour,minute,second,leapSeconds)

                    gpsWeek = results[0]
                    gps_MSOW = int(results[1] * 1000)
                    
                    with self.__packet_number_lock:
                        copy_packet_num = self.__packet_number

                    dataPacket, formattedDataPacket = self.makePacket(gpsWeek, gps_MSOW, copy_packet_num)

                    processed_packets_list.append((dataPacket, formattedDataPacket)) #convert int into byte list

                    with self.__packet_number_lock:
                        self.__packet_number+=1
                    processed_packets += 1

                if packet_terminator in packet:
                    processed_packets += 1
            except Exception as e: # pylint: disable=w0718
                #bad packet 
                # print(f'Bad packet or partial received. For {self.__name}, Error {e}')
                dto = print_message_dto(f'Bad packet or partial received. For {self.__name}, Error {e}')
                self.__coms.print_message(dto, 2)
                processed_packets += 1
        with self.__data_lock: #update the list with unprocessed packets. 
            self.__serial_line_two_data = self.__serial_line_two_data[processed_packets:]
        
        #save the data to the database
        data = {
            'gps_packets' : processed_packets_list,
        }

        if len(processed_packets_list) > 0:
            self.__coms.send_request(system_constants.swp_board_writer, ['write_to_serial_port_bytes', processed_packets_list[-1][0]]) #we are going to grab the last processed gps packet to send

            #make sure their is a db table 
            table = {
                f'formatted_packets_{self.__name}' : [['gps_packets', 0, 'string']]
            }

            self.__coms.send_post([table, '/create_table_db']) # data, then request url

            #now send the save data
            data = {
                'table name' : f'formatted_packets_{self.__name}',
                'data' : { 'gps_packets' : [processed_packets_list[-1][1]]}
            }
            self.__coms.send_post([data, '/save_data_to_table']) # data, then request url


        #now we need to publish the data NOTE: remember we are a passive sensor. 
        sensor_parent.set_publish_data(self, data=data)
        sensor_parent.publish(self)

        sensor_parent.set_thread_status(self, 'Complete')

    def makePacket(self, week, mseconds, packetNumber):
        '''
            This makes a ccsds packet from the give args. (returns byte array)
            
            TODO: add sync word
        '''
        #Create Header

        headerPacketCount = packetNumber


        packet_apid = system_constants.APID_pps #0x21
        data_week = week.to_bytes(2, byteorder='big')
    
        byte_data_mseconds = mseconds.to_bytes(4, byteorder='big')

        byte_data = data_week + byte_data_mseconds

        packet_version_number = system_constants.pvn
        packet_type = system_constants.pck_type
        secondary_header = system_constants.sec_header
        sequence_flags = system_constants.seq_flags
        packet_count = headerPacketCount
        packet_length = len(byte_data) + 1 #Has to be the total number of data bytes (not including crc) plus one for ccsds standard ¯\_(ツ)_/¯

        header_byte1 = ((packet_version_number & system_constants.mask_pvn) << 5) | ((packet_type & system_constants.mask_pck_type) << 4) | ((secondary_header & system_constants.mask_sec_header) << 3) | ((packet_apid & system_constants.mask_APID_1) >> 8)
        header_byte2 = packet_apid & system_constants.mask_APID_2
        header_byte3 = ((sequence_flags & system_constants.mask_seq_flags) << 6) | ((packet_count & system_constants.mask_packet_count_1) >> 8)
        header_byte4 = packet_count & system_constants.mask_packet_count_2
        header_byte5 = (packet_length & system_constants.mask_packet_len_1) >> 8
        header_byte6 = packet_length & system_constants.mask_packet_len_2

        header = bytearray([header_byte1, header_byte2, header_byte3, header_byte4, header_byte5, header_byte6])

        bytes_for_crc = header + byte_data

        crc = ccsds_crc16(data=bytes_for_crc)

        crc_bytes = crc.to_bytes(2, byteorder='big')

        packet_bytes = bytes_for_crc + crc_bytes

        formatted_bytes = [f'\\x{byte:02x}' for byte in packet_bytes]
        formatted_bytes =  ''.join(formatted_bytes) 
        return packet_bytes, formatted_bytes
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

        utc_time = datetime.datetime(year + 2000, month, day, hour, minute, int(sec))
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
