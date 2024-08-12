'''
    This module is for converting parsed TAM packets (L0 data) up to L1 data. 
'''

import copy

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
import system_constants as sensor_config # pylint: disable=e0401
from logging_system_display_python_api.DTOs.print_message_dto import print_message_dto # pylint: disable=e0401

class sobj_TAM_L0_to_L1_converter(sensor_parent):
    def __init__(self, coms):
        self.__name = 'TAM_L0_to_L1_converter'
        self.__config = sensor_config.sensors_config[self.__name]
        self.__coms = coms
        self.__data_received = []

        self.__table_structure = {
             'TAM_L1' : [ ['MBX', 0, 'float'], 
                          ['MBY', 0, 'float'], 
                          ['MBZ', 0, 'float'], ]
        }

        # NOTE: if you change the table_structure, you need to clear the database/dataTypes.dtobj and database/dataTypes_backup.dtobj DO NOT delete the file, just delete everything in side the file.
        sensor_parent.__init__(self, coms=self.__coms, config= self.__config, name=self.__name, db_name = sensor_config.database_name, table_structure=self.__table_structure)
        sensor_parent.set_sensor_status(self, 'Running')

    def process_data(self, _):
        '''
            This function gets called when one of the tap request gets any data. 

            NOTE: This function always gets called no matter with tap gets data. 
        '''
        # print("Here")
        self.__data_received = sensor_parent.get_data_received(self, self.__config['tap_request'][0])
        buffer = {}

        print(self.__data_received)

        # for key in self.__data_received:
        #     print(key + ':')
        #     print(self.__data_received[key])

        # print('\n\n\n')

        # for parsed_packet in data:
        #     for key in parsed_packet:
        #         match key:
        #             case 'MBX':
        #                 buffer[key] = []
        #                 for val in parsed_packet[key]:
        #                     buffer[key].append(val)
        #             case 'MBY':
        #                 buffer[key] = []
        #                 for val in parsed_packet[key]:
        #                     buffer[key].append(val)
        #             case 'MBZ':
        #                 buffer[key] = []
        #                 for val in parsed_packet[key]:
        #                     buffer[key].append(val)

        # print(buffer)