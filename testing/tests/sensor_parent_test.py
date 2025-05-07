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
import time

#Custom imports
from threading_python_api.threadWrapper import threadWrapper
from threading_python_api.taskHandler import taskHandler
import system_constants as sensor_config
from sensor_interface_api.sensor_parent import sensor_parent
from sensor_interface_api.sobj_gps_board_aux import sobj_gps_board_aux
from logging_system_display_python_api.messageHandler import messageHandler
from database_python_api.database_control import DataBaseHandler

@pytest.mark.sensor_parent_tests
def test_init():
    # naming: valid names accepted, invalid names rejected
    DataBaseHandler.create_table_external = MagicMock()

    with pytest.raises(RuntimeError) as excinfo:
        test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': None, 'interval_pub': None}, name='bad\0')
    assert "The name bad\0, is not a valid sensor name" in str(excinfo.value)
    
    with pytest.raises(RuntimeError) as excinfo:
        test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': None, 'interval_pub': None}, name='bad/')
    assert "The name bad/, is not a valid sensor name" in str(excinfo.value)

    coms = messageHandler()
    dataBase = DataBaseHandler(coms, db_name='dataBase')
    thread_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=thread_handler)

    coms.send_request = MagicMock()
    test_sensor = sensor_parent(coms=coms, config={'tap_request': None, 'publisher': None, 'interval_pub': None}, name='good', db_name='dataBase', table_structure={'name': ['row', 0, 'int']})
    thread_handler.add_thread(test_sensor.run, test_sensor.get_sensor_name(), test_sensor)
    thread_handler.start()

    assert test_sensor.get_sensor_name() == 'good'
    
    # database tables set up correctly
    #TODO: database has no tables. Check for make_table_external getting all the right args, check for make_table_external being called
    try:
        coms.send_request.assert_called_with('dataBase', ['create_table_external', {'name': ['row', 0, 'int']}])

        print(f"{dataBase._DataBaseHandler__tables=}")
        assert 'good' in dataBase.get_tables_html()
    finally:
        thread_handler.kill_tasks()

    # html graphs set up correctly
    # events set up correctly
    # threaWrapper stuff set up correctly
    # html page generation stuff set up correctly
    # everything else is initialized properly???

#TODO: maybe also test get and create tap funcs here?
@pytest.mark.sensor_parent_tests
def test_set_up_taps():
    #test for one tap, passive_active == 'active'
    test_sensor = sensor_parent(coms=None, config={'tap_request': ['a'], 'publisher': 'yes', 'passive_active': 'active', 'interval_pub': 1}, name='tap_test_1')
    test_sensor.make_data_tap = MagicMock()
    test_sensor.start_publisher = MagicMock()
    test_sensor.set_up_taps()
    
    test_sensor.make_data_tap.assert_called_with('a')
    assert test_sensor.get_taps() == ['a']
    assert test_sensor._sensor_parent__active == True
    test_sensor.start_publisher.assert_called_with

    #test for multiple taps, passive_active == 'passive'
    test_sensor = sensor_parent(coms=None, config={'tap_request': ['a', 'b', 'c'], 'publisher': 'yes', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='tap_test_2')
    test_sensor.make_data_tap = MagicMock()
    test_sensor.start_publisher = MagicMock()
    test_sensor.set_up_taps()
    
    test_sensor.make_data_tap.assert_called_with('c')
    assert test_sensor.get_taps() == ['a', 'b', 'c']
    assert test_sensor._sensor_parent__active == False
    test_sensor.start_publisher.assert_not_called

    #test for tap_request, publisher, and passive_active == None
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': None, 'passive_active': None, 'interval_pub': 'NA'}, name='tap_test_3')
    test_sensor.make_data_tap = MagicMock()
    test_sensor.start_publisher = MagicMock()
    test_sensor.set_up_taps()

    assert test_sensor.get_taps() == ['None']
    assert test_sensor._sensor_parent__active == False
    test_sensor.start_publisher.assert_not_called
    
    #test for publisher == 'no'
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'no', 'interval_pub': 'NA'}, name='tap_test_4')
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
    # set up tap
    coms = messageHandler(destination='Local')
    thread_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=thread_handler)
    receiver = sensor_parent(coms=coms, config={'tap_request': ['sender'], 'publisher': None, 'interval_pub': None}, name='receiver')
    receiver.set_up_taps()
    assert receiver.get_taps() == ['sender']

    # ensure data_buffer_overwrite is false (ready for data)
    data_ready = False
    while not data_ready:
        data_ready = receiver.ready_for_data()

    # send_tap() is what reciever is told to call by one of its taps when that tap gets data
    data = [['this', 'is', 'some', 'good', 'data'], [1, 2, 3, 4, 5], ['data', 123]]
    for data in data:
        receiver.send_tap(data, 'sender')
        assert receiver.get_data_received('sender') == data

    # test for failure to acquire data_buffer_overwrite_lock
    receiver.send_tap([], 'sender') # send new piece of data so we can test it later
    receiver._sensor_parent__data_buffer_overwrite_lock.acquire()
    if receiver._sensor_parent__data_buffer_overwrite_lock.locked():
        with pytest.raises(RuntimeError) as excinfo:
            receiver.get_data_received('sender')

        receiver._sensor_parent__data_buffer_overwrite_lock.release()
        assert 'Could not acquire data buffer overwrite lock.' in str(excinfo.value)
        assert receiver._sensor_parent__data_buffer_overwrite_lock.locked() == False
        assert receiver.get_data_received('sender') == ['data', 123]    #failure to acquire lock means it is unable to update data_copy to []

    # test for failure to acquire data_lock
    receiver._sensor_parent__data_lock.acquire()
    if receiver._sensor_parent__data_lock.locked():
        with pytest.raises(RuntimeError) as excinfo:
            receiver.get_data_received('sender')

        receiver._sensor_parent__data_lock.release()
        assert 'Could not acquire data lock' in str(excinfo.value)
        assert receiver._sensor_parent__data_lock.locked() == False
        assert receiver.get_data_received('sender') == ['data', 123]    #failure to acquire lock means it is unable to update data_copy to []

