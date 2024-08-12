'''
    This module is for converting parsed STT packets (L0 data) up to L1 data. 
'''

import copy

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
import system_constants as sensor_config # pylint: disable=e0401


class sobj_stt_L0_to_L1_converter(sensor_parent):
    '''
        This class takes in an array of dictionaries representing each STT channel and 
        converts them to L1 data and stores them in the 'STT_L1' table
    '''
    def __init__(self, coms):
        self.__name = 'stt_L0_to_L1_converter'
        self.__config = sensor_config.sensors_config[self.__name]
        self.__coms = coms

        self.__table_structure = {
             'STT_L1' : [ ['GPSW', 0, 'uint'], 
                          ['GPSM', 0, 'uint'], 
                          ['0ADC0', 0, 'float'],
                          ['0ADC1', 0, 'float'],
                          ['0ADC2', 0, 'float'],
                          ['0ADC3', 0, 'float'],
                          ['0ADCT', 0, 'float'],
                          ['1ADC0', 0, 'float'],
                          ['1ADC1', 0, 'float'],
                          ['1ADC2', 0, 'float'],
                          ['1ADC3', 0, 'float'],
                          ['1ADCT', 0, 'float'],
                          ['2ADC0', 0, 'float'],
                          ['2ADC1', 0, 'float'],
                          ['2ADC2', 0, 'float'],
                          ['2ADC3', 0, 'float'],
                          ['2ADCT', 0, 'float'],
                          ['3ADC0', 0, 'float'],
                          ['3ADC1', 0, 'float'],
                          ['3ADC2', 0, 'float'],
                          ['3ADC3', 0, 'float'],
                          ['3ADCT', 0, 'float'],
                          ['4ADC1', 0, 'float'],
                          ['4ADC2', 0, 'float'],
                          ['4ADCT', 0, 'float'],
                          ['PAC', 0, 'uint'],
                          ['PHFC', 0, 'uint'],
                          ['PCFR', 0, 'uint'],
                          ['TBD1', 0, 'uint'],
                          ['TBD2', 0, 'uint'],
                          ['TBD3', 0, 'uint'],
                          ['TBD4', 0, 'uint'],
                          ['TBD5', 0, 'uint'],
                          ['TBD6', 0, 'uint'],
                          ['TBD7', 0, 'uint'],
                          ['TBD8', 0, 'uint'],
                          ['TBD9', 0, 'uint'],
                          ['TBD10', 0, 'uint'],
                          ['TBD11', 0, 'uint'],
                          ['time_STM_CLK', 0, 'uint'],
                          ['time_RTC', 0, 'uint'], ]
        }

        # NOTE: if you change the table_structure, you need to clear the database/dataTypes.dtobj and database/dataTypes_backup.dtobj DO NOT delete the file, just delete everything in side the file.
        sensor_parent.__init__(self, coms=self.__coms, config= self.__config, name=self.__name, db_name = sensor_config.database_name, table_structure=self.__table_structure)
        sensor_parent.set_sensor_status(self, 'Running')

        # conversion constants
        self.__FSR = 2.048
        self.__LSB = (self.__FSR*2) / (65536)
        self.__current_gain = 4.99

    def process_data(self, _):
        '''
            This function gets called when one of the tap request gets any data. 

            NOTE: This function always gets called no matter with tap gets data. 
        '''
        data = sensor_parent.get_data_received(self, self.__config['tap_request'][0])
        buffer = {}
        for parsed_packet in data:
            for key in parsed_packet:
                match key:
                    case '0ADC0':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB) / self.__current_gain]
                    case '0ADC1':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB) / self.__current_gain]
                    case '0ADC2':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB) / self.__current_gain]
                    case '0ADC3':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB) / self.__current_gain]
                    case '0ADCT':
                        buffer[key] = [(parsed_packet[key][0] >> 2) * 0.03125]
                    case '1ADC0':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB) / self.__current_gain]
                    case '1ADC1':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB) / self.__current_gain]
                    case '1ADC2':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB) / self.__current_gain]
                    case '1ADC3':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB) / self.__current_gain]
                    case '1ADCT':
                        buffer[key] = [(parsed_packet[key][0] >> 2) * 0.03125]
                    case '2ADC0':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB) / (100/243)]
                    case '2ADC1':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB) / (1/3)]
                    case '2ADC2':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB) / (100/274)]
                    case '2ADC3':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB)]
                    case '2ADCT':
                        buffer[key] = [(parsed_packet[key][0] >> 2) * 0.03125]
                    case '3ADC0':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB) / (1/2)]
                    case '3ADC1':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB) / (100/151)]
                    case '3ADC2':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB)]
                    case '3ADC3':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB)]
                    case '3ADCT':
                        buffer[key] = [(parsed_packet[key][0] >> 2) * 0.03125]
                    case '4ADC1':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB)]
                    case '4ADC2':
                        buffer[key] = [(parsed_packet[key][0] * self.__LSB) / (100/274)]
                    case '4ADCT':
                        buffer[key] = [(parsed_packet[key][0] >> 2) * 0.03125]
                    case _:
                        buffer[key] = [parsed_packet[key][0]]
            buf_copy = copy.deepcopy(buffer)
            sensor_parent.save_data(self, table='STT_L1', data=buf_copy)