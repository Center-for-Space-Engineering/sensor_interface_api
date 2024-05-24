'''
    This modules imports all the sensors that the user has defined.
'''
import os
import importlib
import yaml

import system_constants # pylint: disable=e0401

class sensor_importer():
    '''
        Any file that is found in the sensor_interface_api/, starts with "sobj_", and ends with ".py" 
    '''
    def __init__(self, packets_file:str, packet_processor_name:str = 'sobj_packet_processor') -> None:
        self.__sensors_class = []
        self.__sensors = []
        self.__packets_file_path = packets_file
        self.__packet_processor_name = packet_processor_name

        #get the packet struture
        with open(self.__packets_file_path, 'r') as file:
            try:
                # Load the YAML content
                self.__packets_struter = yaml.safe_load(file)
            except yaml.YAMLError as exc:
                print(f"Error reading YAML file: {exc}")
                self.__packets_struter = None
        
        #save all the Mnemonic, and APIDS we know about
        system_constants.vaild_apids = list(self.__packets_struter.keys())
        telemetry_packet_types = []
        count = 0
        for packet in self.__packets_struter:
            telemetry_packet_types.append((self.__packets_struter[packet]['Mnemonic'], packet, count)) # Mnemonic, APID, possition in a list
            count += 1
        system_constants.telemetry_packet_types = telemetry_packet_types

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
            if class_name == self.__packet_processor_name: #when we find the packet processor, create one for each packet. 
                for apid in system_constants.vaild_apids:
                    sensor_class = getattr(module, class_name)
                    sensor_object = sensor_class(coms, self.__packets_struter[apid], apid)
                    self.__sensors.append(sensor_object)
            else : 
                sensor_class = getattr(module, class_name)
                sensor_object = sensor_class(coms)
                self.__sensors.append(sensor_object)
    def get_sensors(self):
        '''
            returns all the sensor objects. 
        '''
        return self.__sensors