@pytest.mark.sensor_parent_tests
def test_make_data_tap():
    coms = messageHandler(destination='Local')
    thread_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=thread_handler)
    source = sensor_parent(coms=coms, config={'tap_request': None, 'publisher': 'yes', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='source')
    tapper = sensor_parent(coms=coms, config={'tap_request': ['source'], 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='tapper')
    thread_handler.add_thread(source.run, source.get_sensor_name(), source)
    thread_handler.add_thread(tapper.run, tapper.get_sensor_name(), tapper)
    thread_handler.start()

    tapper.make_data_tap('source')

    while thread_handler.check_request('source', 1) is False:
        pass
    try:
        assert 'tapper' in source._sensor_parent__tap_subscribers
    finally:
        thread_handler.kill_tasks()

    # test for failure to acquire name_lock
    tapper._sensor_parent__name_lock.acquire()
    # mock send_request to make sure it isn't called
    coms.send_request = MagicMock()
    if tapper._sensor_parent__name_lock.locked():
        with pytest.raises(RuntimeError) as excinfo:
            tapper.make_data_tap('source')

        tapper._sensor_parent__name_lock.release()
        assert 'Could not acquire name lock' in str(excinfo.value)
        assert tapper._sensor_parent__name_lock.locked() == False
        coms.send_request.assert_not_called()

#TODO
@pytest.mark.sensor_parent_tests
def test_send_tap():
    #things to test:
    #   no data
    #   some data
    #   sender is in taps list
    #   sender is not in taps list?
    coms = messageHandler(destination='Local')
    thread_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=thread_handler)

    with open("main.yaml", "r") as file:
        config_data = yaml.safe_load(file)
    sensor_config_dict = config_data.get("sensor_config_dict", {})
    sensor_config.sensors_config = sensor_config_dict

    temp = None
    def process_data(*args, **kwargs):
        temp = args[0]

    sensor_parent.process_data = MagicMock(side_effect=process_data)
    # test_sensor = sobj_gps_board_aux(coms=coms)
    test_sensor = sensor_parent(coms=coms, config={'tap_request': ['source'], 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='Justin')
    test_sensor.process_data = MagicMock(side_effect=process_data)
    thread_handler.add_thread(test_sensor.run, test_sensor.get_sensor_name(), test_sensor)
    thread_handler.start()

    try:
        test_sensor.send_tap(data=[1, 2, 3], sender='source')
        print(f"{temp=}")
        assert test_sensor._sensor_parent__data_buffer_overwrite == False
        # assert that return val is something or other
        # assert data in data_received list
        # threadWrapper.set_event.assert_called()
        assert test_sensor._sensor_parent__data_buffer_overwrite_lock.locked() == False
        
        # test_sensor.send_tap(data=[1, 2, 3], sender = 'sender')
        # assert test_sensor._sensor_parent__data_buffer_overwrite == True
        # assert test_sensor._sensor_parent__data_buffer_overwrite_lock.locked() == False
        
        #   not_ready_bool is equal to data_buffer_overwrite (DO WE NEED TO TEST THIS? NOT_READY IS AN INTERNAL SIGNAL)
        #   lock is released
        #   not quite sure how to test while loops

        #   ensure event is set, meaning process data gets called
        #   lock is released

        #   failure to acquire data_buffer_overwrite_lock - I'm probably going to want to make a few threads to try and test the different places
        #   in which it can fail

    finally:
        thread_handler.kill_tasks()
        

#get_taps is already tested (is it though lmao)

#TODO
@pytest.mark.sensor_parent_tests
def test_create_tap():
    #real talk, should I just put all the tap related stuff in one long ass test?
    pass

@pytest.mark.sensor_parent_tests
def test_get_sensor_name():
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': None, 'interval_pub': None}, name='Liz')
    assert test_sensor.get_sensor_name() == 'Liz'

    # test for failure to acquire lock
    test_sensor._sensor_parent__name_lock.acquire()
    if (test_sensor._sensor_parent__name_lock.locked()):
        with pytest.raises(RuntimeError) as excinfo:
            test_sensor.get_sensor_name()
        
        assert "Could not acquire name lock" in str(excinfo.value)
    test_sensor._sensor_parent__name_lock.release()
    
@pytest.mark.sensor_parent_tests
def test_start_publisher():
    # to test:
    #   failure to acquire lock
    coms = messageHandler(destination='Local')
    thread_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=thread_handler)
    test_sensor = sensor_parent(coms=coms, config={'tap_request': ['a'], 'publisher': 'yes', 'passive_active': 'active', 'interval_pub': 1}, name='publisher_test')

    thread_handler.add_thread(test_sensor.run, test_sensor.get_sensor_name(), test_sensor)
    thread_handler.start()
    test_sensor.start_publisher()

    assert 'publisher for publisher_test' in thread_handler._taskHandler__threads

    # test for failure to acquire lock
    test_sensor._sensor_parent__name_lock.acquire()
    if (test_sensor._sensor_parent__name_lock.locked()):
        with pytest.raises(RuntimeError) as excinfo:
            test_sensor.start_publisher()
        
        assert "Could not acquire name lock" in str(excinfo.value)
    test_sensor._sensor_parent__name_lock.release()

    thread_handler.kill_tasks()

#TODO
@pytest.mark.sensor_parent_tests
def test_publish():
    #wow this is very big and very long. maybe I'll go work on that init test lol
    pass