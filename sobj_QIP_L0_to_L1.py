'''
    This module is for converting parsed QIP packets (L0 data) up to L1 data. 
'''

import math

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
import system_constants as sensor_config # pylint: disable=e0401
from logging_system_display_python_api.logger import loggerCustom as logger

class sobj_QIP_L0_to_L1(sensor_parent):
    '''
        raises QIP from L0 to L1
    '''
    def __init__(self, coms):
        self.__name = 'QIP_L0_to_L1'
        self.__config = sensor_config.sensors_config[self.__name]
        self.__coms = coms
        self.__logger = logger(f'logs/{self.__name}.txt') # pylint: disable=W0238

        self.__table_structure = {
             'QIP_L1' : [ ['TFQ', 0, 'float'], 
                          ['IiS', 0, 'float'], 
                          ['IQS', 0, 'float'], 
                          ['Mag', 0, 'float'],
                          ['Phase', 0, 'float'], 
                          ['time_STM_CLK', 0, 'uint'],
                          ['time_RTC', 0, 'uint'],
                          ['time_STM_CLK_UTC', 0, 'mysql_micro_datetime', "secondary_index"],
                          ['time_RTC_UTC', 0, 'mysql_milli_datetime', "secondary_index"],
                          ['received_at', 0, 'uint', "nullable"],
                          ['packet_count', 0, 'uint'],
                          ['granule_index', 0, 'uint'],
                          ]
        }

        # NOTE: if you change the table_structure, you need to clear the database/dataTypes.dtobj and database/dataTypes_backup.dtobj DO NOT delete the file, just delete everything in side the file.
        sensor_parent.__init__(self, coms=self.__coms, config= self.__config, name=self.__name, db_name = sensor_config.database_name, table_structure=self.__table_structure)
        sensor_parent.set_sensor_status(self, 'Running')

        # conversion constants
        # self.__CycleCounts = 200
        self.__QIP_freq_Gain = 1/(1.25e-8 * (2**24) * 1e6)
        self.__QIP_freq_Offset = 0
        self.__QIP_I_Gain = 1/(2**18)
        self.__QIP_I_Offset = 0
        self.__QIP_Q_Gain = 1/(2**18)
        self.__QIP_Q_Offset = 0
        self.__sign_bit = 1 << (19) # 20 bit numbers

    def process_data(self, _):
        '''
            This function gets called when one of the tap request gets any data. 

            NOTE: This function always gets called no matter with tap gets data. 
        '''
        while sensor_parent.data_received_is_empty(self):
            data = sensor_parent.get_data_received(self, self.__config['tap_request'][0])
            buffer = {
                'TFQ' : [],
                'IiQ' : [],
                'IQQ' : [],
                'Mag' : [],
                'Phase' : [],
                'time_STM_CLK' : [],
                'time_RTC' : [],
                'time_STM_CLK_UTC' : [],
                'time_RTC_UTC' : [],
                'received_at' : [],
                'packet_count' : [],
                'granule_index' : [],
            }

            # self.__logger.send_log(f"data: {type(data)}")

            for key in data:
                # self.__logger.send_log(f"key: {key}")
                match key:
                    case 'TFQ':
                        buffer[key] = []
                        for val in data[key]:                        
                            # gain conversion
                            # freq = val/(self.__TIP_ts * (2**self.__TIP_N))
                            freq = val
                            converted = freq*self.__QIP_freq_Gain + self.__QIP_freq_Offset
                            buffer[key].append(converted)
                    case 'IiQ':
                        buffer[key] = []
                        for val in data[key]:
                            # sign extension
                            converted = (val & (self.__sign_bit-1)) - (val & self.__sign_bit)
                            # gain conversion
                            converted = converted*self.__QIP_I_Gain + self.__QIP_I_Offset
                            # # RAW values
                            # converted = val
                            buffer[key].append(converted)
                    case 'IQQ':
                        buffer[key] = []
                        for val in data[key]:
                            # sign extension
                            converted = (val & (self.__sign_bit-1)) - (val & self.__sign_bit)
                            # gain conversion
                            converted = converted*self.__QIP_Q_Gain + self.__QIP_Q_Offset
                            # # RAW values
                            # converted = val
                            buffer[key].append(converted)

                    case 'time_STM_CLK':
                        buffer[key] = data[key]
                    case 'time_RTC':
                        buffer[key] = data[key]
                    case 'granule_index':
                        buffer[key] = data[key]
                    case _ :
                        buffer[key] = data[key]
            # self.__logger.send_log(f"buffer: {buffer}")

            buffer['Mag'] = [math.sqrt(x[0]**2 + x[1]**2) for x in zip(buffer['IiQ'], buffer['IQQ'])]
            buffer['Phase'] = [math.atan2(x[1], x[0]) for x in zip(buffer['IiQ'], buffer['IQQ'])]

            # self.__logger.send_log(str(buffer))



            sensor_parent.save_data(self, table = 'QIP_L1', data = buffer)
