import random

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
from threading_python_api.threadWrapper import threadWrapper # pylint: disable=e0401
from sensor_interface_api import system_constants as sensor_config # pylint: disable=e0401

class sobj_gps_board(sensor_parent):
    def __init__(self, coms):
        self.__name = 'gps_board'
        self.__graphs = ['num gps packets received']
        self.__config = sensor_config.sensors_config[self.__name]
        self.__serial_line_two_data = []
        # the structure here is a dict where the key is the name of the table you want to make and the value is a list of list that has your row information on each sub index.
        # the row structure is [<table name>, bit count (zero if you dont care), type (int, float, string, bool, bigint, byte)]
        self.__table_structure = {
            f'processed_data_for_{self.__name}' : [['gps_packets', 0, 'string'], ['test_data', 10, 'int']],
            f'processed_data_for_{self.__name}_table_2' : [['gps_packets', 0, 'string'], ['test_data', 10, 'int']],

        }

        # NOTE: if you change the table_structure, you need to clear the database/dataTypes.dtobj and database/dataTypes_backup.dtobj DO NOT delete the file, just delete everything in side the file.
        sensor_parent.__init__(self, coms=coms, config= self.__config, name=self.__name, graphs=self.__graphs, max_data_points=100, db_name = sensor_config.database_name, table_structure=self.__table_structure)
        sensor_parent.set_sensor_status(self, 'Running')
        
    def process_data(self, event):
        '''
            This function gets called when one of the tap request gets any data. 

            NOTE: This function always gets called no matter with tap gets data. 
        '''
        y = [random.random() for _ in range(100)]
        x = [i for i in range(100)] 
        sensor_parent.add_graph_data(self, graph=self.__graphs[0], x=x, y=y)
        data = [[1,2,3], [4,5,6]]
        sensor_parent.set_publish_data(self, data=data)
        sensor_parent.publish(self)
        print(f'Event called: {event}')
        print(sensor_parent.get_data_received(self, self.__config['tap_request'][0]))
        data = {
            'gps_packets' : ['hello', 'hello'],
            'test_data' : [10, 10]
        }
        sensor_parent.save_data(self, table = f'processed_data_for_{self.__name}', data = data)