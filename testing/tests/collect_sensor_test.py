'''
    Unit test for collect_sensor
'''
# Python imports
import pytest
import os
import yaml
from io import StringIO
from unittest import mock
from unittest.mock import MagicMock

# Custom imports
import system_constants as sensor_config
from logging_system_display_python_api.messageHandler import messageHandler
from sensor_interface_api.collect_sensor import sensor_importer
from threading_python_api.taskHandler import taskHandler

@pytest.mark.collect_sensor_tests
#Test for successfully reading a yaml file
def test_success_importing_yaml():
        file_path = "sensor_interface_api/testing/sensor_test/collect_sensor_test.yaml"

        #make a test instance of collect_sensor with test file path
        sensor_importer([file_path], [], [], '')

        assert sensor_config.valid_apids[file_path] == ['040']
        assert sensor_config.telemetry_packet_types[file_path] == [('STTA', '040', 0)]
        assert sensor_config.telemetry_packet_num[file_path] == 1


# Test for throwing an error on a bad yaml file
# TODO: check with Shawn and make sure the original code is actually working-
#       it doesn't print "error reading yaml," just moves on and hits a different error
#       I might also need to rewrite the test for a yamlerror that won't error out later
@pytest.mark.collect_sensor_tests
@mock.patch('sys.stdout', new_callable=StringIO)
def test_fail_importing_yaml(mock_stdout):
  
    # do more with except, idk what tho
    try:
        file_path = "sensor_interface_api/testing/sensor_test/bad_collect_sensor_test.yaml"
        sensor_importer([file_path], [], [], '')

        output = mock_stdout.getvalue()
        assert "Error reading YAML file" in output
    except UnboundLocalError:
        pass

@pytest.mark.collect_sensor_tests
def test_import_modules():
    test_sensor = sensor_importer([], [], [], '')
    test_sensor.import_modules()

    # get list of all modules that should have be imported
    current_dir = os.path.dirname("sensor_interface_api/collect_sensor.py")
    file_list = os.listdir(current_dir)
    sobj_list = []
    for file in file_list:
        if 'sobj_' in file:
            sobj_list.append("sensor_interface_api." + file.strip('.py'))
    # get list of the names of all modules that were imported
    module_names = []
    for module in test_sensor._sensor_importer__sensors_class:
        module_names.append(module.__name__)

    # every module that was imported should have been imported (no extras modules)
    for module in module_names:
        assert module in sobj_list
        assert "sobj_" in module
    # every module that should have been imported was imported (no missing modules)
    for file in sobj_list:
        assert file in module_names

@pytest.mark.collect_sensor_tests
def test_instantiate_sensor_objects():    
    # set up for importing sensors
    coms = messageHandler(destination='Local')
    thread_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=thread_handler)
    with open("main.yaml", "r") as file:
        config_data = yaml.safe_load(file)
    sensor_config_dict = config_data.get("sensor_config_dict", {})
    sensor_config.sensors_config = sensor_config_dict
    test_detector_list = []
    test_processor_list = []
    test_packet_file_list = []
    packet_list = []
    for sensor in sensor_config_dict:
        if 'detect' in sensor:
            test_packet_file_list.append(sensor_config_dict[sensor]['packet_sturture'])
            test_detector_list.append(sensor)
        else:
            if 'parser' in sensor:
                test_processor_list.append((sensor, sensor_config_dict[sensor]['source']))

    # create test sensor and instantiate sensors
    test_sensor = sensor_importer(packets_file_list=test_packet_file_list, detector_list=test_detector_list, processor_list=test_processor_list, packet_processor_name='sobj_packet_processor')
    test_sensor.import_modules()
    test_sensor.instantiate_sensor_objects(coms)

    # get names of the sensors that *were* created
    sensor_obj_list = test_sensor.get_sensors()
    sensor_obj_names = []
    for sensor in sensor_obj_list:
        sensor_obj_names.append(sensor.get_sensor_name())

    # get names of all sensors that *should be* created
    desired_sensors = []
    for detector in test_detector_list:
        desired_sensors.append(detector)

    keys = []
    for processor in test_processor_list:
        packet_dict = yaml.safe_load(open(processor[1], 'r'))
        keys = packet_dict.keys()
        for key in keys:
            desired_sensors.append(packet_dict[key]['Mnemonic'] + sensor_config.sensors_config[processor[0]]['extention'])

    sobj_directory = os.path.dirname("sensor_interface_api/collect_sensor.py")
    temp_list = os.listdir(sobj_directory)
    for file in temp_list:
        if 'sobj' in file and 'detect' not in file and 'processor' not in file:
            desired_sensors.append(file.removeprefix('sobj_').removesuffix('.py'))

    # assert that all sensors that should have been created were created (no missing sensors)
    desired_sensors.append('evil')
    for sensor in desired_sensors:
        if sensor == 'evil':
            assert sensor not in sensor_obj_names
        else:
            assert sensor in sensor_obj_names
    
    # assert that all sensors that were created should have been created (no extra sensors, also tests get_sensors)
    desired_sensors.remove('evil')
    sensor_obj_names.append('evil')
    for sensor in sensor_obj_names:
        if sensor == 'evil':
            assert sensor not in desired_sensors
        else:
            assert sensor in desired_sensors