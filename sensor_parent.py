'''
    This class enforces the correct structure onto the sub-sensors class. And preforms most of the needed functions for a sensor class. 
'''

#python imports
import threading
import copy
import time
import re
from datetime import datetime

#Custom imports
from threading_python_api.threadWrapper import threadWrapper # pylint: disable=e0401
from sensor_interface_api.sensor_html_page_generator import sensor_html_page_generator # pylint: disable=e0401

class sensor_parent(threadWrapper, sensor_html_page_generator):
    '''
         There are a few functions that your sensor class must implement,

         __init__(self, coms) : every python class needs this.
         get_html_page : this returns a custom html page for your sensor
         set_sensor_status : Returns where the sensor is running or not. NOTE: threadWrapper has its own set_status, used by the system, so thats why the name is longer. 
         get_sensor_status : should return Running, Error, Not running. 
         get_data_received : Returns the last sample the sensor returned.
         get_taps : Returns a list of taps that the user has requested for this class. 
         process_data : This is the function that is called when the data_received event is called. 
         make_data_tap : sends a request to the serial listener telling it to send data to this class.
         send_tab : this function is what the serial listener calls to send the tab to this class.
         create_tab : this function creates a tab to this class.
         get_sensor_name : This function returns the name of the sensor. The users class need to implement this.
         start_publisher : Starts a data publisher on its own thread. (For active publishers only)
         publish : publishes data
         set_publish_data : the users class calls this function, it sets data to be published.
         has_been_published : Returns a bool that is true if the data has been publish and false otherwise. 
         event_listener : this function waits for events to happen then it calls the function corresponding to that event
         publish_data : Notifies the system that data is published of the given data type. 
         add_graph_data : adds an x and y point
         get_data_report : returns the data report to the webpage
         get_graph_names : returns the list of graphs for this sensor
         get_last_published_data : returns the last thing published and the time it was published at.
         preprocess_data : this function may work for you if your data comes in in chucks, and needs to be put back together. See the function docer string. 
         set_thread_status : set the status for your processing threads. 
         get_data_name : return data name
         save_byte_data : saves byte data into the database.
         save_data : saves data into the database.

         ARGS:
            coms : the message handler, that almost every class uses in this system.
            config : the configuration created by the user. 
            name : name of this sensor
            event_dict : any events the user wishes to add. 
    '''
    def __init__(self, coms, config:dict, name:str, events_dict:dict = {}, graphs:list = None, max_data_points = 10, table_structure: dict = None, db_name: str = '') -> None: # pylint: disable=w0102,r0915
        ###################### Sensor information ################################
        self.__coms = coms
        self.__status_lock = threading.Lock()
        self.__status = "Not Running"
        self.__data_received = {}
        self.__data_lock = threading.Lock()
        self.__tap_requests = []
        self.__tap_requests_lock = threading.Lock()
        self.__config = config
        self.__config_lock = threading.Lock()
        self.__publish_data = []
        self.__publish_data_lock = threading.Lock()
        self.__publish_data = []
        self.__has_been_published  = True
        self.__has_been_published_lock = threading.Lock()
        self.__name_lock = threading.Lock()
        #check to make sure the name is a valid name
        pattern = r'^[a-zA-Z0-9_.-]+$' # this is the patter for valid file names. 
        if bool(re.match(pattern, name)):
            self.__name = name
        else :
            raise RuntimeError(f'The name {name}, is not a valid sensor name because it does not match the stander file format. Please change the name.')
        self.__data_name = self.__config['publish_data_name']
        self.__events = events_dict
        self.__active = False
        self.__active__lock = threading.Lock()
        self.__interval_pub = self.__config['interval_pub']
        self.__taps_lock = threading.Lock()
        self.__last_published_data = {
            'time' : 'NA',
            'data' : 'NA'
        }
        self.__last_published_data_lock = threading.Lock()
        self.__db_name = db_name
        ##########################################################################
        ################ Set up the database tables according ####################
        if not table_structure is None:
            self.__coms.send_request(self.__db_name, ['create_table_external', table_structure])
        ##########################################################################
        ############ Set up the sensor according to the config file ############
        if self.__config['tap_request'] is not None:
            for request in self.__config['tap_request']:
                self.make_data_tap(request)
                self.__data_received[request] = [] #make a spot in the data received for this tap info to be added to. 

                # Now we need to build the event dict
                self.__events[f'data_received_for_{request}'] = self.process_data
            self.__taps = self.__config['tap_request']
        else :
            self.__taps = ['None']
        if self.__config['publisher'] == 'yes':
            if self.__config['passive_active'] == 'active':
                self.__active = True
                self.start_publisher()
        ##########################################################################
        ##################### set up the threadWrapper stuff #####################
        self.__function_dict = { 
            'create_tab' : self.create_tab,
        }
        threadWrapper.__init__(self, self.__function_dict, self.__events)
        ##########################################################################
        ###################### set up the html graphs stuff ######################
        self.__graphs = graphs
        self.__max_data_points = max_data_points
        self.__data_report = {}
        if not self.__graphs is None:
            for graph in self.__graphs:
                self.__data_report[graph] = {
                    'x' : [],
                    'y' : [],
                }
        self.__data_report_lock = threading.Lock()
        self.__graphs_lock = threading.Lock()
        ##########################################################################
        ################## set up the html page generation stuff #################
        sensor_html_page_generator.__init__(self, self.__name, self.__config, not self.__graphs is None)
        self.__html_file_path = f'templates/{self.__name}.html'
        # we probably dont need this, but we might one day and I dont want to 
        # debug it if we do
        self.__html__lock = threading.Lock()
        ##########################################################################
    def get_html_page(self):
        '''
            Returns an file path to an html file.
        '''
        with self.__html__lock:
            temp_token = self.generate_html_file(self.__html_file_path)
        return temp_token
    def get__sensor_status(self):
        '''
            Returns the status of the sensor, it is up to the user to set this status, this function returns that status to the server. 
        '''
        with self.__status_lock:
            temp = self.__status
        return temp
    def set_sensor_status(self, status):
        '''
            User calls this function to set a status, must be Running, Error, Not running.
        '''
        with self.__status_lock:
            if status == 'Running':
                self.__status = status
            elif status == 'Error':
                self.__status = status
            elif status == 'Not running':
                self.__status = status
            else :
                raise RuntimeError(f"{status} is not a valid status.")
    def set_thread_status(self, status):
        '''
            This function is for setting the threading status AKA your processing threads that get started. USE 'Running', 'Complete' or 'Error'.
        '''
        threadWrapper.set_status(self, status)
    def process_data(self):
        '''
            This function gets called when the data_received event happens. NOTE: It should be short, because it holds up this whole
            thread. If you have large amounts of processing have this function create another thread and process the data on that. 
        '''
        raise NotImplementedError("process_data Not implemented, should process that last data received (data is stored in the __data_received variable).")
    def get_data_received(self, tap_name):
        '''
            Returns the last data point collected from the given tap

            ARGS:
                tap_name : the name of the tap you want to get data out of. 
        '''
        with self.__data_lock:
            data_copy = copy.deepcopy(self.__data_received[tap_name])
        return data_copy
    def make_data_tap(self, name_of_class_to_make_tap):
        '''
            This requests sends a request to the class you want and then that class creates a tap for you to listen too.
        '''
        with self.__name_lock:
            temp_name_token = self.__name
        self.__coms.send_request(name_of_class_to_make_tap, ['create_tap', self.send_tap, temp_name_token])
    def send_tap(self, data, sender):
        '''
            This is the function that is called by the class you asked to make a tap.
        '''
        with self.__data_lock:
            self.__data_received[sender] = copy.deepcopy(data) #NOTE: This could make things really slow, depending on the data rate.
        threadWrapper.set_event(self, f'data_received_for_{sender}')
    def get_taps(self):
        '''
            This function returns the list of requested taps 
        '''
        with self.__taps_lock:
            temp = self.__taps
        return temp
    def create_tab(self, args):
        '''
            This function creates a tab, a tab will send the data it receives from the requested class to the class that created the tab.
            ARGS:
                args[0] : tab function to call.  
        '''
        with self.__tap_requests_lock:
            self.__tap_requests.append(args[0])
        with self.__config_lock:
            self.__config['subscribers'] = self.__tap_requests
    def get_sensor_name(self):
        '''
            This function returns the name of the sensor.
        '''
        with self.__name_lock:
            temp = self.__name
        return temp
    def start_publisher(self):
        '''
            If it is an active publisher then we will start it on its own thread.
        '''
        with self.__name_lock:
            temp_name_token = self.__name
        self.__coms.send_request('task_handler', ['add_thread_request_func', self.publish, f'publisher for {temp_name_token}', self])
    def publish(self):
        '''
            Publishes the data to all the other threads that have requested taps.
        '''
        with self.__active__lock:
            active = self.__active
            if active:
                interval_pub = self.__interval_pub
        if active:
            while True:
                with self.__publish_data_lock:
                    data_copy = self.__publish_data #I am making a copy of the data here, so the data is better protected.
                with self.__tap_requests_lock:
                    tap_request_copy = copy.deepcopy(self.__tap_requests)
                for subscriber in tap_request_copy:
                    temp  = data_copy #The reason I copy that data again is so that every subscriber gets its own copy of the data it can manipulate. 
                    subscriber.send_tap(temp)
                with self.__last_published_data_lock:
                    self.__last_published_data['time'] = str(datetime.now())
                    try :
                        self.__last_published_data['data'] = ' , '.join(data_copy[-1])
                    except : # pylint: disable=w0702
                        self.__last_published_data['data'] = 'Unable to convert last data to string for reporting, this should not effect performance of the publishing.'
                with self.__has_been_published_lock:
                    self.__has_been_published = True
                time.sleep(interval_pub)
        else :
            with self.__publish_data_lock:
                data_copy = self.__publish_data #I am making a copy of the data here, so the data is better protected.
            with self.__tap_requests_lock:
                tap_request_copy = copy.deepcopy(self.__tap_requests)
            for subscriber in tap_request_copy:
                temp  = data_copy #The reason I copy that data again is so that every subscriber gets its own copy of the data it can manipulate. 
                subscriber.send_tap(temp)
            with self.__last_published_data_lock:
                self.__last_published_data['time'] = str(datetime.now())
                try:
                    self.__last_published_data['data'] = ' , '.join(map(str,data_copy[-1]))
                except : # pylint: disable=w0702
                    self.__last_published_data['data'] = 'Unable to convert last data to string for reporting, this should not effect performance of the publishing.'
        with self.__has_been_published_lock:
            self.__has_been_published = True
    def set_publish_data(self, data):
        '''
            This function takes a list of list to publish.

            NOTE: This will erase the old data to publish, if this is a problem you can check, the has_been_published function to see if the data has been published already. 

            ARGS : 
                data : list of list to publish to the system. Example [[1, 2, 3], [4, 5, 6]]
        '''
        with self.__publish_data_lock:
            self.__publish_data = data
        with self.__has_been_published_lock:
            self.__has_been_published = False
    def has_been_published(self):
        '''
            This returns a boolean about where or not the last message has been published. 
        '''
        with self.__has_been_published_lock:
            copy_token = self.__has_been_published
        return copy_token
    def add_graph_data(self, graph, x, y):
        '''
            This function adds the new x, y points to the data that should be reported to the web page
            
            ARGS: 
                graph : name of the graph you want to add to
                x : list of x data points
                y : list of y data points
        '''
        with self.__data_report_lock:
            self.__data_report[graph]['x'] = self.__data_report[graph]['x'] + x
            self.__data_report[graph]['y'] = self.__data_report[graph]['y'] + y

            x_data_over = 0
            y_data_over = 0

            if len(self.__data_report[graph]['x']) > self.__max_data_points:
                x_data_over = len(self.__data_report[graph]['x']) - self.__max_data_points
            for _ in range(x_data_over):
                self.__data_report[graph]['x'].pop(0)

            if len(self.__data_report[graph]['y']) > self.__max_data_points:
                y_data_over = len(self.__data_report[graph]['y']) - self.__max_data_points
            for _ in range(y_data_over):
                self.__data_report[graph]['y'].pop(0)
    def get_data_report(self):
        '''
            Returns a copy of the data report to the requester. 
        '''
        with self.__data_report_lock:
            copy_data_report = copy.deepcopy(self.__data_report)
        return copy_data_report
    def get_graph_names(self):
        '''
            Returns a copy of the graph names to the requester. 
        '''
        with self.__graphs_lock:
            copy_graph_names = copy.deepcopy(self.__graphs)
        return copy_graph_names
    def get_last_published_data(self):
        '''
            Returns a copy of the last data published to the requester. 
        '''
        with self.__last_published_data_lock:
            copy_last_data_published = copy.deepcopy(self.__last_published_data)
        return copy_last_data_published
    def save_data(self, table, data):
        '''
            This function takes in a dict of data to save. NO byte data

            ARGS:
                table : name of the table you want to send data to 
                data : list of the data to store. NOTE: if you are saving into table with multiple values per row, then it should be a list of list, where each sub list is each value per row in order.
                    Example : table : arg1, arg2, arg3 -> save_data(table = 'table', data = {'arg1' : ['hello', 'hello'], 'arg2' : ['world', 'world']}]) 
        '''
        self.__coms.send_request(self.__db_name, ['save_data_group', table, data, self.__name])
    def save_byte_data(self, table, data):
        '''
            This function takes in a dict of data to save, but can contain byte data

            ARGS:
                table : name of the table you want to send data to 
                data : list of the data to store. NOTE: if you are saving into table with multiple values per row, then it should be a list of list, where each sub list is each value per row in order.
                    Example : table : arg1, arg2, arg3 -> save_data(table = 'table', data = {'arg1' : ['hello', 'hello'], 'arg2' : ['world', 'world']}]) 
        '''
        self.__coms.send_request('Data Base', ['save_byte_data', table, data, self.__name])


    def preprocess_data(self, data, delimiter:bytearray, terminator:bytearray):
        '''
            This function will go through your data and find the delimiter you gave the function, and then put messages together.
            Example delimiter = b'$'
            data = '$hello$world'
            return ['hello', 'world']

            NOTE: it drops the delimiter but not the terminator.

            If your data follows this structure this function will work well. However, if your data does not have a delimiter or header,
            this function will not work for your needs.  
        '''
        if isinstance(delimiter, int):
            delimiter = self.int_to_bytes(delimiter)
        if isinstance(terminator, int):
            terminator = self.int_to_bytes(terminator)
        data = bytes().join(data) # make the list into one long sequence so it is possible to process the data.
        found_packets = data.split(delimiter)

        #check for partial packets at the end and the beginning
        partial_end_packet = False
        partial_start_packet = False
        if terminator not in found_packets[-1]:
            partial_end_packet = True
        if terminator not in found_packets[0] or delimiter not in found_packets[0]:
            partial_start_packet = True
            
        return found_packets, partial_start_packet, partial_end_packet
    def int_to_bytes(seflf, integer_value):
        '''
            converts an integer to correct size byte object 
        '''
        if integer_value == 0:
            return b'\x00'
        
        num_bytes = (integer_value.bit_length() + 7) // 8
        return integer_value.to_bytes(num_bytes, byteorder='big')
    def get_data_name(self):
        '''
            This function returns the name of the data that this class publishes
        '''
        return self.__data_name
