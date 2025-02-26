'''
    This module is for processing packets that are defined in the telemetry Dictionary 
'''
import copy
from bitarray import bitarray
from datetime import datetime, timedelta, timezone
import sys

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
import system_constants as sensor_config # pylint: disable=e0401
from logging_system_display_python_api.logger import loggerCustom as logger

'''
    We think the IndexError is originating here- issues with STT L0 to L1 conversion specifically - length of data not consistent

    float object is not subscriptable, followed by IndexError - is it trying to access index of a float for some reason in STT specifically??
    Sean mentioned they were having issues with STT and STTA in the real gs - could be a deeper issue :/
    Got four STT packets before it failed- not an issue with all STTs?

    NOTE: test with aux file- much faster to get STTAs, and a lot more
'''

class sobj_packet_processor(sensor_parent):
    '''
        This model is generic packet processor, one of these classes is created for each packet that is defined in the yaml. It will create 
        database tables for the granules in the packets then saves them into the database. 
    '''
    def __init__(self, coms, name, packet_config_dict:dict, apid:str) -> None:
        self.__name = name
        self.__coms = coms
        self.__packet_config = packet_config_dict
        self.__packet_nmemonic = self.__packet_config['Mnemonic']
        self.__apid = apid #this is the  sensor name 
        sensor_config.sensors_config[self.__name].update(self.__packet_config) # every processor uses the same general config
        self.__config = sensor_config.sensors_config[self.__name]
        self.__config['apid'] = self.__apid
        self.__name = self.__packet_nmemonic + self.__config['extention']
        self.__count = 0
        self.__logger = logger(f'logs/{self.__packet_nmemonic}.txt')

        self.__table_structure = {}

        self.__colms_list = [['temp', 0, 'uint'] for _ in range(self.__packet_config['Channels'])]
        if self.__name in sensor_config.time_correlation:
            self.__colms_list.append(['PPS_UTC', 0, 'mysql_micro_datetime'])
            self.__colms_list.append(['PPSR_EPOCH', 0, 'mysql_milli_datetime'])
            self.__colms_list.append(['PPSS_EPOCH', 0, 'mysql_micro_datetime'])
        self.__colms_list.append(['time_STM_CLK', 0, 'bigint'])
        self.__colms_list.append(['time_RTC', 0, 'uint'])
        self.__colms_list.append(['time_STM_CLK_UTC', 0, 'mysql_micro_datetime', "secondary_index"])
        self.__colms_list.append(['time_RTC_UTC', 0, 'mysql_milli_datetime', "secondary_index"])
        self.__colms_list.append(['received_at', 0, 'uint', "nullable"])
        self.__colms_list.append(['packet_count', 0, 'uint'])
        self.__colms_list.append(['granule_index', 0, 'uint'])
        self.__unpacking_map = [0  for _ in range(self.__packet_config['Channels'])]

        converted = True

        for key in self.__packet_config["granule definition"]:
            try : 
                if self.__packet_config["granule definition"][key]['Signed']:
                    self.__colms_list[int (self.__packet_config["granule definition"][key]['Order'] - 1)][2] = 'int'
                if int (self.__packet_config["granule definition"][key]['Order'] - 1) >= self.__packet_config['Channels']: # some timnes we have granules that have tbh parts
                    continue
                self.__colms_list[int (self.__packet_config["granule definition"][key]['Order'] - 1)][0] =  key
                self.__unpacking_map[int (self.__packet_config["granule definition"][key]['Order'] - 1)] = int(self.__packet_config["granule definition"][key]['Word Length (bits)'])
            except ValueError: # we cant convert the dictionary raise an error
                converted = False
                print(f"Warning can not convert type for apid {self.__apid}")
            except Exception as e: #pylint: disable=w0718
                converted = False
                print(f"Warning convertion faild for apid {self.__apid} Error: {e}")
        if converted is True :
            self.__table_structure[f"{self.__packet_config['Mnemonic']}"] = self.__colms_list

        self.__buffer = {}

        #!!! check this here - is it still looking at the right columns??
        for i in range(len(self.__colms_list)-2): # ignore last two position since they are system clock and rtc values
            self.__buffer[self.__colms_list[i][0]] =  [0xFFFFFFFF for _ in range(self.__packet_config['Granule count'])]
        if self.__name in sensor_config.time_correlation:
            self.__buffer["PPS_UTC"] = [(sensor_config.PPS_UTC) for _ in range(self.__packet_config['Granule count'])]
            self.__buffer["PPSS_EPOCH"] = [(sensor_config.PPSS_epoch) for _ in range(self.__packet_config['Granule count'])]
            self.__buffer["PPSR_EPOCH"] = [(sensor_config.PPSR_epoch) for _ in range (self.__packet_config['Granule count'])]

        self.__buffer["time_STM_CLK"] = [bytearray(sensor_config.system_clock) for _ in range(self.__packet_config['Granule count'])]
        self.__buffer["time_RTC"] = [bytearray(sensor_config.real_time_clock) for _ in range(self.__packet_config['Granule count'])]

        self.__buffer["time_STM_CLK_UTC"] = [bytearray(sensor_config.system_clock_utc) for _ in range(self.__packet_config['Granule count'])]  # !!! what do I put inside the brackets?
        self.__buffer["time_RTC_UTC"] = [bytearray(sensor_config.real_time_clock_utc) for _ in range(self.__packet_config['Granule count'])]   #do I want 
        self.__buffer["received_at"] = [bytearray(sensor_config.received_at) for _ in range(self.__packet_config['Granule count'])]
        self.__buffer["packet_count"] = [bytearray(sensor_config.packet_count) for _ in range(self.__packet_config['Granule count'])]
        self.__buffer["granule_index"] = [j for j in range(self.__packet_config['Granule count'])]

        # NOTE: if you change the table_structure, you need to clear the database/dataTypes.dtobj and database/dataTypes_backup.dtobj DO NOT delete the file, just delete everything in side the file.
        sensor_parent.__init__(self, coms=self.__coms, config= self.__config, name=self.__name, max_data_points=100, db_name = sensor_config.database_name, table_structure=self.__table_structure)
        sensor_parent.set_sensor_status(self, 'Running')
        self.__logger.send_log(f"Setup complete{self.__packet_nmemonic}")
    def process_data(self, _):
        '''
            This function gets called when one of the tap request gets any data. 

            NOTE: This function always gets called no matter with tap gets data. 
        '''
        data = sensor_parent.get_data_received(self, self.__config['tap_request'][0])[self.__packet_nmemonic]
        buffer_dict_to_publish = {
        }
        for packet in data:
            if len(packet) > 0:
                # print(f"APID: {self.__apid}\n\tPacket {packet}")
                packet_count = ((packet[2] << 8) | (packet[3])) & 0x3FFF
                sys_clk_ms = (packet[sensor_config.ccsds_header_len+1] << 24) | (packet[sensor_config.ccsds_header_len+2] << 16) | (packet[sensor_config.ccsds_header_len+3] << 8) | (packet[sensor_config.ccsds_header_len+4])
                real_time_clk = (packet[sensor_config.ccsds_header_len+sensor_config.system_clock+1] << 16) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock+2] << 8) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock+3])
                cur_position_bits = int((sensor_config.ccsds_header_len+1 + sensor_config.system_clock + sensor_config.real_time_clock) * 8)
                packet_bits = bitarray()
                packet_bits.frombytes(packet)
                for j in range(self.__packet_config['Granule count']):
                    self.__buffer['time_STM_CLK'][j] = sys_clk_ms
                    self.__buffer['time_RTC'][j] = real_time_clk
                    # self.__logger.send_log(f"{sys_clk_ms=} {real_time_clk=}")

                    self.__buffer['time_STM_CLK_UTC'][j] = self.to_UTC(sys_clk_ms, is_RTC=False).strftime('%Y-%m-%d %H:%M:%-S.%f')
                    self.__buffer['time_RTC_UTC'][j] = self.to_UTC(real_time_clk, is_RTC=True).strftime('%Y-%m-%d %H:%M:%-S.%f')[:-3]
                    self.__buffer['received_at'][j] = datetime.now(timezone.utc).timestamp()
                    # self.__logger.send_log(f"Clocks updated to UTC at time {datetime.fromtimestamp(self.__buffer['received_at'][j])}")
                    self.__buffer['packet_count'][j] = packet_count
                    sys_clk_ms = int((1/(self.__packet_config['G. Rate'])) * 1000) + sys_clk_ms if self.__packet_config['G. Rate'] != 0 else sys_clk_ms # system clock is in milliseconds
                    for i in range(len(self.__unpacking_map)): # pylint: disable=C0200
                        # print(f"APID: {self.__apid}\tPacket length: {len(packet)}\tPacket length bits: {len(packet_bits)}\tcolmslist curr: {self.__colms_list[i]}\t cur_position: {cur_position_bits}\tcurpostiion+unpacking: {cur_position_bits+self.__unpacking_map[i]}")
                        temp = packet_bits[cur_position_bits:cur_position_bits+self.__unpacking_map[i]]
                        if len(temp) > 32: #all of these need to be an unit 32 or smaller. 
                            self.__buffer[self.__colms_list[i][0]][j] = 0
                            self.__logger.send_log(f'Unpacking packet {self.__packet_nmemonic} got too large of bin size at {self.__colms_list[i][0]}, must be 32 bits or smaller but has size {self.__unpacking_map[i]}.')
                        else :
                            if self.__colms_list[i][2] == 'int' and temp[0] == 1:
                                while len(temp) < 32:
                                    temp.insert(0,1)
                                self.__buffer[self.__colms_list[i][0]][j] = int.from_bytes(temp, byteorder=sys.byteorder,signed = True)
                            else:
                                self.__buffer[self.__colms_list[i][0]][j] = self.bitarray_to_int(temp) | 0x00000000
                        cur_position_bits += self.__unpacking_map[i]

                    # Update PPS_UTC and, if necessary, PPSS and PPSR epochs
                    if self.__name in sensor_config.time_correlation:
                        # Updating PPS_UTC
                        #get PPS packet for the correct board
                        PPSS = (packet[sensor_config.ccsds_header_len+sensor_config.gps_weeks+sensor_config.gps_milliseconds+1] << 24) | (packet[sensor_config.ccsds_header_len+sensor_config.gps_weeks+sensor_config.gps_milliseconds+2] << 16) | (packet[sensor_config.ccsds_header_len+sensor_config.gps_weeks+sensor_config.gps_milliseconds+3] << 8) | (packet[sensor_config.ccsds_header_len+sensor_config.gps_weeks+sensor_config.gps_milliseconds+4])
                        PPSR = (packet[sensor_config.ccsds_header_len+sensor_config.gps_weeks+sensor_config.gps_milliseconds+sensor_config.system_clock+1] << 16) | (packet[sensor_config.ccsds_header_len+sensor_config.gps_weeks+sensor_config.gps_milliseconds+sensor_config.system_clock+2] << 8) | (packet[sensor_config.ccsds_header_len+sensor_config.gps_weeks+sensor_config.gps_milliseconds+sensor_config.system_clock+3])

                        gps_week = (packet[sensor_config.ccsds_header_len + sensor_config.system_clock + sensor_config.real_time_clock+ 1] << 8) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+2]) # Value is dubious
                        gps_milli = (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+sensor_config.gps_weeks+1] << 24) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+sensor_config.gps_weeks+2] << 16) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+sensor_config.gps_weeks+3] << 8) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+sensor_config.gps_weeks+4])
                        
                        if gps_week != None and gps_milli != None:
                            newPPS_UTC = (datetime(1980, 1, 6, 0 , 0) + timedelta(weeks=gps_week) + timedelta(milliseconds=gps_milli))
                            self.__buffer['PPS_UTC'][j] = newPPS_UTC.strftime('%Y-%m-%d %H:%M:%-S.%f')
                            sensor_config.PPS_UTC = newPPS_UTC
                        else:
                            self.__buffer['PPS_UTC'][j] = None # Swenson recommended None / null so the field comes in empty into the database
                            sensor_config.PPS_UTC = None


                        if (sensor_config.PPS_UTC != None):

                            sensor_config.PPSS_epoch = (sensor_config.PPS_UTC - timedelta(milliseconds=PPSS))
                            sensor_config.PPSR_epoch = (sensor_config.PPS_UTC - timedelta(seconds=PPSR))

                            self.__buffer['PPSS_EPOCH'][j] = sensor_config.PPSS_epoch.strftime('%Y-%m-%d %H:%M:%-S.%f')
                            self.__buffer['PPSR_EPOCH'][j] = sensor_config.PPSR_epoch.strftime('%Y-%m-%d %H:%M:%-S.%f')[:-3]
                        else:
                            self.__buffer['PPSS_EPOCH'][j] = None # Swenson recommended None / null so the field comes in empty into the database
                            self.__buffer['PPSR_EPOCH'][j] = None # Swenson recommended None / null so the field comes in empty into the database
                # save to db and publish 
                buf_copy = copy.deepcopy(self.__buffer)
                sensor_parent.save_data(self, table=f"{self.__packet_nmemonic}", data=buf_copy)

                #lets save the data into a dictionary
                all_keys_set = set(self.__buffer.keys()).union(buffer_dict_to_publish.keys())

                for key in all_keys_set:
                    buffer_dict_to_publish[key] = self.__buffer.get(key, []) + buffer_dict_to_publish.get(key, [])

                # flush the buffer
                for key in self.__buffer: # pylint: disable=C0206
                    if not key == 'granule_index':
                        for byte_storage in range(len(self.__buffer[key])):
                            self.__buffer[key][byte_storage] = 0xFFFFFFFF

        sensor_parent.set_publish_data(self, data=buffer_dict_to_publish)
        sensor_parent.publish(self)
        
    def bitarray_to_int(self, bit_array):
        '''
            converts bitarray into and int
        '''
        result = 0
        for bit in bit_array:
            result = (result << 1) | bit
        return result

    def to_UTC(self, gps_clock, is_RTC):
        '''
            converts given time into utc time

            returned obj is datetime obj
        '''
        if (is_RTC):
            new_datetime = (sensor_config.PPSR_epoch) + timedelta(seconds=gps_clock)
            return  new_datetime
        else:
            new_datetime = (sensor_config.PPSS_epoch) + timedelta(milliseconds=gps_clock)
            return new_datetime              
        