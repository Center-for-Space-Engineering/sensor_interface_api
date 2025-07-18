'''
    This module is for converting parsed STTA packets (L0 data) up to L1 data. 
'''

import copy

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
import system_constants as sensor_config # pylint: disable=e0401
from logging_system_display_python_api.logger import loggerCustom as logger


class sobj_stta_L0_to_L1_converter(sensor_parent):
    '''
        This class takes in an array of dictionaries representing each STT channel and 
        converts them to L1 data and stores them in the 'STT_L1' table
    '''
    def __init__(self, coms):
        self.__name = 'stta_L0_to_L1_converter'
        self.__config = sensor_config.sensors_config[self.__name]
        self.__coms = coms
        self.__logger = logger(f'logs/{self.__name}.txt') # pylint: disable=W0238

        self.__table_structure = {
             'STTA_L1' : [ ['PPSW', 0, 'uint'],
                          ['PPSM', 0, 'uint'],
                          ['PPSS', 0, 'uint'],
                          ['PPSR', 0, 'uint'],
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
                          ['4ADC0', 0, 'float'],
                          ['4ADC1', 0, 'float'],
                          ['4ADC2', 0, 'float'],
                          ['4ADC3', 0, 'float'],
                          ['4ADCT', 0, 'float'],
                          ['PAC', 0, 'uint'],
                          ['PHFC', 0, 'uint'],
                          ['PCFC', 0, 'uint'],
                          ['VERS', 0, 'uint'],
                          ['MODE1', 0, 'uint'],
                          ['H1S', 0, 'uint'],
                          ['H2S', 0, 'uint'],
                          ['H3S', 0, 'uint'],
                          ['H4S', 0, 'uint'],
                          ['H5S', 0, 'uint'],
                          ['H6S', 0, 'uint'],
                          ['REG_5V', 0, 'uint'],
                          ['GPS_C', 0, 'uint'],
                          ['DEBUG', 0, 'uint'],
                          ['time_STM_CLK', 0, 'uint'],
                          ['time_RTC', 0, 'uint'],
                          ['time_STM_CLK_UTC', 0, 'mysql_micro_datetime', "secondary_index"],
                          ['time_RTC_UTC', 0, 'mysql_milli_datetime', "secondary_index"],
                          ['PPS_UTC', 0, 'mysql_micro_datetime', 'nullable'],
                          ['PPSR_EPOCH', 0, 'mysql_milli_datetime', 'nullable'],
                          ['PPSS_EPOCH', 0, 'mysql_micro_datetime', 'nullable'],
                          ['received_at', 0, 'uint', "nullable"],
                          ['packet_count', 0, 'uint'], 
                          ['granule_index', 0, 'uint'],
                          ]
        }

        # NOTE: if you change the table_structure, you need to clear the database/dataTypes.dtobj and database/dataTypes_backup.dtobj DO NOT delete the file, just delete everything in side the file.
        sensor_parent.__init__(self, coms=self.__coms, config= self.__config, name=self.__name, db_name = sensor_config.database_name, table_structure=self.__table_structure, data_overwrite_exception = False)
        sensor_parent.set_sensor_status(self, 'Running')

        # conversion constants
        self.__FSR = 2.048
        self.__LSB = (self.__FSR*2) / (65536)
        self.__current_gain = 4.99
        # self.__sign_bit = 1 << (15) # 16 bit numbers

    def process_data(self, _):
        '''
            This function gets called when one of the tap request gets any data. 

            NOTE: This function always gets called no matter with tap gets data. 
        '''
        while sensor_parent.data_received_is_empty(self):
            data = sensor_parent.get_data_received(self, self.__config['tap_request'][0])
            # sensor_parent.save_data(self, table='STT_L1', data=data)
            # self.__logger.send_log(f"data: {data}\n")
            # return
            buffer = {
                'PPSW' : [],
                'PPSM' : [],
                'PPSS' : [],
                'PPSR' : [],
                '1ADC0' : [],
                '1ADC1' : [],
                '1ADC2' : [],
                '1ADC3' : [],
                '1ADCT' : [],
                '2ADC0' : [],
                '2ADC1' : [],
                '2ADC2' : [],
                '2ADC3' : [],
                '2ADCT' : [],
                '3ADC0' : [],
                '3ADC1' : [],
                '3ADC2' : [],
                '3ADC3' : [],
                '3ADCT' : [],
                '4ADC0' : [],
                '4ADC1' : [],
                '4ADC2' : [],
                '4ADC3' : [],
                '4ADCT' : [],
                'PAC' : [],
                'PHFC' : [],
                'PCFC' : [],
                'VERS' : [],
                'MODE1' : [],
                'H1S' : [],
                'H2S' : [],
                'H3S' : [],
                'H4S' : [],
                'H5S' : [],
                'H6S' : [],
                'REG_5V' : [],
                'GPS_C' : [],
                'DEBUG' : [],
                'time_STM_CLK' : [],
                'time_RTC' : [],
                'time_STM_CLK_UTC' : [],
                'time_RTC_UTC' : [],
                'PPS_UTC' : [],
                'PPSR_EPOCH' : [],
                'PPSS_EPOCH' : [],
                'received_at' : [],
                'packet_count' : [],
                'granule_index' : [],
            }

            for key in data:
                match key:
                    case '1ADC0':
                        buffer[key] = [(data[key][0] * self.__LSB) / self.__current_gain]
                    case '1ADC1':
                        buffer[key] = [(data[key][0] * self.__LSB) / (100/274)] 
                    case '1ADC2':
                        buffer[key] = [(data[key][0] * self.__LSB) / self.__current_gain]
                    case '1ADC3':
                        buffer[key] = [(data[key][0] * self.__LSB) / self.__current_gain]
                    case '1ADCT':
                        buffer[key] = [(data[key][0] >> 2) * 0.03125] # add in sign bit checking
                    case '2ADC0':
                        buffer[key] = [(data[key][0] * self.__LSB) / self.__current_gain]
                    case '2ADC1':
                        buffer[key] = [(data[key][0] * self.__LSB) / self.__current_gain]
                    case '2ADC2':
                        buffer[key] = [(data[key][0] * self.__LSB) / self.__current_gain]
                    case '2ADC3':
                        buffer[key] = [(data[key][0] * self.__LSB) / self.__current_gain]
                    case '2ADCT':
                        buffer[key] = [(data[key][0] >> 2) * 0.03125]
                    case '3ADC0':
                        buffer[key] = [(data[key][0] * self.__LSB) / (100/243)]
                    case '3ADC1':
                        buffer[key] = [(data[key][0] * self.__LSB) / (1/3)]
                    case '3ADC2':
                        buffer[key] = [(data[key][0] * self.__LSB) / (100/274)]
                    case '3ADC3':
                        buffer[key] = [(data[key][0] * self.__LSB)]
                    case '3ADCT':
                        buffer[key] = [(data[key][0] >> 2) * 0.03125]
                    case '4ADC0':
                        buffer[key] = [(data[key][0] * self.__LSB) / (51/151)]
                    case '4ADC1':
                        buffer[key] = [(data[key][0] * self.__LSB) / (1/2)]
                    case '4ADC2':
                        buffer[key] = [(data[key][0] * self.__LSB)]
                    case '4ADC3':
                        buffer[key] = [(data[key][0] * self.__LSB)]
                    case '4ADCT':
                        buffer[key] = [(data[key][0] >> 2) * 0.03125]
                    case _:
                        buffer[key] = [data[key]]
            # self.__logger.send_log(f"buffer: {buffer}\ntable: {self.__table_structure}\n\n")
            # return
            buf_copy = copy.deepcopy(buffer)
            # self.__logger.send_log(f"buffer: {buffer}\n\n")
            sensor_parent.save_data(self, table='STTA_L1', data=buf_copy)
            
