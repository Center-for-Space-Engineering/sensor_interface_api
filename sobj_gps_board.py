from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
from threading_python_api.threadWrapper import threadWrapper # pylint: disable=e0401
from sensor_interface_api import system_constants as sensor_config # pylint: disable=e0401

class sobj_gps_board(sensor_parent, threadWrapper):
    def __init__(self, coms):
        sensor_parent.__init__(self, coms)
        self.__name = 'gps board'
        # print(sensor_config.serial_port_one)
    def get_sensor_name(self):
        return self.__name