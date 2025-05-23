'''
    Unit test for collect_sensor
'''

#Python imports
import pytest
import yaml
from unittest.mock import MagicMock
from io import StringIO

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

#TODO: elses on lock failure test

db_name = 'unit_tests_sensor_parent'

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
    thread_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=thread_handler)

    dataBase = DataBaseHandler(coms=coms, db_name=db_name, user='ground_cse', password='usuCSEgs', clear_database=True)
    thread_handler.add_thread(dataBase.run, db_name, dataBase)
    thread_handler.start()

    try:
        test_sensor = sensor_parent(coms=coms, config={'tap_request': ['this', 'that'], 'publisher': 'no', 'interval_pub': 'NA'}, name='good_sensor', db_name=db_name, table_structure=table_structure,
                                    graphs=['one', 'two', 'three'])

        thread_handler.add_thread(test_sensor.run, test_sensor.get_sensor_name(), test_sensor)
        thread_handler.start()

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
        thread_handler.kill_tasks()

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

    try:
        tapper.make_data_tap('source')

        while thread_handler.check_request('source', 1) is False:
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
        coms.send_request.assert_not_called()
    finally:
        thread_handler.kill_tasks()

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

#TODO
@pytest.mark.sensor_parent_tests
def test_create_tap():
    #real talk, should I just put all the tap related stuff in one long ass test?
    pass

@pytest.mark.sensor_parent_tests
def test_start_publisher():
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

#TODO: deal with active sensor - how do I break out of the while loop???
@pytest.mark.sensor_parent_tests
def test_publish():
    good_data = ['abc', 'def', 'ghi']
    bad_data = [MagicMock]

    sensor_parent.start_publisher = MagicMock()

    # ######################## Active sensor #######################
    # active_test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'yes', 'passive_active': 'active', 'interval_pub': 1}, name='active')
    # active_test_sensor.set_up_taps()

    # active_test_sensor.set_publish_data(good_data)
    # active_test_sensor.publish()
    # assert active_test_sensor.get_last_published_data()['data'] == 'g , h , i'

    # active_test_sensor.set_publish_data(bad_data)
    # active_test_sensor.publish()
    # assert active_test_sensor.get_last_published_data()['data'] == "Unable to convert last data to string for reporting, this should not effect performance of the publishing."

    # # failure to acquire lock
    # active_test_sensor._sensor_parent__last_published_data_lock.acquire()
    # if (active_test_sensor._sensor_parent__last_published_data_lock.locked()):
    #     with pytest.raises(RuntimeError) as excinfo:
    #         active_test_sensor.publish()
        
    #     assert "Could not acquire published data lock" in str(excinfo.value)
    # active_test_sensor._sensor_parent__last_published_data_lock.release()

    # # failure to acquire other lock
    # active_test_sensor._sensor_parent__has_been_published_lock.acquire()
    # if (active_test_sensor._sensor_parent__has_been_published_lock.locked()):
    #     with pytest.raises(RuntimeError) as excinfo:
    #         active_test_sensor.publish()
        
    #     assert "Could not acquire has been published lock" in str(excinfo.value)
    # active_test_sensor._sensor_parent__has_been_published_lock.release()

    ####################### Passive sensor #######################
    passive_test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'yes', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='passive')
    passive_test_sensor.set_up_taps()

    passive_test_sensor.set_publish_data(good_data)
    passive_test_sensor.publish()
    assert passive_test_sensor.get_last_published_data()['data'] == 'g , h , i'

    passive_test_sensor.set_publish_data(bad_data)
    passive_test_sensor.publish()
    assert passive_test_sensor.get_last_published_data()['data'] == "Unable to convert last data to string for reporting, this should not effect performance of the publishing."

    # failure to acquire lock
    passive_test_sensor._sensor_parent__last_published_data_lock.acquire()
    if (passive_test_sensor._sensor_parent__last_published_data_lock.locked()):
        with pytest.raises(RuntimeError) as excinfo:
            passive_test_sensor.publish()
        
        assert "Could not acquire last published data lock" in str(excinfo.value)
    passive_test_sensor._sensor_parent__last_published_data_lock.release()

    # failure to acquire lock
    passive_test_sensor._sensor_parent__has_been_published_lock.acquire()
    if (passive_test_sensor._sensor_parent__has_been_published_lock.locked()):
        with pytest.raises(RuntimeError) as excinfo:
            passive_test_sensor.publish()
        
        assert "Could not acquire has been published lock" in str(excinfo.value)
    passive_test_sensor._sensor_parent__has_been_published_lock.release()

