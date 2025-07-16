'''
    Unit test for collect_sensor
'''

#Python imports
import pytest
import yaml
from unittest.mock import MagicMock, call
from io import StringIO
import warnings
import time
from datetime import datetime
import os

#Custom imports
from threading_python_api.threadWrapper import threadWrapper
from threading_python_api.taskHandler import taskHandler
import system_constants as sensor_config
from sensor_interface_api.sensor_parent import sensor_parent
from sensor_interface_api.sobj_gps_board_aux import sobj_gps_board_aux
from sensor_interface_api.sobj_gps_board import sobj_gps_board
from logging_system_display_python_api.messageHandler import messageHandler
from database_python_api.database_control import DataBaseHandler
from cmd_inter import cmd_inter
from port_interface_api.file_read_api.file_listener import file_listener
from server_message_handler import serverMessageHandler
from server import serverHandler


#TODO: elses on lock failure test

db_name = 'unit_tests_sensor_parent'
db_username = os.getenv('DB_USERNAME')
db_password = os.getenv('DB_PASSWORD')

'''
    Before running this test, you need to make sure that you have created a mysql database called
    unit_tests_sensor_parent and have given the user ground_cse full access rights. If you have not, run these commands in root access mysql

    CREATE DATABASE unit_tests_sensor_parent;
    GRANT ALL PRIVILEGES ON unit_tests_sensor_parent.* TO 'ground_cse'@'localhost';
    FLUSH PRIVILEGES;
'''
@pytest.mark.sensor_parent_tests
def test_init():
    '''
        Tests init, get_sensor_name(), get_graph_name(), and get_html_page()
    '''
    # setup
    table_structure = {'init_test_table': [['rowan', 0, 'int'], ['row2', 0, 'float'], ['row3', 0, 'string']]}

    coms = messageHandler()
    task_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=task_handler)

    dataBase = DataBaseHandler(coms=coms, db_name=db_name, user=db_username, password=db_password, clear_database=True)
    task_handler.add_thread(dataBase.run, db_name, dataBase)
    task_handler.start()

    try:
        test_sensor = sensor_parent(coms=coms, config={'tap_request': ['this', 'that'], 'publisher': 'no', 'interval_pub': 'NA'}, name='good_sensor', db_name=db_name, table_structure=table_structure,
                                    graphs=['one', 'two', 'three'])

        task_handler.add_thread(test_sensor.run, test_sensor.get_sensor_name(), test_sensor)
        task_handler.start()

        ######################## Names set up correctly ##########################
        # valid names accepted
        assert test_sensor.get_sensor_name() == 'good_sensor'

        # test get_name failure to acquire lock
        test_sensor._sensor_parent__name_lock.acquire()
        if (test_sensor._sensor_parent__name_lock.locked()):
            with pytest.raises(RuntimeError) as excinfo:
                test_sensor.get_sensor_name()
        assert "Could not acquire name lock" in str(excinfo.value)
        test_sensor._sensor_parent__name_lock.release()

        # invalid names rejected
        with pytest.raises(RuntimeError) as excinfo:
            bad_test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': None, 'interval_pub': None}, name='bad\0')
        assert "The name bad\0, is not a valid sensor name" in str(excinfo.value)
        
        with pytest.raises(RuntimeError) as excinfo:
            bad_test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': None, 'interval_pub': None}, name='bad/')
        assert "The name bad/, is not a valid sensor name" in str(excinfo.value)

        ###################### Database set up correctly #########################
        assert 'init_test_table' in dataBase.get_tables_html()

        ##################### Html graphs set up correctly #######################
        assert test_sensor.get_graph_names() == ['one', 'two', 'three']
        assert 'one' in test_sensor.get_data_report()
        assert 'two' in test_sensor.get_data_report()
        assert 'three' in test_sensor.get_data_report()
        assert test_sensor._sensor_parent__data_report_lock.locked() == False
        assert test_sensor._sensor_parent__graphs_lock.locked() == False

        # get_graph_names failure to acquire lock
        test_sensor._sensor_parent__graphs_lock.acquire()
        if test_sensor._sensor_parent__graphs_lock.locked():
            with pytest.raises(RuntimeError) as excinfo:
                test_sensor.get_graph_names()
            assert "Could not acquire graphs lock" in str(excinfo.value)
        test_sensor._sensor_parent__graphs_lock.release()

        ##################### Html graphs set up correctly########################
        # events set up correctly
        assert 'data_received_for_this' in test_sensor._sensor_parent__events
        assert 'data_received_for_that' in test_sensor._sensor_parent__events

        #################### Threadwrapper set up correctly#######################
        assert test_sensor._threadWrapper__function_dict == test_sensor._sensor_parent__function_dict
        assert 'data_received_for_this' in test_sensor._threadWrapper__event_dict
        assert 'data_received_for_that' in test_sensor._threadWrapper__event_dict

        ###################### Html page set up correctly#########################
        # html page generation stuff set up correctly
        assert test_sensor.get_html_page() == 'templates/good_sensor.html'

        # test without lock acquired:
        test_sensor._sensor_parent__html_lock.acquire()
        if test_sensor._sensor_parent__html_lock.locked():
            with pytest.raises(RuntimeError) as excinfo:
                test_sensor.get_html_page()

            test_sensor._sensor_parent__html_lock.release()
            assert "Could not acquire html lock" in str(excinfo.value)
            assert test_sensor._sensor_parent__html_lock.locked() == False

    finally:
        dataBase._DataBaseHandler__close_sql_connections()
        task_handler.kill_tasks()

