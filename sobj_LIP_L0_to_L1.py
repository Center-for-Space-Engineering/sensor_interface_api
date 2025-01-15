'''
    This module is for converting parsed LIP packets (L0 data) up to L1 data. 
'''

import copy
import datetime
import math

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
import system_constants as sensor_config # pylint: disable=e0401
from logging_system_display_python_api.DTOs.print_message_dto import print_message_dto # pylint: disable=e0401
from logging_system_display_python_api.logger import loggerCustom as logger

class sobj_LIP_L0_to_L1(sensor_parent):
    def __init__(self, coms):
        self.__name = 'LIP_L0_to_L1'
        self.__config = sensor_config.sensors_config[self.__name]
        self.__coms = coms
        self.__logger = logger(f'logs/{self.__name}.txt')

        self.__table_structure = {
             'LIP_L1' : [ ['IiS', 0, 'float'], 
                          ['IQS', 0, 'float'], 
                        #   ['IQS_1', 0, 'float'], 
                          ['Mag', 0, 'float'],
                          ['Phase', 0, 'float'], 
                          ['time_STM_CLK', 0, 'uint'],
                          ['time_RTC', 0, 'uint'],
                          ['granule_index', 0, 'uint'],
             ]
        }

        # NOTE: if you change the table_structure, you need to clear the database/dataTypes.dtobj and database/dataTypes_backup.dtobj DO NOT delete the file, just delete everything in side the file.
        sensor_parent.__init__(self, coms=self.__coms, config= self.__config, name=self.__name, db_name = sensor_config.database_name, table_structure=self.__table_structure)
        sensor_parent.set_sensor_status(self, 'Running')

        # conversion constants
        self.__CycleCounts = 200
        # self.__LIP_I_Gain = 1/(2**18)
        # self.__LIP_I_Offset = 0
        # self.__LIP_Q_Gain = 1/(2**18)
        # self.__LIP_Q_Offset = 0
        self.__LIP_I_Gain = 1
        self.__LIP_I_Offset = 0
        self.__LIP_Q_Gain = 1
        self.__LIP_Q_Offset = 0
        self.__sign_bit = 1 << (19) # 20 bit numbers

    def process_data(self, _):
        '''
            This function gets called when one of the tap request gets any data. 

            NOTE: This function always gets called no matter with tap gets data. 
        '''
        data = sensor_parent.get_data_received(self, self.__config['tap_request'][0])
        buffer = {
            'IiS' : [],
            'IQS' : [],
            # 'IQS_1' : [],
            'Mag' : [],
            'Phase' : [],
            'time_STM_CLK' : [],
            'time_RTC' : [],
            'granule_index':[],

        }

        self.__logger.send_log(f"data: {type(data)}")

        for key in data:
            # self.__logger.send_log(f"key: {key}")
            match key:
                case 'IiS':
                    buffer[key] = []
                    for val in data[key]:
                        # sign extension
                        # converted = (val & (self.__sign_bit-1)) - (val & self.__sign_bit)
                        converted = val
                        # gain conversion
                        converted = converted*self.__LIP_I_Gain + self.__LIP_I_Offset
                        # # RAW values
                        # converted = val
                        buffer[key].append(converted)
                case 'IQS':
                    buffer[key] = []
                    for val in data[key]:
                        # sign extension
                        converted = (val & (self.__sign_bit-1)) - (val & self.__sign_bit)
                        # converted = val
                        # gain conversion
                        converted = converted*self.__LIP_Q_Gain + self.__LIP_Q_Offset
                        # # RAW values
                        # converted = val
                        buffer[key].append(converted)
                # case 'IQS_1':
                #     buffer[key] = []
                #     for val in data[key]:
                #         # sign extension
                #         converted = (val & (self.__sign_bit-1)) - (val & self.__sign_bit)
                #         # gain conversion
                #         converted = converted*self.__LIP_Q_Gain + self.__LIP_Q_Offset
                #         # # RAW values
                #         # converted = val
                #         buffer[key].append(converted)

                case 'time_STM_CLK':
                    buffer[key] = data[key]
                case 'time_RTC':
                    buffer[key] = data[key]
                case 'granule_index':
                    buffer[key] = data[key]

        # self.__logger.send_log(f"buffer: {buffer}")

        buffer['Mag'] = [math.sqrt(x[0]**2 + x[1]**2) for x in zip(buffer['IiS'], buffer['IQS'])]
        buffer['Phase'] = [math.atan2(x[1], x[0]) for x in zip(buffer['IiS'], buffer['IQS'])]


        # buffer['Mag'] = [math.floor(x[0] / (2**10)) for x in zip(buffer['IQS'])]
        # buffer['Phase'] = [x[0] - (math.floor(x[0] / (2**10)) * 2**10) for x in zip(buffer['IQS'])]

        self.__logger.send_log(str(buffer))

        sensor_parent.save_data(self, table = 'LIP_L1', data = buffer)
