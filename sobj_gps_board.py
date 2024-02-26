from sensor_interface_api.sensor_parent import sensor_parent

class sobj_gps_board(sensor_parent):
    def __init__(self, coms):
        super().__init__(coms)