@pytest.mark.sensor_parent_tests
def test_get_set_taps():
    #test for one tap, passive_active == 'active'
    test_sensor = sensor_parent(coms=None, config={'tap_request': ['a'], 'publisher': 'yes', 'passive_active': 'active', 'interval_pub': 1}, name='tap_test_1')

    test_sensor.make_data_tap = MagicMock()
    test_sensor.start_publisher = MagicMock()
    test_sensor.set_up_taps()
    
    test_sensor.make_data_tap.assert_called_with('a')
    assert test_sensor.get_taps() == ['a']
    assert test_sensor._sensor_parent__active == True
    test_sensor.start_publisher.assert_called()

    #for getter, test if it fails to acquire lock
    test_sensor._sensor_parent__taps_lock.acquire()
    if test_sensor._sensor_parent__taps_lock.locked():
        with pytest.raises(RuntimeError) as excinfo:
            test_sensor.get_taps()
        assert "Could not acquire taps lock" in str(excinfo.value)
    test_sensor._sensor_parent__taps_lock.release()

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
    task_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=task_handler)
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
    task_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=task_handler)

    source = sensor_parent(coms=coms, config={'tap_request': None, 'publisher': 'yes', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='source')
    tapper = sensor_parent(coms=coms, config={'tap_request': ['source'], 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='tapper')

    task_handler.add_thread(source.run, source.get_sensor_name(), source)
    task_handler.add_thread(tapper.run, tapper.get_sensor_name(), tapper)
    task_handler.start()

    try:
        tapper.make_data_tap('source')

        while task_handler.check_request('source', 1) is False:
            pass
        assert 'tapper' in source._sensor_parent__tap_subscribers

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
        assert call('source', ['create_tap', tapper.send_tap, 'source']) not in coms.send_request.call_args
    finally:
        task_handler.kill_tasks()

#NOTE: there are still a couple cases in the middle where it checks the data_buffer_overwrite lock that I don't have covered, but I think the first check should be enough
# also there is the while loop that isn't covered but like. I don't want to. I could probably make another thread that can change the data_buffer_overwrite bool but that sounds like a lot of work ngl
@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
@pytest.mark.sensor_parent_tests
def test_send_tap_not_read_from_file(capsys):
    coms = messageHandler(destination='Local')
    task_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=task_handler)

    with open("main.yaml", "r") as file:
        config_data = yaml.safe_load(file)
    sensor_config_dict = config_data.get("sensor_config_dict", {})
    sensor_config.sensors_config = sensor_config_dict

    test_sensor = sensor_parent(coms=coms, config={'tap_request': ['sender'], 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='receiver')
    test_sensor.process_data = MagicMock()
    test_sensor.process_data.side_effect = print("process_data called") #this is necesarry, as the call count is not incremented when a func is called through coms

    task_handler.add_thread(test_sensor.run, test_sensor.get_sensor_name(), test_sensor)
    task_handler.start()

    try:
        data = [1, 2, 3]
        test_sensor.send_tap(data=data, sender='sender')
        captured = capsys.readouterr()
        assert test_sensor._sensor_parent__data_received['sender'] == data
        assert captured.out == "process_data called\n"
        
        test_sensor.send_tap(data=[], sender = 'sender')
        assert test_sensor._sensor_parent__data_received['sender'] == data

        #testing all instances of data_buffer_overwrite_lock
        test_sensor._sensor_parent__data_buffer_overwrite_lock.acquire()
        if test_sensor._sensor_parent__data_buffer_overwrite_lock.locked():
            with pytest.raises(RuntimeError) as excinfo:
                test_sensor.send_tap(data=[], sender = 'Little Justin')

            test_sensor._sensor_parent__data_buffer_overwrite_lock.release()
            assert "Could not acquire data buffer overwrite lock." in str(excinfo.value)

        test_sensor._sensor_parent__data_lock.acquire()
        if test_sensor._sensor_parent__data_lock.locked():
            with pytest.raises(RuntimeError) as excinfo:
                test_sensor.send_tap(data=data, sender = 'Little Justin')

            test_sensor._sensor_parent__data_lock.release()
            assert "Could not acquire data lock" in str(excinfo.value)

    finally:
        task_handler.kill_tasks()

@pytest.mark.filterwarnings("ignore::pytest.PytestUnhandledThreadExceptionWarning")
@pytest.mark.sensor_parent_tests
def test_send_tap_read_from_file(capsys):
    coms = messageHandler(destination='Local')
    task_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=task_handler)

    with open("main.yaml", "r") as file:
        config_data = yaml.safe_load(file)
    sensor_config_dict = config_data.get("sensor_config_dict", {})
    sensor_config.sensors_config = sensor_config_dict

    sensor_config.read_from_file = True
    file_listener_obj = file_listener(coms, thread_name='file_listener', batch_size=1024, batch_collection_number_before_save=10, import_bin_path='')
    task_handler.add_thread(file_listener_obj.run, 'file_listener', file_listener_obj)
    sensor_config.file_listener_name = 'file_listener'
    file_listener_obj._file_listener__logger.send_log = MagicMock()
    
    test_sensor = sensor_parent(coms=coms, config={'tap_request': ['sender'], 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='receiver')
    test_sensor.process_data = MagicMock()
    test_sensor.process_data.side_effect = print("process_data called") #this is necesarry, as the call count is not incremented when a func is called through coms

    task_handler.add_thread(test_sensor.run, test_sensor.get_sensor_name(), test_sensor)
    task_handler.start()

    try:
        data = [1, 2, 3]
        test_sensor.send_tap(data=data, sender='sender')
        captured = capsys.readouterr()
        assert test_sensor._sensor_parent__data_received['sender'] == data
        assert "process_data called" in captured.out
        
        #assuming the mark_started request is the first one made to the file listener
        while task_handler.check_request('file_listener', 1) is False:
            pass
        file_listener_obj._file_listener__logger.send_log.assert_called_with("['sender'] started")

    finally:
        task_handler.kill_tasks()

@pytest.mark.sensor_parent_tests
def test_create_tap():
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='Peter')

    test_sensor.create_tap([None, None])
    test_sensor.create_tap([MagicMock, 'subscriber_name'])
    assert test_sensor._sensor_parent__tap_requests == [MagicMock]
    assert test_sensor._sensor_parent__tap_subscribers ==['subscriber_name']
    
    test_sensor._sensor_parent__tap_requests_lock.acquire()
    with pytest.raises(RuntimeError) as excinfo:
        test_sensor.create_tap([MagicMock, 'subscriber_name'])
    assert "Could not acquire tap requests lock" in str(excinfo.value)
    test_sensor._sensor_parent__tap_requests_lock.release()

    test_sensor._sensor_parent__tap_subscribers_lock.acquire()
    with pytest.raises(RuntimeError) as excinfo:
        test_sensor.create_tap([MagicMock, 'subscriber_name'])
    assert "Could not acquire config lock" in str(excinfo.value)
    test_sensor._sensor_parent__tap_subscribers_lock.release()

@pytest.mark.sensor_parent_tests
def test_start_publisher():
    coms = messageHandler(destination='Local')
    task_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=task_handler)
    test_sensor = sensor_parent(coms=coms, config={'tap_request': ['a'], 'publisher': 'yes', 'passive_active': 'active', 'interval_pub': 1}, name='publisher_test')

    task_handler.add_thread(test_sensor.run, test_sensor.get_sensor_name(), test_sensor)
    task_handler.start()
    test_sensor.start_publisher()

    assert 'publisher for publisher_test' in task_handler._taskHandler__threads

    # test for failure to acquire lock
    test_sensor._sensor_parent__name_lock.acquire()
    if (test_sensor._sensor_parent__name_lock.locked()):
        with pytest.raises(RuntimeError) as excinfo:
            test_sensor.start_publisher()
        
        assert "Could not acquire name lock" in str(excinfo.value)
    test_sensor._sensor_parent__name_lock.release()

    task_handler.kill_tasks()

