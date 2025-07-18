'''
    This module handles the incoming data from the gps board, process it and then makes a packet and publishes the gps time packet.
'''
import threading
import copy
from datetime import datetime

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
import system_constants as sensor_config # pylint: disable=e0401
from command_packets.functions import ccsds_crc16 # pylint: disable=e0401
from logging_system_display_python_api.logger import loggerCustom as logger

class sobj_packet_detect(sensor_parent):
    '''
        This models counts the number of each type of packet recieved.
    '''
    def __init__(self, coms, name:str):
        self.__name = name
        self.__config = sensor_config.sensors_config[self.__name]
        self.__data_group = self.__config['packet_sturture'] # we are going to use the file name to track our data
        self.__serial_line_two_data = []
        self.__data_lock = threading.Lock()
        self.__coms = coms

        self.__telemetry_packet_type_num = sensor_config.telemetry_packet_num[self.__data_group]
        self.__packet_count = [0] * self.__telemetry_packet_type_num
        self.__bad_crc_count = 0
        self.__unknown_apid_count = 0

        self.__telemetry_packet_types = sensor_config.telemetry_packet_types[self.__data_group]
        self.__telemetry_packet_types_lock = threading.Lock() 


        self.__apids = sensor_config.valid_apids[self.__data_group]
        self.__apids_lock = threading.Lock()

        self.__start_time = datetime.now()

        self.__logger = logger(f'logs/{self.__name}.txt') # pylint: disable=W0238
        # self.__logger_lock = threading.Lock()


        # the structure here is a dict where the key is the name of the table you want to make and the value is a list of list that has your row information on each sub index.
        # the row structure is [<table name>, bit count (zero if you dont care), type (int, float, string, bool, bigint, byte)]
        counts = [['time', 0, 'string'], ['Ukwn', 0, 'int'], ['bad_crc', 0, 'int']]
        counts.extend([tup[0], 0, 'int'] for tup in self.__telemetry_packet_types)

        rates = [['time', 0, 'string'], ['Ukwn', 0, 'float'], ['bad_crc', 0, 'float']]
        rates.extend([tup[0], 0, 'float'] for tup in self.__telemetry_packet_types)

        self.__table_structure = {
            f'processed_data_for_{self.__name}_counts' : counts,
            f'processed_data_for_{self.__name}_rates' : rates
        }

        # NOTE: if you change the table_structure, you need to clear the database/dataTypes.dtobj and database/dataTypes_backup.dtobj DO NOT delete the file, just delete everything in side the file.
        sensor_parent.__init__(self, coms=coms, config= self.__config, name=self.__name, max_data_points=00, db_name = sensor_config.database_name, table_structure=self.__table_structure)
        sensor_parent.set_sensor_status(self, 'Running')
    def is_valid_apid(self, apid, apids):
        '''
            check apid agaist list of valid apids
        '''
        return apid in apids
    def get_packet_info(self, apid):
        '''
            this function searches thorugh the list of telemetry packets then returns to corrisponding information 
            for the given apid.
        '''
        temp = ()
        if self.__telemetry_packet_types_lock.acquire(): # pylint: disable=R1732
            for tup in self.__telemetry_packet_types:
                if apid in tup:
                    temp = tup
                    break
            self.__telemetry_packet_types_lock.release()
        else :
            raise RuntimeError('Could not acquire telemetry packets types lock')
        return temp
    def process_data(self, event):
        '''
            This function gets called when one of the tap request gets any data. 

            NOTE: This function always gets called no matter with tap gets data. 
        '''
        telemetry_packets_copy = None
        apids = None
        if self.__telemetry_packet_types_lock.acquire(): # pylint: disable=R1732
            telemetry_packets_copy = copy.deepcopy(self.__telemetry_packet_types)
            self.__telemetry_packet_types_lock.release()
        else :
            raise RuntimeError("Could not acquire telementry packet types lock")
        
        if self.__apids_lock.acquire(): # pylint: disable=R1732
            apids = copy.deepcopy(self.__apids)
            self.__apids_lock.release()
        else :
            raise RuntimeError("Could not acquire apids lock")
        
        
        # self.__logger.send_log(str(event))
        event_name = event[18:]
        while sensor_parent.data_received_is_empty(self):
            temp, _ = sensor_parent.preprocess_ccsds_data(self, sensor_parent.get_data_received(self, event_name)) #add the received data to the list of data we have received.
            
            with self.__data_lock:
                self.__serial_line_two_data += temp
                data_ready_for_processing =  len(self.__serial_line_two_data) #if the last packet is a partial pack then we are not going to process it.
                self.__coms.send_request('task_handler', ['add_thread_request_func', self.process_count_packets, f'processing data for {self.__name}', self, [copy.deepcopy(self.__serial_line_two_data[:data_ready_for_processing]), event, apids, telemetry_packets_copy]]) #start a thread to process data 
                self.__serial_line_two_data = self.__serial_line_two_data[data_ready_for_processing:]
    def process_count_packets(self, temp_data_structure, _, apids, telemetry_packets_copy):
        '''
            This function rips apart telemetry packets and counts how many of each type there is.  
        '''
        sensor_parent.set_thread_status(self, 'Running')
        # data to publish
        data = {tup[0]: [] for tup in self.__telemetry_packet_types} #pos zero is the packet Mnemonic

        # sort the packets basied on apid and mnemonic
        for packet in temp_data_structure:
            # self.__logger.send_log(f"Packet: {packet.hex()}")
            #get apid
            APID = int.from_bytes(packet[:2], 'big') & 0x07ff
            apid_str = f"{APID:03X}"

            #validation check
            if not self.is_valid_apid(apid_str, apids):
                self.__unknown_apid_count += 1
            else : 
                #sort packets into their corrisponding list
                packet_data_tup = self.get_packet_info(apid_str)
                if ccsds_crc16(packet) == 0x00:                                    # valid crc
                    self.__packet_count[packet_data_tup[2]] += 1                             # increment the appropriate packet count
                    data[packet_data_tup[0]].append(packet)   # add packet to list in data dictionary for publishing
                else:                                                                   # invalid crc
                    self.__bad_crc_count += 1
                    # self.__logger.send_log(f"bad_crc found: {packet[-2:]}")

        current_time = datetime.now()
        elapsed_seconds = (current_time - self.__start_time).total_seconds()
        
        # Create data to save to the database
        save_data = {
            'time' : [str(current_time)],
            'Ukwn' : [self.__unknown_apid_count],
            'bad_crc' : [self.__bad_crc_count]
        }
        
        #put all the packet counts in the corret place
        for packet in telemetry_packets_copy:
            save_data[packet[0]] = [self.__packet_count[packet[2]]]
        #save counts
        sensor_parent.save_data(self, table=f'processed_data_for_{self.__name}_counts', data=save_data)

        # Create data to save to the database
        save_data = {
            'time' : [str(current_time)],
            'Ukwn' : [0 if self.__unknown_apid_count == 0.0 else elapsed_seconds/self.__unknown_apid_count],
            'bad_crc' : [0 if self.__bad_crc_count == 0.0 else elapsed_seconds/self.__bad_crc_count]
        }
        #put all the packet counts in the corret place
        for packet in telemetry_packets_copy:
            save_data[packet[0]] = [0 if self.__packet_count[packet[2]] == 0 else elapsed_seconds/self.__packet_count[packet[2]]]
        #save rate data
        sensor_parent.save_data(self, table=f'processed_data_for_{self.__name}_rates', data=save_data)

        #now we need to publish the data NOTE: remember we are a passive sensor. 
        sensor_parent.set_publish_data(self, data=data)
        sensor_parent.publish(self)

        sensor_parent.set_thread_status(self, 'Complete')
