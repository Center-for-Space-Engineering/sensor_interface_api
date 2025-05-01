'''
    Unit test for collect_sensor
'''

#Python imports
import pytest
import yaml
from unittest.mock import MagicMock
from unittest import mock
from io import StringIO
import threading
from pytest import ExceptionInfo

#Custom imports
from threading_python_api.threadWrapper import threadWrapper
from threading_python_api.taskHandler import taskHandler
import system_constants as sensor_config
from sensor_interface_api.sensor_parent import sensor_parent
from sensor_interface_api.sobj_gps_board_aux import sobj_gps_board_aux
from logging_system_display_python_api.messageHandler import messageHandler

@pytest.mark.sensor_parent_tests
def test_init():
    #this looks incredibly awful so I might skip this for now
    pass

#TODO: maybe also test get and create tap funcs here?
@pytest.mark.sensor_parent_tests
def test_set_up_taps():
    #test for one tap, passive_active == 'active'
    test_sensor = sensor_parent(coms=None, config={'tap_request': ['a'], 'publisher': 'yes', 'passive_active': 'active', 'interval_pub': 0}, name='tap_test_1')
    test_sensor.make_data_tap = MagicMock()
    test_sensor.start_publisher = MagicMock()
    test_sensor.set_up_taps()
    
    test_sensor.make_data_tap.assert_called_with('a')
    assert test_sensor.get_taps() == ['a']
    assert test_sensor._sensor_parent__active == True
    test_sensor.start_publisher.assert_called_with

    #test for multiple taps, passive_active == 'passive'
    test_sensor = sensor_parent(coms=None, config={'tap_request': ['a', 'b', 'c'], 'publisher': 'yes', 'passive_active': 'passive', 'interval_pub': 0}, name='tap_test_2')
    test_sensor.make_data_tap = MagicMock()
    test_sensor.start_publisher = MagicMock()
    test_sensor.set_up_taps()
    
    test_sensor.make_data_tap.assert_called_with('c')
    assert test_sensor.get_taps() == ['a', 'b', 'c']
    assert test_sensor._sensor_parent__active == False
    test_sensor.start_publisher.assert_not_called

    #test for tap_request, publisher, and passive_active == None
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': None, 'passive_active': None, 'interval_pub': 0}, name='tap_test_3')
    test_sensor.make_data_tap = MagicMock()
    test_sensor.start_publisher = MagicMock()
    test_sensor.set_up_taps()

    assert test_sensor.get_taps() == ['None']
    assert test_sensor._sensor_parent__active == False
    test_sensor.start_publisher.assert_not_called
    
    #test for publisher == 'no'
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'no', 'interval_pub': 0}, name='tap_test_4')
    test_sensor.set_up_taps()
    test_sensor.start_publisher = MagicMock()

    test_sensor.start_publisher.assert_not_called
    assert test_sensor._sensor_parent__active == False

@pytest.mark.sensor_parent_tests
def test_get_html_page():
    # test with lock acquired
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': None, 'interval_pub': None}, name='html_test')
    test_sensor.generate_html_file = MagicMock()
    test_sensor.generate_html_file.return_value = 'file/path'
    result = test_sensor.get_html_page()

    test_sensor.generate_html_file.assert_called_with('templates/html_test.html')
    assert result == 'file/path'
    assert test_sensor._sensor_parent__html__lock.locked() == False

    # test without lock acquired:
    test_sensor._sensor_parent__html__lock.acquire()
    if test_sensor._sensor_parent__html__lock.locked():
        with pytest.raises(RuntimeError) as excinfo:
            test_sensor.get_html_page()

        test_sensor._sensor_parent__html__lock.release()
        assert "Could not acquire html lock" in str(excinfo.value)
        assert test_sensor._sensor_parent__html__lock.locked() == False