@pytest.mark.sensor_parent_tests
def test_publish():
    good_data = ['abc', 'def', 'ghi']
    bad_data = [MagicMock]

    coms = messageHandler(server_name='CSE_Server_Listener')
    task_handler = taskHandler(coms=coms)
    coms.set_thread_handler(task_handler)


    ######################## Active sensor #######################
    active_test_sensor = sensor_parent(coms=coms, config={'tap_request': None, 'publisher': 'yes', 'passive_active': 'active', 'interval_pub': 1}, name='active')
    active_test_sensor.set_up_taps()
    # hate = sensor_parent(coms=coms, config={'tap_request': ['active'], 'publisher': 'yes', 'passive_active': 'passive', 'interval_pub': 'NA'}, name = 'evil')


    # In theory, this should test if the active sensor publishes data at the correct interval, but the infinite while loop prevents the thread from dying, thus the test can never finish.
    # I'm leaving it here because it may be useful in the future as a guideline when we rewrite the tests

    # active_test_sensor._sensor_parent__events[f'data_received_for_sender'] = active_test_sensor.publish()
    # task_handler.add_thread(active_test_sensor.run, active_test_sensor.get_sensor_name(), active_test_sensor)
    # task_handler.add_thread(hate.run, hate.get_sensor_name(), hate)
    # task_handler.start()

    # try:
    #     active_test_sensor.set_up_taps()
    #     hate.set_up_taps()

    #     active_test_sensor.set_publish_data(data=good_data)
    #     time.sleep(1)
    #     # print(f"\n\n{active_test_sensor.get_last_published_data()}")
    #     assert active_test_sensor.get_last_published_data()['data'] == 'g , h , i'
    #     time_1 = active_test_sensor.get_last_published_data()['time']

    #     #now we have to do something to make the other sensor ready for more data but idk how. I think we gotta process it
    #     hate.process_data()

    #     active_test_sensor.set_publish_data(data=bad_data)
    #     time.sleep(1)
    #     # print(f"\n\n{active_test_sensor.get_last_published_data()}")
    #     assert active_test_sensor.get_last_published_data()['data'] == "Unable to convert last data to string for reporting, this should not affect performance of the publishing."
    #     time_2 = active_test_sensor.get_last_published_data()['time']

    #     format = '%y-%m-%d %H:%M:%S.%f'
    #     time_diff = datetime.strptime(time_2, format) - datetime.strptime(time_1, format)
    #     assert time_diff.seconds >= 1
    # finally:
    #     task_handler.kill_tasks()

    # failure to acquire locks
    active_test_sensor._sensor_parent__active__lock.acquire()
    if (active_test_sensor._sensor_parent__active__lock.locked()):
        with pytest.raises(RuntimeError) as excinfo:
            active_test_sensor.publish()
        
        assert "Could not acquire active lock" in str(excinfo.value)
    active_test_sensor._sensor_parent__active__lock.release()

    active_test_sensor._sensor_parent__last_published_data_lock.acquire()
    if (active_test_sensor._sensor_parent__last_published_data_lock.locked()):
        with pytest.raises(RuntimeError) as excinfo:
            active_test_sensor.publish()
        
        assert "Could not acquire published data lock" in str(excinfo.value)
    active_test_sensor._sensor_parent__last_published_data_lock.release()

    active_test_sensor._sensor_parent__has_been_published_lock.acquire()
    if (active_test_sensor._sensor_parent__has_been_published_lock.locked()):
        with pytest.raises(RuntimeError) as excinfo:
            active_test_sensor.publish()
        
        assert "Could not acquire has been published lock" in str(excinfo.value)
    active_test_sensor._sensor_parent__has_been_published_lock.release()

    ####################### Passive sensor #######################
    passive_test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'yes', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='passive')
    passive_test_sensor.set_up_taps()

    passive_test_sensor.set_publish_data(good_data)
    passive_test_sensor.publish()
    assert passive_test_sensor.get_last_published_data()['data'] == 'g , h , i'

    passive_test_sensor.set_publish_data(bad_data)
    passive_test_sensor.publish()
    assert passive_test_sensor.get_last_published_data()['data'] == "Unable to convert last data to string for reporting, this should not affect performance of the publishing."

    # failure to acquire locks
    passive_test_sensor._sensor_parent__last_published_data_lock.acquire()
    if (passive_test_sensor._sensor_parent__last_published_data_lock.locked()):
        with pytest.raises(RuntimeError) as excinfo:
            passive_test_sensor.publish()
        
        assert "Could not acquire last published data lock" in str(excinfo.value)
    passive_test_sensor._sensor_parent__last_published_data_lock.release()

    passive_test_sensor._sensor_parent__has_been_published_lock.acquire()
    if (passive_test_sensor._sensor_parent__has_been_published_lock.locked()):
        with pytest.raises(RuntimeError) as excinfo:
            passive_test_sensor.publish()
        
        assert "Could not acquire has been published lock" in str(excinfo.value)
    passive_test_sensor._sensor_parent__has_been_published_lock.release()

