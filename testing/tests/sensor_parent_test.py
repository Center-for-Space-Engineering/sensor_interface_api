'''
    Unit test for collect_sensor
'''

#Python imports
import pytest
import yaml
from unittest.mock import MagicMock

#Custom imports
from threading_python_api.taskHandler import taskHandler
import system_constants as sensor_config
from sensor_interface_api.sensor_parent import sensor_parent
from sensor_interface_api.sobj_gps_board_aux import sobj_gps_board_aux
from logging_system_display_python_api.messageHandler import messageHandler

@pytest.mark.sensor_parent_tests
def test_init():
    #this looks incredibly awful so I might skip this for now
    pass

@pytest.mark.sensor_parent_tests
def test_set_up_taps():
    #test for one tap, passive_active == 'active'
    test_parent = sensor_parent(coms=None, config={'tap_request': ['a'], 'publisher': 'yes', 'passive_active': 'active', 'interval_pub': 0}, name='test_2')
    test_parent.make_data_tap = MagicMock()
    test_parent.start_publisher = MagicMock()
    test_parent.set_up_taps()
    
    test_parent.make_data_tap.assert_called_with('a')
    assert test_parent.get_taps() == ['a']
    assert test_parent._sensor_parent__active == True
    test_parent.start_publisher.assert_called_with

    #test for multiple taps, passive_active == 'passive'
    test_parent = sensor_parent(coms=None, config={'tap_request': ['a', 'b', 'c'], 'publisher': 'yes', 'passive_active': 'passive', 'interval_pub': 0}, name='test_2')
    test_parent.make_data_tap = MagicMock()
    test_parent.start_publisher = MagicMock()
    test_parent.set_up_taps()
    
    test_parent.make_data_tap.assert_called_with('c')
    assert test_parent.get_taps() == ['a', 'b', 'c']
    assert test_parent._sensor_parent__active == False
    test_parent.start_publisher.assert_not_called

    #test for tap_request == None
    test_parent = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'yes', 'passive_active':'passive', 'interval_pub': 0}, name='test_3')
    test_parent.make_data_tap = MagicMock()
    test_parent.start_publisher = MagicMock()
    test_parent.set_up_taps()

    assert test_parent.get_taps() == ['None']
    
    #test for publisher == 'no'
    test_parent = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'no', 'interval_pub': 0}, name='test_1')
    test_parent.set_up_taps()
    test_parent.start_publisher = MagicMock()

    test_parent.start_publisher.assert_not_called
    assert test_parent._sensor_parent__active == False

@pytest.mark.sensor_parent_tests
def test_get_name():
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': None, 'interval_pub': None}, name='Shawn')
    assert test_sensor.get_sensor_name() == 'Shawn'