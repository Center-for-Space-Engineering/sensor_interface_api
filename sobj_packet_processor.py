'''
    This module is for processing packets that are defined in the telemetry Dictionary 
'''
import copy
from bitarray import bitarray

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
import system_constants as sensor_config # pylint: disable=e0401

class sobj_packet_processor(sensor_parent):
    '''
        This model is generic packet processor, one of these classes is created for each packet that is defined in the yaml. It will create 
        database tables for the granles in the packets then saves them into the database. 
    '''
    def __init__(self, coms, packet_config_dict:dict, apid:str) -> None:
        self.__coms = coms
        self.__packet_config = packet_config_dict
        self.__packet_nmemonic = self.__packet_config['Mnemonic']
        self.__apid = apid #this is the  sensor name 
        sensor_config.sensors_config['packet_parser'].update(self.__packet_config) # every processor uses the same genral config
        self.__config = sensor_config.sensors_config['packet_parser']
        self.__name = self.__packet_nmemonic + self.__config['extention']

        

        self.__table_structure = {}

        self.__colms_list = [['temp', 0, 'uint'] for _ in range(self.__packet_config['Channels'])]
        self.__colms_list.append(['time_STM_CLK', 0, 'bigint'])
        self.__colms_list.append(['time_RTC', 0, 'uint'])
        self.__unpacking_map = [0  for _ in range(self.__packet_config['Channels'])]

        converted = True

        for key in self.__packet_config["granule definition"]:
            try : 
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
        for i in range(len(self.__colms_list)-2): # ignore last two position since they are system clock and rtc values 
            self.__buffer[self.__colms_list[i][0]] =  [0xFFFFFFFF for _ in range(self.__packet_config['Granule count'])]   
        self.__buffer["time_STM_CLK"] = [bytearray(sensor_config.system_clock) for _ in range(self.__packet_config['Granule count'])]
        self.__buffer["time_RTC"] = [bytearray(sensor_config.real_time_clock) for _ in range(self.__packet_config['Granule count'])]

        # NOTE: if you change the table_structure, you need to clear the database/dataTypes.dtobj and database/dataTypes_backup.dtobj DO NOT delete the file, just delete everything in side the file.
        sensor_parent.__init__(self, coms=self.__coms, config= self.__config, name=self.__name, max_data_points=100, db_name = sensor_config.database_name, table_structure=self.__table_structure)
        sensor_parent.set_sensor_status(self, 'Running')
    def process_data(self, _):
        '''
            This function gets called when one of the tap request gets any data. 

            NOTE: This function always gets called no matter with tap gets data. 
        '''
        data = sensor_parent.get_data_received(self, self.__config['tap_request'][0])[self.__packet_nmemonic]
        buffer_list_to_publish = []
        for packet in data:
            if len(packet) > 0:
                # print(f"APID: {self.__apid}\n\tPacket {packet}")
                sys_clk_ms = (packet[sensor_config.ccsds_header_len+1] << 24) | (packet[sensor_config.ccsds_header_len+2] << 16) | (packet[sensor_config.ccsds_header_len+3] << 8) | (packet[sensor_config.ccsds_header_len+4])
                real_time_clk = (packet[sensor_config.ccsds_header_len+sensor_config.system_clock+1] << 16) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock+2] << 8) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock+3])
                cur_position_bits = int((sensor_config.ccsds_header_len+1 + sensor_config.system_clock + sensor_config.real_time_clock) * 8)
                packet_bits = bitarray()
                packet_bits.frombytes(packet)
                for j in range(self.__packet_config['Granule count']):
                    self.__buffer['time_STM_CLK'][j] = sys_clk_ms
                    self.__buffer['time_RTC'][j] = real_time_clk
                    sys_clk_ms += int((1/(self.__packet_config['G. Rate'])) * 1000) # system clock is in milliseconds
                    for i in range(len(self.__unpacking_map)): # pylint: disable=C0200
                        # print(f"APID: {self.__apid}\tPacket length: {len(packet)}\tPacket length bits: {len(packet_bits)}\tcolmslist curr: {self.__colms_list[i]}\t cur_position: {cur_position_bits}\tcurpostiion+unpacking: {cur_position_bits+self.__unpacking_map[i]}")
                        temp = packet_bits[cur_position_bits:cur_position_bits+self.__unpacking_map[i]]
                        self.__buffer[self.__colms_list[i][0]][j] = self.bitarray_to_int(temp) | 0x00000000
                        cur_position_bits += self.__unpacking_map[i]
                # save to db and publish 
                buf_copy = copy.deepcopy(self.__buffer)
                sensor_parent.save_data(self, table=f"{self.__packet_config['Mnemonic']}", data=buf_copy)
                buffer_list_to_publish.append(buf_copy)
                # flush the buffer
                for key in self.__buffer: # pylint: disable=C0206
                    for byte_storage in range(len(self.__buffer[key])):
                        self.__buffer[key][byte_storage] = 0xFFFFFFFF
        sensor_parent.set_publish_data(self, data=buffer_list_to_publish)
        sensor_parent.publish(self)
    def bitarray_to_int(self, bit_array):
        '''
            converts bitarray into and int
        '''
        result = 0
        for bit in bit_array:
            result = (result << 1) | bit
        return result

                

                
        
        