@pytest.mark.sensor_parent_tests
def test_send_data_to_tap():
    coms = messageHandler()
    task_handler = taskHandler(coms=coms)
    coms.set_thread_handler(task_handler)

    receiver = sensor_parent(coms=coms, config={'tap_request': ['sender'], 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='receiver')
    sender = sensor_parent(coms=coms, config={'tap_request': None, 'publisher': 'yes', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='sender')

    task_handler.add_thread(receiver.run, receiver.get_sensor_name(), receiver)
    task_handler.add_thread(sender.run, sender.get_sensor_name(), sender)
    task_handler.start()

    try:
        data = ['abc', 'def']
        receiver.set_up_taps()
        sender.set_up_taps()

        while sender.check_request(1) is False:
            pass

        sender.set_publish_data(data)
        sender.send_data_to_tap()
        
        assert receiver._sensor_parent__data_received['sender'] == data
    finally:
        task_handler.kill_tasks()

@pytest.mark.sensor_parent_tests
def test_fail_send_data_to_tap():
    coms = messageHandler()
    task_handler = taskHandler(coms=coms)
    coms.set_thread_handler(task_handler)

    receiver = sensor_parent(coms=coms, config={'tap_request': ['sender'], 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='receiver')
    sender = sensor_parent(coms=coms, config={'tap_request': None, 'publisher': 'yes', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='sender')

    task_handler.add_thread(receiver.run, receiver.get_sensor_name(), receiver)
    task_handler.add_thread(sender.run, sender.get_sensor_name(), sender)
    task_handler.start()

    try:
        data = ['abc', 'def']
        receiver.set_up_taps()
        sender.set_up_taps()

        while sender.check_request(1) is False:
            pass

        sender.set_publish_data(data)
        # failure to acquire publish data lock
        sender._sensor_parent__publish_data_lock.acquire()
        if (sender._sensor_parent__publish_data_lock.locked()):
            with pytest.raises(RuntimeError) as excinfo:
                sender.send_data_to_tap()
            assert "Could not acquire publish data lock" in str(excinfo.value)
        sender._sensor_parent__publish_data_lock.release()

        # failure to acquire subscribers lock
        sender._sensor_parent__tap_subscribers_lock.acquire()
        if (sender._sensor_parent__tap_subscribers_lock.locked()):
            with pytest.raises(RuntimeError) as excinfo:
                sender.send_data_to_tap()
            assert "Could not acquire config lock" in str(excinfo.value)
        sender._sensor_parent__tap_subscribers_lock.release()
        
        # failure to acquire tap requests lock
        sender._sensor_parent__tap_requests_lock.acquire()
        if (sender._sensor_parent__tap_requests_lock.locked()):
            with pytest.raises(RuntimeError) as excinfo:
                sender.send_data_to_tap()
            assert "Could not acquire tap requests lock" in str(excinfo.value)
        sender._sensor_parent__tap_requests_lock.release()
    finally:
        task_handler.kill_tasks()

@pytest.mark.sensor_parent_tests
def test_set_check_publish():
    '''
        Tests set_publish_data() and has_been_published()
    '''
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='Shawn')
    data = [1, 2, 3]
    
    test_sensor.set_publish_data(data)
    assert not test_sensor.has_been_published()
    assert test_sensor._sensor_parent__publish_data == data

    # set_publish_data failure to acquire locks
    test_sensor._sensor_parent__publish_data_lock.acquire()
    if (test_sensor._sensor_parent__publish_data_lock.locked()):
        with pytest.raises(RuntimeError) as excinfo:
            test_sensor.set_publish_data(data)
        
        assert "Could not acquire publish data lock" in str(excinfo.value)
    test_sensor._sensor_parent__publish_data_lock.release()

    test_sensor._sensor_parent__has_been_published_lock.acquire()
    if (test_sensor._sensor_parent__has_been_published_lock.locked()):
        with pytest.raises(RuntimeError) as excinfo:
            test_sensor.set_publish_data(data)
        
        assert "Could not acquire has been published lock" in str(excinfo.value)
    test_sensor._sensor_parent__has_been_published_lock.release()

    # has_been_published failure to acquire lock
    test_sensor._sensor_parent__has_been_published_lock.acquire()
    if (test_sensor._sensor_parent__has_been_published_lock.locked()):
        with pytest.raises(RuntimeError) as excinfo:
            test_sensor.has_been_published()
        
        assert "Could not acquire has been published lock" in str(excinfo.value)
    test_sensor._sensor_parent__has_been_published_lock.release()

@pytest.mark.sensor_parent_tests
def test_get_set_graph_data():
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='Tim', graphs=['plot', 'over'])

    # inserting a point
    test_sensor.add_graph_data('plot', [2], [3])
    data_report = test_sensor.get_data_report()
    assert data_report['plot'] == {'x': [2], 'y': [3]}
    assert data_report['over'] == {'x': [], 'y': []}

    # reaching max number of data points
    test_sensor.add_graph_data('over', [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0])
    data_report = test_sensor.get_data_report()
    assert data_report['over'] == {'x': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 'y': [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]}

    # add_graph_data fail to acquire lock
    test_sensor._sensor_parent__data_report_lock.acquire()
    if (test_sensor._sensor_parent__data_report_lock.locked()):
        with pytest.raises(RuntimeError) as excinfo:
            test_sensor.add_graph_data('plot', 2, 3)
        
        assert "Could not acquire data report lock" in str(excinfo.value)
    test_sensor._sensor_parent__data_report_lock.release()

    # get_data_report failure to acquire locks
    test_sensor._sensor_parent__data_report_lock.acquire()
    if test_sensor._sensor_parent__data_report_lock.locked():
        with pytest.raises(RuntimeError) as excinfo:
            test_sensor.get_data_report()
        assert "Could not acquire data report lock" in str(excinfo.value)
    test_sensor._sensor_parent__data_report_lock.release()

@pytest.mark.sensor_parent_tests
def test_get_last_published_data():
    data = ['abc', 'def', 'ghi']

    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'yes', 'passive_active': 'active', 'interval_pub': 1}, name='active')

    test_sensor.set_publish_data(data)
    test_sensor.publish()
    assert test_sensor.get_last_published_data()['data'] == 'g , h , i'

    # failure to acquire lock
    test_sensor._sensor_parent__last_published_data_lock.acquire()
    if (test_sensor._sensor_parent__last_published_data_lock.locked()):
        with pytest.raises(RuntimeError) as excinfo:
            test_sensor.get_last_published_data()
        
        assert "Could not acquire last published data lock" in str(excinfo.value)
    test_sensor._sensor_parent__last_published_data_lock.release()