@pytest.mark.sensor_parent_tests
def test_get_set_sensor_status():
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': None, 'interval_pub': None}, name='sensor_status_test')

    # test for all valid inputs
    assert test_sensor.get_sensor_status() == 'Not Running'
    assert test_sensor._sensor_parent__status_lock.locked() == False

    possible_status = ['Running', 'Error', 'Not Running']
    for status in possible_status:
        test_sensor.set_sensor_status(status)
        assert test_sensor._sensor_parent__status_lock.locked() == False

        assert test_sensor.get_sensor_status() == status
        assert test_sensor._sensor_parent__status_lock.locked() == False

    # test for invalid input
    with pytest.raises(RuntimeError) as excinfo:
        test_sensor.set_sensor_status('bad')
    
    assert "bad is not a valid status" in str(excinfo.value)
    assert test_sensor._sensor_parent__status_lock.locked() == False
    assert test_sensor.get_sensor_status() == 'Not Running'
    assert test_sensor._sensor_parent__status_lock.locked() == False

    # test for set_sensor_status failing to get lock
    test_sensor._sensor_parent__status_lock.acquire()
    if test_sensor._sensor_parent__status_lock.locked():
        with pytest.raises(RuntimeError) as excinfo:
            test_sensor.set_sensor_status('Running')
        
        print('here')
        test_sensor._sensor_parent__status_lock.release()
        assert 'Could not acquire status lock' in str(excinfo.value)
        assert test_sensor._sensor_parent__status_lock.locked() == False
        assert test_sensor.get_sensor_status() == 'Not Running'

    # test for get_sensor_status failing to get lock
    test_sensor._sensor_parent__status_lock.acquire()
    if test_sensor._sensor_parent__status_lock.locked():
        with pytest.raises(RuntimeError) as excinfo:
            test_sensor.get_sensor_status()
        
        test_sensor._sensor_parent__status_lock.release()
        assert 'Could not acquire status lock' in str(excinfo.value)
        assert test_sensor._sensor_parent__status_lock.locked() == False

#NOTE: as of right now, there are no checks for invalid statuses, so there is no test for such cases. Maybe we add checks in the future.
@pytest.mark.sensor_parent_tests
def test_set_thread_status():
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': None, 'interval_pub': None}, name='thread_status_test')

    # test for each status case
    possible_status = ['Running', 'Error', 'Not Running']
    for status in possible_status:
        test_sensor.set_thread_status(status)
        assert threadWrapper.get_status(test_sensor) == status

#TODO: possibly figure out how to change data_buffer_overwrite not manually
@pytest.mark.sensor_parent_tests
def test_ready_for_data():
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': None, 'interval_pub': None}, name='test_data_ready')
    assert test_sensor.ready_for_data() == True

    test_sensor._sensor_parent__data_buffer_overwrite = True
    assert test_sensor.ready_for_data() == False

@pytest.mark.sensor_parent_tests
def test_process_data():
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': None, 'interval_pub': None}, name='test_process')
    with pytest.raises(NotImplementedError) as excinfo:
        test_sensor.process_data(None)
    assert "process_data Not implemented, should process that last data received (data is stored in the __data_received variable)." in str(excinfo.value)

@pytest.mark.sensor_parent_tests
def test_get_data():
    # create a tap
    coms = messageHandler(destination='Local')
    thread_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=thread_handler)
    sender = sensor_parent(coms=coms, config={'tap_request': None, 'publisher': None, 'interval_pub': None}, name='sender')
    receiver = sensor_parent(coms=coms, config={'tap_request': ['sender'], 'publisher': None, 'interval_pub': None}, name='receiver')
    receiver.set_up_taps()
    assert receiver.get_taps() == ['sender']

    # ensure data_buffer_overwrite is false (ready for data)
    assert receiver.ready_for_data()

    # sender.send_tap(data, 'receiver')

    # return val is the same as data received from the tap
    # from threadHandler, if event (data received from ___) is true, then it calls the function
    # in this case, that'll be process_data, which calls get_data_received in every sobj
    # so that means I need to
    #   1. have sender call send_tap (sends data over)
    #   2. have receiver call... publish? something else? how does it know when data is received again??

    # steps for testing:
    #
    #   test for failing to acquire data_buffer_overwrite lock
    #   test for failing to acquire data lock

    # potential issue- if we wanted to add more requests to a sensor (specifically looking at lip l0 to l1) it may not listen to all
    # but I think this will be covered in the sensor specific tests so i'll just assume we good

@pytest.mark.sensor_parent_tests
def test_get_sensor_name():
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': None, 'interval_pub': None}, name='Liz')
    assert test_sensor.get_sensor_name() == 'Liz'
    