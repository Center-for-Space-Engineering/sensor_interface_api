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
    def __init__(self, packets_file_list:list, detector_list:list, processor_list:list, packet_processor_name:str = 'sobj_packet_processor') -> None:
        self.__sensors_class = []
        self.__sensors = []
        self.__packets_file_paths_list = packets_file_list
        self.__packet_processor_name = packet_processor_name
        self.__detector_list = detector_list
        self.__processor_list = processor_list
        self.__packets_struter = {}
        self.__source_list = {}

        for file_path in self.__packets_file_paths_list:
            # NOTE: we are going to use the file name to track our data
            
            #get the packet struture
            telemetry_packet_types = []
            count = 0

            with open(file_path, 'r') as file:
                try:
                    # Load the YAML content
                    temp_structur = yaml.safe_load(file)
                    self.__packets_struter.update(temp_structur)
                    self.__source_list[file_path] = list(temp_structur.keys())
                except yaml.YAMLError as exc:
                    print(f"Error reading YAML file: {exc}")
            
                #save all the Mnemonic, and APIDS we know about
                system_constants.vaild_apids[file_path] = list(temp_structur.keys())
                
                for packet in temp_structur:
                    telemetry_packet_types.append((temp_structur[packet]['Mnemonic'], packet, count)) # Mnemonic, APID, possition in a list
                    count += 1
            system_constants.telemetry_packet_types[file_path] = telemetry_packet_types
            system_constants.telemetry_packet_num[file_path] = count

        print(self.__source_list)

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
            if 'detect' in class_name:
                for detect in self.__detector_list:
                    sensor_class = getattr(module, class_name)
                    sensor_object = sensor_class(coms, name=detect)
                    self.__sensors.append(sensor_object)
            elif class_name == self.__packet_processor_name: #when we find the packet processor, create one for each packet. 
                for process in self.__processor_list:
                    for apid in self.__source_list[process[1]]:
                        sensor_class = getattr(module, class_name)
                        sensor_object = sensor_class(coms, process[0], self.__packets_struter[apid], apid)
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