@pytest.mark.sensor_parent_tests
def test_save_data_read_from_file():
    sensor_config.read_from_file = True
    table_structure = {'save_data_test_table': [['first', 0, 'int'], ['second', 0, 'float'], ['third', 0, 'string']]}
    
    coms = messageHandler()
    task_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=task_handler)

    file_listener_obj = file_listener(coms, thread_name='file_listener', batch_size=1024, batch_collection_number_before_save=10, import_bin_path='')
    task_handler.add_thread(file_listener_obj.run, 'file_listener', file_listener_obj)
    sensor_config.file_listener_name = 'file_listener'
    file_listener_obj._file_listener__logger.send_log = MagicMock()

    dataBase = DataBaseHandler(coms=coms, db_name=db_name, user=db_username, password=db_password, clear_database=True)
    task_handler.add_thread(dataBase.run, db_name, dataBase)
    task_handler.start()

    try:
        test_sensor = sensor_parent(coms=coms, config={'tap_request': None, 'publisher': 'no', 'interval_pub': 'NA'}, name='save_data_test', db_name=db_name, table_structure=table_structure)
        task_handler.add_thread(test_sensor.run, test_sensor.get_sensor_name(), test_sensor)
        task_handler.start()
        
        for request in dataBase._threadWrapper__request:
            if request[0] == 'create_table_external':
                request_num = request[4]

        while dataBase.check_request(request_num) is False:
            pass

        test_sensor.save_data(table='save_data_test_table', data={'first': [1], 'second': [0.5], 'third': ['x']})
        
        for request in dataBase._threadWrapper__request:
            if request[0] == 'save_data_group':
                request_num = request[4]
        
        while dataBase.check_request(request_num) is False:
            pass
        
        assert '1,0.5,x' in dataBase.get_data(['save_data_test_table', 0])

        file_listener_obj._file_listener__logger.send_log.assert_called_with("['save_data_testnot byte'] ended")
    finally:
        dataBase._DataBaseHandler__close_sql_connections()
        task_handler.kill_tasks()

