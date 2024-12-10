'''
    This module is for converting parsed TIP packets (L0 data) up to L1 data. 
'''

import copy
import datetime
import math

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
import system_constants as sensor_config # pylint: disable=e0401
from logging_system_display_python_api.DTOs.print_message_dto import print_message_dto # pylint: disable=e0401
from logging_system_display_python_api.logger import loggerCustom as logger

class sobj_TIP_L0_to_L1(sensor_parent):
    def __init__(self, coms):
        self.__name = 'TIP_L0_to_L1'
        self.__config = sensor_config.sensors_config[self.__name]
        self.__coms = coms
        self.__logger = logger(f'logs/{self.__name}.txt')

        self.__table_structure = {
             'TIP_L1' : [ ['TFQ', 0, 'float'], 
                          ['time_STM_CLK', 0, 'uint'],
                          ['time_RTC', 0, 'uint'], ]
        }

        # NOTE: if you change the table_structure, you need to clear the database/dataTypes.dtobj and database/dataTypes_backup.dtobj DO NOT delete the file, just delete everything in side the file.
        sensor_parent.__init__(self, coms=self.__coms, config= self.__config, name=self.__name, db_name = sensor_config.database_name, table_structure=self.__table_structure)
        sensor_parent.set_sensor_status(self, 'Running')

        # conversion constants
        self.__CycleCounts = 200
        self.__TIP_ts = 1/80e6
        self.__TIP_N = 24
        self.__TIP_freq_Gain = 1/1e6
        self.__TIP_freq_Offset = 0

    def process_data(self, _):
        '''
            This function gets called when one of the tap request gets any data. 

            NOTE: This function always gets called no matter with tap gets data. 
        '''
        data = sensor_parent.get_data_received(self, self.__config['tap_request'][0])
        buffer = {
            'TFQ' : [],
            'time_STM_CLK' : [],
            'time_RTC' : [],
        }

        self.__logger.send_log(f"data: {type(data)}")

        for key in data:
            match key:
                case 'TFQ':
                    buffer[key] = []
                    for val in data[key]:                        
                        # gain conversion
                        freq = val/(self.__TIP_ts * (2**self.__TIP_N))
                        # freq = val
                        converted = freq*self.__TIP_freq_Gain + self.__TIP_freq_Offset
                        buffer[key].append(converted)

                case 'time_STM_CLK':
                    buffer[key] = data[key]
                case 'time_RTC':
                    buffer[key] = data[key]

        self.__logger.send_log(str(buffer))

        sensor_parent.save_data(self, table = 'TIP_L1', data = buffer)
