'''
    This modules imports all the sensors that the user has defined.
'''
import os
import importlib

class sensor_importer():
    '''
        Any file that is found in the sensor_interface_api/, starts with "sobj_", and ends with ".py" 
    '''
    def __init__(self) -> None:
        self.__sensors_class = []
        self.__sensors = []
    def import_modules(self):
        '''
            this function import modules
        '''
        sub_folder_path = os.path.dirname(__file__)
        for file_name in os.listdir(sub_folder_path):
            if file_name.endswith('.py') and file_name != '__init__.py' and "sobj_" in file_name:
                module_name = os.path.splitext(file_name)[0]
                module = importlib.import_module(f'sensor_interface_api.{module_name}', package=__name__)
                self.__sensors_class.append(module)
    def instantiate_sensor_objects(self, coms):
        '''
            This function instantiates all the sensor objects it found. 
        '''
        for module in self.__sensors_class:
            # Assuming your class name is the same as your module name (but capitalized)
            class_name = module.__name__.split('.')[-1]
            sensor_class = getattr(module, class_name)
            sensor_object = sensor_class(coms)
            self.__sensors.append(sensor_object)
    def get_sensors(self):
        '''
            returns all the sensor objects. 
        '''
        return self.__sensors