@pytest.mark.sensor_parent_tests
def test_save_data_not_read_from_file():
    sensor_config.read_from_file = False
    table_structure = {'save_data_test_table': [['first', 0, 'int'], ['second', 0, 'float'], ['third', 0, 'string']]}
    
    coms = messageHandler()
    task_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=task_handler)

    dataBase = DataBaseHandler(coms=coms, db_name=db_name, user=db_username, password=db_password, clear_database=True)
    task_handler.add_thread(dataBase.run, db_name, dataBase)
    task_handler.start()

    try:
        test_sensor = sensor_parent(coms=coms, config={'tap_request': None, 'publisher': 'no', 'interval_pub': 'NA'}, name='save_data_test', db_name=db_name, table_structure=table_structure)
        task_handler.add_thread(test_sensor.run, test_sensor.get_sensor_name(), test_sensor)
        task_handler.start()
        
        for request in dataBase._threadWrapper__request:
            if request[0] == 'create_table_external':
                request_num = request[4]

        while dataBase.check_request(request_num) is False:
            pass

        test_sensor.save_data(table='save_data_test_table', data={'first': [1], 'second': [0.5], 'third': ['x']})
        
        for request in dataBase._threadWrapper__request:
            if request[0] == 'save_data_group':
                request_num = request[4]
        
        while dataBase.check_request(request_num) is False:
            pass
        
        assert '1,0.5,x' in dataBase.get_data(['save_data_test_table', 0])

    finally:
        dataBase._DataBaseHandler__close_sql_connections()
        task_handler.kill_tasks()

