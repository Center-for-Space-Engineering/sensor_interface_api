import random

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
from threading_python_api.threadWrapper import threadWrapper # pylint: disable=e0401
from sensor_interface_api import system_constants as sensor_config # pylint: disable=e0401

class sobj_gps_board(sensor_parent):
    def __init__(self, coms):
        self.__name = 'gps_board'
        self.__graphs = ['num gps packets received']
        self.__config = sensor_config.sensors_config[self.__name]
        sensor_parent.__init__(self, coms=coms, config= self.__config, name=self.__name, graphs=self.__graphs, max_data_points=100)
        sensor_parent.set_sensor_status(self, 'Running')
        
    def process_data(self):
        y = [random.random() for _ in range(100)]
        x = [i for i in range(100)] 
        sensor_parent.add_graph_data(self, graph=self.__graphs[0], x=x, y=y)
        data = [[1,2,3], [4,5,6]]
        sensor_parent.set_publish_data(self, data=data)
        sensor_parent.publish(self)
        print(sensor_parent.get_data_received(self, self.__config['tap_request'][0]))