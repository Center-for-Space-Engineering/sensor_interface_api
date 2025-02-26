'''
    This module is for converting parsed TAM packets (L0 data) up to L1 data. 
'''

import copy
import datetime

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
import system_constants as sensor_config # pylint: disable=e0401
from logging_system_display_python_api.DTOs.print_message_dto import print_message_dto # pylint: disable=e0401
from logging_system_display_python_api.logger import loggerCustom as logger

class sobj_TAM_L0_to_L1_converter(sensor_parent):
    def __init__(self, coms):
        self.__name = 'TAM_L0_to_L1_converter'
        self.__config = sensor_config.sensors_config[self.__name]
        self.__coms = coms
        self.__data_received = []
        self.__logger = logger(f'logs/{self.__name}.txt')

        self.__table_structure = {
             'TAM_L1' : [ ['MBX', 0, 'float'], 
                          ['MBY', 0, 'float'], 
                          ['MBZ', 0, 'float'],
                          ['time_STM_CLK', 0, 'uint'],
                          ['time_RTC', 0, 'uint'], 
                          ['time_STM_CLK_UTC', 0, 'mysql_micro_datetime', "secondary_index"],
                          ['time_RTC_UTC', 0, 'mysql_milli_datetime', "secondary_index"],
                          ['received_at', 0, 'uint', "nullable"],
                          ['granule_index', 0, 'uint'],
                          ]
        }

        # NOTE: if you change the table_structure, you need to clear the database/dataTypes.dtobj and database/dataTypes_backup.dtobj DO NOT delete the file, just delete everything in side the file.
        sensor_parent.__init__(self, coms=self.__coms, config= self.__config, name=self.__name, db_name = sensor_config.database_name, table_structure=self.__table_structure)
        sensor_parent.set_sensor_status(self, 'Running')

        # conversion constants
        self.__CycleCounts = 200
        self.__TAMGain = (0.3671*self.__CycleCounts + 1.5)
        self.__sign_bit = 1 << (23) # 24 bit numbers

    def process_data(self, _):
        '''
            This function gets called when one of the tap request gets any data. 

            NOTE: This function always gets called no matter with tap gets data. 
        '''
        data = sensor_parent.get_data_received(self, self.__config['tap_request'][0])
        buffer = {
            'MBX' : [],
            'MBY' : [],
            'MBZ' : [],
            'time_STM_CLK' : [],
            'time_RTC' : [],
            'time_STM_CLK_UTC' : [],
            'time_RTC_UTC' : [],
            'received_at' : [],
            'granule_index' : [],
        }

        # self.__logger.send_log(f"data: {data}")

        for key in data:
            match key:
                case 'MBX':
                    buffer[key] = []
                    for val in data[key]:
                        # sign extension
                        converted = (val & (self.__sign_bit-1)) - (val & self.__sign_bit)
                        # gain conversion
                        converted = converted/self.__TAMGain
                        buffer[key].append(converted)
                case 'MBY':
                    buffer[key] = []
                    for val in data[key]:
                        # sign extension
                        converted = (val & (self.__sign_bit-1)) - (val & self.__sign_bit)
                        # gain conversion
                        converted = converted/self.__TAMGain
                        buffer[key].append(converted)
                case 'MBZ':
                    buffer[key] = []
                    for val in data[key]:
                        # sign extension
                        converted = (val & (self.__sign_bit-1)) - (val & self.__sign_bit)
                        # gain conversion
                        converted = converted/self.__TAMGain
                        buffer[key].append(converted)

                # case 'time_STM_CLK':
                #     buffer[key] = data[key]
                # case 'time_RTC':
                #     buffer[key] = data[key]
                # case 'granule_index':
                #     buffer[key] = data[key]
                case _ :
                    buffer[key] = data[key]


        # sensor_parent.save_data(self, table = 'TAM_L1', data = buffer)