@pytest.mark.sensor_parent_tests
def test_save_byte_data_read_from_file():
    #test if read_from_file is false
    sensor_config.read_from_file = True
    table_structure = {'save_byte_data_test_table': [['first', 4, 'byte']]}
    
    coms = messageHandler()
    task_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=task_handler)

    file_listener_obj = file_listener(coms, thread_name='file_listener', batch_size=1024, batch_collection_number_before_save=10, import_bin_path='')
    task_handler.add_thread(file_listener_obj.run, 'file_listener', file_listener_obj)
    sensor_config.file_listener_name = 'file_listener'
    file_listener_obj._file_listener__logger.send_log = MagicMock()

    dataBase = DataBaseHandler(coms=coms, db_name=db_name, user=db_username, password=db_password, clear_database=True)
    task_handler.add_thread(dataBase.run, db_name, dataBase)
    task_handler.start()

    try:
        test_sensor = sensor_parent(coms=coms, config={'tap_request': None, 'publisher': 'no', 'interval_pub': 'NA'}, name='save_byte_data_test', db_name=db_name, table_structure=table_structure)
        task_handler.add_thread(test_sensor.run, test_sensor.get_sensor_name(), test_sensor)
        task_handler.start()
        
        for request in dataBase._threadWrapper__request:
            if request[0] == 'create_table_external':
                request_num = request[4]

        while dataBase.check_request(request_num) is False:
            pass
        test_sensor.save_byte_data(table='save_byte_data_test_table', data={'first': [[11]]})
        
        for request in dataBase._threadWrapper__request:
            if request[0] == 'save_byte_data':
                request_num = request[4]
        while dataBase.check_request(request_num) is False:
            pass
        assert 'x0b' in dataBase.get_data(['save_byte_data_test_table', 0])

        file_listener_obj._file_listener__logger.send_log.assert_called_with("['save_byte_data_testbyte'] ended")
    finally:
        dataBase._DataBaseHandler__close_sql_connections()
        task_handler.kill_tasks()

@pytest.mark.sensor_parent_tests
def test_save_byte_data_not_read_from_file():
    sensor_config.read_from_file = False
    table_structure = {'save_byte_data_test_table': [['first', 4, 'byte']]}
    
    coms = messageHandler()
    task_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=task_handler)

    dataBase = DataBaseHandler(coms=coms, db_name=db_name, user=db_username, password=db_password, clear_database=True)
    task_handler.add_thread(dataBase.run, db_name, dataBase)
    task_handler.start()

    try:
        test_sensor = sensor_parent(coms=coms, config={'tap_request': None, 'publisher': 'no', 'interval_pub': 'NA'}, name='save_byte_data_test', db_name=db_name, table_structure=table_structure)
        task_handler.add_thread(test_sensor.run, test_sensor.get_sensor_name(), test_sensor)
        task_handler.start()
        
        for request in dataBase._threadWrapper__request:
            if request[0] == 'create_table_external':
                request_num = request[4]

        while dataBase.check_request(request_num) is False:
            pass
        test_sensor.save_byte_data(table='save_byte_data_test_table', data={'first': [[11]]})
        
        for request in dataBase._threadWrapper__request:
            if request[0] == 'save_byte_data':
                request_num = request[4]
        while dataBase.check_request(request_num) is False:
            pass
        assert 'x0b' in dataBase.get_data(['save_byte_data_test_table', 0])

    finally:
        dataBase._DataBaseHandler__close_sql_connections()
        task_handler.kill_tasks()

