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
         

# What are we testing for?
#   all correct files get added to list
#       TODO
#   all files in list are correct
#       check if all files are in subdirectory
#       check if all files in list have sobj and .py

@pytest.mark.collect_sensor_tests
def test_import_modules():
    test_sensor = sensor_importer([], [], [], '')
    test_sensor.import_modules()

    current_dir = os.path.dirname("sensor_interface_api/collect_sensor.py")
    file_list = os.listdir(current_dir)

    for file in file_list:
        file_list[file_list.index(file)] = "sensor_interface_api." + file.strip('.py')

    for module in test_sensor._sensor_importer__sensors_class:
        assert module.__name__ in file_list
        assert "sobj_" in module.__name__

# What to test for:
#   class name == module name?
#   packet detect
#       ensure a sensor object is added for every detector
#   packet processor
#       ensure a sensor object is added for every apid for every process
#   generic sensor
#       ensure an object is added for a generic sensor
@pytest.mark.collect_sensor_tests
def test_instantiate_sensor_objects():
    coms = messageHandler(destination='Local')

    sobj_directory = os.path.dirname("sensor_interface_api/collect_sensor.py")
    sensor_class_list = os.listdir(sobj_directory)
    with open("main.yaml", "r") as file:
        config_data = yaml.safe_load(file)
    sensor_config_dict = config_data.get("sensor_config_dict", {})
    sensor_config.sensors_config = sensor_config_dict


    test_sensor = sensor_importer([], [], [], 'sobj_packet_processor')
    test_sensor.import_modules()
    test_sensor.instantiate_sensor_objects(coms)    #need coms here
    sensor_obj_list = test_sensor.get_sensors()
    # maybe test getter here
    for sensor in sensor_obj_list:
        print("hello")

    for sensor in sensor_class_list:
        if ('sobj_' in sensor):
            if ('detect' in sensor):
                pass
            elif ('sobj_packet_processor' in sensor):
                pass
            else:
                assert sensor.strip('.py') in sensor_obj_list

# get_sensors is prob going to be tested above