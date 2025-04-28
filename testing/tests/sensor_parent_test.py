'''
    Unit test for collect_sensor
'''

#For this class:
import pytest
from sensor_interface_api.sensor_parent import sensor_parent
import system_constants
from unittest import mock
from unittest.mock import MagicMock

#From sensor_parent class:
#python imports
import threading
import copy
import time
import re
from datetime import datetime

#Custom imports
from threading_python_api.threadWrapper import threadWrapper # pylint: disable=e0401
from sensor_interface_api.sensor_html_page_generator import sensor_html_page_generator # pylint: disable=e0401
import system_constants as sys_c # pylint: disable=e0401
from logging_system_display_python_api.logger import loggerCustom # pylint: disable=e0401

# @pytest.mark.sensor_parent_tests
# def test_init():
#     #this looks incredibly awful so I might skip this for now
#     pass

@pytest.mark.sensor_parent_tests
def test_set_up_taps():
        #test for tap_request != None, publisher == 'yes,' passive_active == 'active'
        test_parent = sensor_parent(coms=None, config={'tap_request': ['a'], 'publisher':'yes', 'passive_active':'active', 'interval_pub':0}, name='test_2')
        test_parent.make_data_tap = MagicMock()
        test_parent.start_publisher = MagicMock()
        test_parent.set_up_taps()
        
        test_parent.make_data_tap.assert_called_with('a')
        test_parent.start_publisher.assert_called_with

        #test for tap_request == None, passive_active == 'passive'
        test_parent = sensor_parent(coms=None, config={'tap_request': None, 'publisher':'yes', 'passive_active':'passive', 'interval_pub':0}, name='test_3')
        test_parent.make_data_tap = MagicMock()
        test_parent.start_publisher = MagicMock()
        test_parent.set_up_taps()

        assert test_parent.get_taps() == ['None']
        
        test_parent.start_publisher.assert_not_called
        assert test_parent._sensor_parent__active == False
        
        #test for publisher == 'no'
        test_parent = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'no', 'interval_pub':0}, name='test_1')
        test_parent.set_up_taps()
        test_parent.start_publisher = MagicMock()

        test_parent.start_publisher.assert_not_called
        assert test_parent._sensor_parent__active == False