#TODO
@pytest.mark.sensor_parent_tests
def test_send_data_to_tap():
    coms = messageHandler()
    thread_handler = taskHandler(coms=coms)
    coms.set_thread_handler(thread_handler)

    receiver = sensor_parent(coms=coms, config={'tap_request': ['sender'], 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='receiver')
    sender = sensor_parent(coms=coms, config={'tap_request': None, 'publisher': 'yes', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='sender')

    thread_handler.add_thread(receiver.run, receiver.get_sensor_name(), receiver)
    thread_handler.add_thread(sender.run, sender.get_sensor_name(), sender)
    thread_handler.start()

    try:
        data = ['abc', 'def']
        receiver.set_up_taps()
        sender.set_up_taps()

        while sender.check_request(1) is False:
            pass

        sender.set_publish_data(data)
        sender.send_data_to_tap()
        
        assert receiver._sensor_parent__data_received['sender'] == data
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
        print("done1")
        
        data = [123, 45]
        # failure to acquire tap requests lock
        sender._sensor_parent__tap_requests_lock.acquire()
        print(F"{receiver._sensor_parent__data_buffer_overwrite=}")
        if (sender._sensor_parent__tap_requests_lock.locked()):
            print("locked")
            with pytest.raises(RuntimeError) as excinfo:
                sender.send_data_to_tap()
            assert "Could not acquire tap requests lock" in str(excinfo.value)
            print("error raised")
        print("releasing...")
        sender._sensor_parent__tap_requests_lock.release()
        print("done2")
    finally:
        thread_handler.kill_tasks()

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
def test_save_data():
    #test if read_from_file is true
    #plan: mock logger.send_log and assert called with f"{sensor_name} ended"

    #test if read_from_file is false
    table_structure = {'save_data_test_table': [['first', 0, 'int'], ['second', 0, 'float'], ['third', 0, 'string']]}
    
    coms = messageHandler()
    thread_handler = taskHandler(coms=coms)
    coms.set_thread_handler(threadHandler=thread_handler)

    dataBase = DataBaseHandler(coms=coms, db_name=db_name, user='ground_cse', password='usuCSEgs', clear_database=True)
    thread_handler.add_thread(dataBase.run, db_name, dataBase)
    thread_handler.start()

    try:
        test_sensor = sensor_parent(coms=coms, config={'tap_request': None, 'publisher': 'no', 'interval_pub': 'NA'}, name='save_data_test', db_name=db_name, table_structure=table_structure)
        thread_handler.add_thread(test_sensor.run, test_sensor.get_sensor_name(), test_sensor)
        thread_handler.start()
        
        for request in dataBase._threadWrapper__request:
            if request[0] == 'create_table_external':
                request_num = request[4]

        while dataBase.check_request(request_num) is False:
            pass

        print(f"\n\n{dataBase._DataBaseHandler__conn.is_connected()=}\n\n")
        
        # issue is here now - cursor is apparently unconnected or something :/
        test_sensor.save_data(table='save_data_test_table', data={'first': [1], 'second': [0.5], 'third': ['x']})
        
        for request in dataBase._threadWrapper__request:
            if request[0] == 'save_data_group':
                request_num = request[4]
        
        while dataBase.check_request(request_num) is False:
            pass
        
        print(f'\n\n{dataBase.get_data(['save_data_test_table', 0])=}\n\n')
        assert '1,0.5,x' in dataBase.get_data(['save_data_test_table', 0])

    finally:
        # dataBase._DataBaseHandler__close_sql_connections()
        thread_handler.kill_tasks()

#TODO: ew coms
@pytest.mark.sensor_parent_tests
def test_save_byte_data():
    pass

#TODO
@pytest.mark.sensor_parent_tests
def test_preprocess_data():
    pass

#TODO: this is going to be tricky
@pytest.mark.sensor_parent_tests
def test_preprocess_ccsds_data():
    pass

@pytest.mark.sensor_parent_tests
def test_int_to_bytes():
    test_sensor = sensor_parent(coms=None, config={'tap_request': None, 'publisher': 'no', 'passive_active': 'passive', 'interval_pub': 'NA'}, name='Phillip')
    
    assert test_sensor.int_to_bytes(0) == (0).to_bytes()
    assert test_sensor.int_to_bytes(3) == (3).to_bytes()
    assert test_sensor.int_to_bytes(1234567) == (1234567).to_bytes(length=3)