@pytest.mark.sensor_parent_tests
def test_preprocess_data():
    #NOTE: as the preprocess function is currently written, it works, but partial_start is never false; when it should be, the blank bytes object is treated as the partial start packet

    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='preprocess_test')
    
    # delimiter and terminator are binary, partial start packet, complete end packet
    data = [b'dangerous to go alone,\r\n$take this.\r\n']
    data, partial_start, partial_end = test_sensor.preprocess_data(data=data, delimiter=b'$', terminator=b'\r\n')
    assert data == [b'dangerous to go alone,\r\n', b'take this.\r\n']
    assert partial_start == True
    assert partial_end == False
    
    # delimiter and terminator are ints, complete start packet, partial end packet
    data = [b'$To be, or not to be,\r\n$that is the']    
    data, partial_start, partial_end = test_sensor.preprocess_data(data=data, delimiter=0x24, terminator=0x0D0A)
    assert data == [b'', b'To be, or not to be,\r\n', b'that is the']
    assert partial_start == True
    assert partial_end == True

#potential issue with preprocess_ccsds_data: if the first packet is bad, it might not be recognized as a bad packet, and if all the headers get messed up, it could look like we're getting no data
@pytest.mark.sensor_parent_tests
def test_preprocess_ccsds_data_good_packet():
    # tests
    sensor_config.sync_word_len = 4
    sensor_config.ccsds_header_len = 5
    sensor_config.sync_word = 0x352ef853
    sensor_config.packet_len_addr1 = 8
    sensor_config.packet_len_addr2 = 9

    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='Johnny')
    
    with open('sensor_interface_api/testing/sensor_test/good_test_packet.bin', 'rb+') as file:
        data = [file.read()]
    
    if file is not None:
        packets, bad_packets = test_sensor.preprocess_ccsds_data(data=data)
        assert len(packets) == 1
        assert bytes(packets[0]) in data[0]
        assert bad_packets is False

@pytest.mark.sensor_parent_tests
def test_preprocess_ccsds_data_incomplete_packets():
    #incomplete_test_packet_1 contains an incomplete packet followed by the first half of a good packet
    #incomplete_test_packet_2 contains the second half of the good packet and a fragment of a packet header

    sensor_config.sync_word_len = 4
    sensor_config.ccsds_header_len = 5
    sensor_config.sync_word = 0x352ef853
    sensor_config.packet_len_addr1 = 8
    sensor_config.packet_len_addr2 = 9

    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='Josh')
    
    with open('sensor_interface_api/testing/sensor_test/incomplete_test_packet_1.bin', 'rb+') as file1:
        with open('sensor_interface_api/testing/sensor_test/incomplete_test_packet_2.bin', 'rb+') as file2:
            data1 = [file1.read()]
            data2 = [file2.read()]
            full_data = bytes().join(data1) + bytes().join(data2)
    
    if file1 is not None and file2 is not None:
        packets, bad_packets = test_sensor.preprocess_ccsds_data(data=data1)
        assert len(packets) == 0
        assert bad_packets is False

        packets, bad_packets = test_sensor.preprocess_ccsds_data(data=data2)
        assert len(packets) == 1
        print(f"{packets=}")
        assert bytes(packets[0]) in full_data
        assert bad_packets is False

@pytest.mark.sensor_parent_tests
def test_preprocess_ccsds_data_bad_packet():
    sensor_config.sync_word_len = 4
    sensor_config.ccsds_header_len = 5
    sensor_config.sync_word = 0x352ef853
    sensor_config.packet_len_addr1 = 8
    sensor_config.packet_len_addr2 = 9

    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='Todd')
    
    with open('sensor_interface_api/testing/sensor_test/bad_test_packet.bin', 'rb+') as file:
        data = [file.read()]
    
    if file is not None:
        packets, bad_packets = test_sensor.preprocess_ccsds_data(data=data)
        assert len(packets) == 1
        assert bytes(packets[0]) in data[0]
        assert bad_packets is True

@pytest.mark.sensor_parent_tests
def test_int_to_bytes():
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='Phillip')
    
    assert test_sensor.int_to_bytes(0) == (0).to_bytes()
    assert test_sensor.int_to_bytes(3) == (3).to_bytes()
    assert test_sensor.int_to_bytes(1234567) == (1234567).to_bytes(length=3)