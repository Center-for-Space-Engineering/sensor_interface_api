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
import system_constants as sys_c # pylint: disable=e0401
from logging_system_display_python_api.logger import loggerCustom # pylint: disable=e0401


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
         make_data_tap : sends a request to another class telling it to send data to this class.
         send_tap : this function is what the serial listener calls to send the tab to this class.
         create_tap : this function creates a tab to this class.
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
    def __init__(self, coms, config:dict, name:str, events_dict:dict = {}, graphs:list = None, max_data_points = 10, table_structure: dict = None, db_name: str = '', data_overwrite_exception:bool = True) -> None: # pylint: disable=w0102,r0915
        ###################### Sensor information ################################
        self.__logger = loggerCustom("logs/sensor_parent.txt")
        self.__coms = coms
        self.__status_lock = threading.Lock()
        self.__status = "Not Running"
        self.__data_received = {}
        self.__data_lock = threading.Lock()
        self.__tap_requests = []
        self.__tap_requests_lock = threading.Lock()
        self.__tap_subscribers = []
        self.__tap_subscribers_lock = threading.Lock()
        self.__config = config
        self.__config_lock = threading.Lock()
        self.__publish_data = []
        self.__publish_data_lock = threading.Lock()
        self.__publish_data = []
        self.__taps = []
        self.__has_been_published  = True
        self.__has_been_published_lock = threading.Lock()
        self.__name_lock = threading.Lock()
        self.__data_buffer_overwrite = False
        self.__data_buffer_overwrite_lock = threading.Lock()
        self.__data_overwrite_exception = data_overwrite_exception
        #check to make sure the name is a valid name
        pattern = r'^[a-zA-Z0-9_.-]+$' # this is the pattern for valid file names. 
        if bool(re.match(pattern, name)):
            self.__name = name
        else :
            raise RuntimeError(f'The name {name}, is not a valid sensor name because it does not match the standard file format. Please change the name.')
        # self.__logger = loggerCustom(f"logs/sensor_parent_{self.__name}.txt")
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
        ############ Set up the Events according to the config file ############
        if self.__config['tap_request'] is not None:
            for request in self.__config['tap_request']:
                # Now we need to build the event dict
                self.__events[f'data_received_for_{request}'] = self.process_data
        ##################### set up the threadWrapper stuff #####################
        self.__function_dict = { 
            'create_tap' : self.create_tap,
            'ready_for_data': self.ready_for_data
        }
        threadWrapper.__init__(self, self.__function_dict, self.__events)
        ##########################################################################
        ################## set up the html page generation stuff #################
        sensor_html_page_generator.__init__(self, self.__name, self.__config, not self.__graphs is None)
        self.__html_file_path = f'templates/{self.__name}.html'
        # we probably dont need this, but we might one day and I dont want to 
        # debug it if we do
        self.__html_lock = threading.Lock()
        ##########################################################################
        ################## initialize byte array for incomplete packets ##########
        self.__extra_packet_data = bytearray()
    def set_up_taps(self):
        '''
            Set up the taps for the sensor class. This needs to be called out side of the __init__ function
            beacause all the sensors need to be created before we can create the tap network. 
        '''
        ############ Set up the sensor according to the config file ############
        if self.__config['tap_request'] is not None:
            for request in self.__config['tap_request']:
                self.make_data_tap(request)
                self.__data_received[request] = [] #make a spot in the data received for this tap info to be added to. 
            self.__taps = self.__config['tap_request']
        else :
            self.__taps = ['None']
        if self.__config['publisher'] == 'yes':
            if self.__config['passive_active'] == 'active':
                self.__active = True
                self.start_publisher()
        ##########################################################################
    def get_html_page(self):
        '''
            Returns an file path to an html file.
        '''
        if self.__html_lock.acquire(timeout=1): # pylint: disable=R1732
            temp_token = self.generate_html_file(self.__html_file_path)
            self.__html_lock.release()
        else : 
            raise RuntimeError("Could not acquire html lock")
        return temp_token
    def get_sensor_status(self):
        '''
            Returns the status of the sensor, it is up to the user to set this status, this function returns that status to the server. 
        '''
        if self.__status_lock.acquire(timeout=1): # pylint: disable=R1732
            temp = self.__status
            self.__status_lock.release()
        else : 
            raise RuntimeError("Could not acquire status lock")
        return temp
    def set_sensor_status(self, status):
        '''
            User calls this function to set a status, must be Running, Error, Not running.
        '''
        if self.__status_lock.acquire(timeout=1): # pylint: disable=R1732
            if status.lower() =='running':
                self.__status = status
            elif status.lower() == 'error':
                self.__status = status
            elif status.lower() == 'not running':
                self.__status = status
            else :
                self.__status_lock.release()
                raise RuntimeError(f"{status} is not a valid status.")
            self.__status_lock.release()
        else :
            raise RuntimeError("Could not acquire status lock")
    def set_thread_status(self, status):
        '''
            This function is for setting the threading status AKA your processing threads that get started. USE 'Running', 'Complete' or 'Error'.
        '''
        threadWrapper.set_status(self, status)
    def ready_for_data(self):
        if self.__data_buffer_overwrite:
            return False
        else:
            return True
    def process_data(self, event):
        '''
            This function gets called when the data_received event happens. NOTE: It should be short, because it holds up this whole
            thread. If you have large amounts of processing have this function create another thread and process the data on that. 
        '''
        self.__logger.send_log('here')
        raise NotImplementedError("process_data Not implemented, should process that last data received (data is stored in the __data_received variable).")
    def get_data_received(self, tap_name):
        '''
            Returns the last data point collected from the given tap

            ARGS:
                tap_name : the name of the tap you want to get data out of. 
        '''
        if self.__data_buffer_overwrite_lock.acquire(timeout=5): # pylint: disable=R1732
            self.__data_buffer_overwrite = False
            self.__data_buffer_overwrite_lock.release()
        else :
            raise RuntimeError("Could not acquire data buffer overwrite lock.")
        if self.__data_lock.acquire(timeout=1): # pylint: disable=R1732
            data_copy = copy.deepcopy(self.__data_received[tap_name])
            self.__data_lock.release()
        else : 
            raise RuntimeError("Could not acquire data lock")
        return data_copy
    def make_data_tap(self, name_of_class_to_make_tap):
        '''
            This requests sends a request to the class you want and then that class creates a tap for you to listen too.
        '''
        if self.__name_lock.acquire(timeout=1): # pylint: disable=R1732
            temp_name_token = self.__name
            self.__name_lock.release()
        else :
            raise RuntimeError("Could not acquire name lock")
        self.__coms.send_request(name_of_class_to_make_tap, ['create_tap', self.send_tap, temp_name_token])
    def send_tap(self, data, sender):
        '''
            This is the function that is called by the class you asked to make a tap.
        '''
        if self.__data_buffer_overwrite_lock.acquire(timeout=5): # pylint: disable=R1732
            if len(data) <= 0:
                self.__data_buffer_overwrite = False
                self.__data_buffer_overwrite_lock.release()
                return
            self.__data_buffer_overwrite_lock.release()
        else :
            raise RuntimeError("Could not acquire data buffer overwrite lock.")
        
        not_ready_bool = True

        if self.__data_buffer_overwrite_lock.acquire(timeout=5): # pylint: disable=R1732
            not_ready_bool = self.__data_buffer_overwrite
            self.__data_buffer_overwrite_lock.release()
        else :
            raise RuntimeError("Could not acquire data buffer overwrite lock.")
        
        while not_ready_bool == True:
            if self.__data_buffer_overwrite_lock.acquire(timeout=5): # pylint: disable=R1732
                not_ready_bool = self.__data_buffer_overwrite
                self.__data_buffer_overwrite_lock.release()
            else :
                raise RuntimeError("Could not acquire data buffer overwrite lock.")
            time.sleep(1)

        if self.__data_lock.acquire(timeout=1): # pylint: disable=R1732
            self.__data_received[sender] = copy.deepcopy(data) #NOTE: This could make things really slow, depending on the data rate.
            threadWrapper.set_event(self, f'data_received_for_{sender}')
            if sys_c.read_from_file:
                self.__coms.send_request(sys_c.file_listener_name, ['mark_started', sender])
            self.__data_lock.release()
        else :
            raise RuntimeError("Could not acquire data lock")          
    def get_taps(self):
        '''
            This function returns the list of requested taps 
        '''
        if self.__taps_lock.acquire(timeout=1): # pylint: disable=R1732
            temp = self.__taps
            self.__taps_lock.release()
        else :
            raise RuntimeError("Could not acquire taps lock")
        return temp
    def create_tap(self, args):
        '''
            This function creates a tap, a tap will send the data it receives from the requested class to the class that created the tap.
            ARGS:
                args[0] : tab function to call.  
                args[1] : name of subscriber.  
        '''
        if args[0] != None:
            if self.__tap_requests_lock.acquire(timeout=1): # pylint: disable=R1732
                self.__tap_requests.append(args[0])
                self.__tap_requests_lock.release()
            else :
                raise RuntimeError("Could not acquire tap requests lock")
            if self.__tap_subscribers_lock.acquire(timeout=1): # pylint: disable=R1732
                self.__tap_subscribers.append(args[1])
                self.__tap_subscribers_lock.release()
            else : 
                raise RuntimeError("Could not acquire config lock")
    def get_sensor_name(self):
        '''
            This function returns the name of the sensor.
        '''
        if self.__name_lock.acquire(timeout=1): # pylint: disable=R1732
            temp = self.__name
            self.__name_lock.release()
        else :
            raise RuntimeError("Could not acquire name lock")
        return temp
    def start_publisher(self):
        '''
            If it is an active publisher then we will start it on its own thread.
        '''
        if self.__name_lock.acquire(timeout=1): # pylint: disable=R1732
            temp_name_token = self.__name
            self.__name_lock.release()
        else : 
            raise RuntimeError("Could not acquire name lock")
        self.__coms.send_request('task_handler', ['add_thread_request_func', self.publish, f'publisher for {temp_name_token}', self])
    def publish(self): # pylint: disable=R0915
        '''
            Publishes the data to all the other threads that have requested taps.
        '''
        if self.__active__lock.acquire(timeout=1): # pylint: disable=R1732
            active = self.__active
            if active:
                interval_pub = self.__interval_pub
            self.__active__lock.release()
        else : 
            raise RuntimeError("Could not acquire active lock")
        if active:
            while True:              
                data_copy = self.send_data_to_tap()

                if self.__last_published_data_lock.acquire(timeout=1): # pylint: disable=R1732
                    self.__last_published_data['time'] = str(datetime.now())
                    try :
                        self.__last_published_data['data'] = ' , '.join(data_copy[-1])
                    except : # pylint: disable=w0702
                        self.__last_published_data['data'] = 'Unable to convert last data to string for reporting, this should not effect performance of the publishing.'
                    self.__last_published_data_lock.release()
                else :
                    raise RuntimeError("Could not acquire published data lock")
                if self.__has_been_published_lock.acquire(timeout=1): # pylint: disable=R1732
                    self.__has_been_published = True
                    self.__has_been_published_lock.release()
                else : 
                    raise RuntimeError("Could not acquire has been published lock")
                time.sleep(interval_pub)
        else :
            data_copy = self.send_data_to_tap()

            if self.__last_published_data_lock.acquire(timeout=1): # pylint: disable=R1732
                self.__last_published_data['time'] = str(datetime.now())
                try:
                    self.__last_published_data['data'] = ' , '.join(map(str,data_copy[-1]))
                except : # pylint: disable=w0702
                    self.__last_published_data['data'] = 'Unable to convert last data to string for reporting, this should not effect performance of the publishing.'
                self.__last_published_data_lock.release()
            else : 
                raise RuntimeError("Could not acquire last published data lock")
        if self.__has_been_published_lock.acquire(timeout=1): # pylint: disable=R1732
            self.__has_been_published = True
            self.__has_been_published_lock.release()
        else : 
            raise RuntimeError("Could not acquire has been published lock")
    def send_data_to_tap(self):
        '''
            this send the data to all the tap request we have received. 
        '''
        if self.__publish_data_lock.acquire(timeout=1): # pylint: disable=R1732
            data_copy = self.__publish_data #I am making a copy of the data here, so the data is better protected.
            self.__publish_data_lock.release()
        else :
            raise RuntimeError("Could not acquire publish data lock")
        
        config_copy_subscribers = []

        if self.__tap_subscribers_lock.acquire(timeout=1): # pylint: disable=R1732
            config_copy_subscribers = copy.deepcopy(self.__tap_subscribers)

            self.__tap_subscribers_lock.release()
        else : 
            raise RuntimeError('Could not acquire config lock')

        i = 0

        for subscriber in config_copy_subscribers: #loop on copies
            temp  = copy.deepcopy(data_copy) #The reason I copy that data again is so that every subscriber gets its own copy of the data it can manipulate.

            is_ready_req_id = self.__coms.send_request(subscriber, ['ready_for_data'])
            is_ready = self.__coms.get_return(subscriber, is_ready_req_id)

            while is_ready is not True:
                time.sleep(0.01)
                is_ready = self.__coms.get_return(subscriber, is_ready_req_id)
            
                if not is_ready:
                    is_ready_req_id = self.__coms.send_request(subscriber, ['ready_for_data'])
                    is_ready = self.__coms.get_return(subscriber, is_ready_req_id)

            if is_ready:
                if self.__tap_requests_lock.acquire(timeout=10): # pylint: disable=R1732
                    self.__tap_requests[i](temp, self.get_sensor_name()) # call the get sensor name so that the data is mutex protected.
                    i += 1
                    self.__tap_requests_lock.release()
                else : 
                    raise RuntimeError('Could not acquire tap requests lock')
        return data_copy      
    def set_publish_data(self, data):
        '''
            This function takes a list of list to publish.

            NOTE: This will erase the old data to publish, if this is a problem you can check, the has_been_published function to see if the data has been published already. 

            ARGS : 
                data : list of list to publish to the system. Example [[1, 2, 3], [4, 5, 6]]
        '''
        if self.__publish_data_lock.acquire(timeout=1): # pylint: disable=R1732
            self.__publish_data = data
            self.__publish_data_lock.release()
        else : 
            raise RuntimeError("Could not acquire publish data lock")
        if self.__has_been_published_lock.acquire(timeout=1): # pylint: disable=R1732
            self.__has_been_published = False
            self.__has_been_published_lock.release()
        else : 
            raise RuntimeError("Could not acquire has been published lock")
    def has_been_published(self):
        '''
            This returns a boolean about where or not the last message has been published. 
        '''
        if self.__has_been_published_lock.acquire(timeout=1): # pylint: disable=R1732
            copy_token = self.__has_been_published
            self.__has_been_published_lock.release()
        else :
            raise RuntimeError("Could not acquire has been published lock")
        return copy_token
    def add_graph_data(self, graph, x, y):
        '''
            This function adds the new x, y points to the data that should be reported to the web page
            
            ARGS: 
                graph : name of the graph you want to add to
                x : list of x data points
                y : list of y data points
        '''
        if self.__data_report_lock.acquire(timeout=1):# pylint: disable=R1732
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
            self.__data_report_lock.release()
        else : 
            raise RuntimeError("Could not acquire data report lock")
    def get_data_report(self):
        '''
            Returns a copy of the data report to the requester. 
        '''
        # pylint: disable=R1732
        if self.__data_report_lock.acquire(timeout=1):
            copy_data_report = copy.deepcopy(self.__data_report)
            self.__data_report_lock.release()
        else :
            raise RuntimeError("Could not acquire data report lock")
        return copy_data_report
    def get_graph_names(self):
        '''
            Returns a copy of the graph names to the requester. 
        '''
        # pylint: disable=R1732
        if self.__graphs_lock.acquire(timeout=1):
            copy_graph_names = copy.deepcopy(self.__graphs)
            self.__graphs_lock.release()
        else : 
            raise RuntimeError("Could not acquire graphs lock")
        return copy_graph_names
    def get_last_published_data(self):
        '''
            Returns a copy of the last data published to the requester. 
        '''
        # pylint: disable=R1732
        if self.__last_published_data_lock.acquire(timeout=1):
            copy_last_data_published = copy.deepcopy(self.__last_published_data)
            self.__last_published_data_lock.release()
        else : 
            raise RuntimeError("Could not acquire last published data lock")
        return copy_last_data_published
    def save_data(self, table, data):
        '''
            This function takes in a dict of data to save. NO byte data

            ARGS:
                table : name of the table you want to send data to 
                data : list of the data to store. NOTE: if you are saving into table with multiple values per row, then it should be a list of list, where each sub list is each value per row in order.
                    Example : table : arg1, arg2-> save_data(table = 'table', data = {'arg1' : ['hello', 'hello'], 'arg2' : ['world', 'world']}]) 
        '''
        self.__coms.send_request(self.__db_name, ['save_data_group', table, data, self.__name])
        if sys_c.read_from_file:
                self.__coms.send_request(sys_c.file_listener_name, ['mark_ended', self.__name + 'not byte'])
    def save_byte_data(self, table, data):
        '''
            This function takes in a dict of data to save, but can contain byte data

            ARGS:
                table : name of the table you want to send data to 
                data : list of the data to store. NOTE: if you are saving into table with multiple values per row, then it should be a list of list, where each sub list is each value per row in order.
                    Example : table : arg1, arg2, arg3 -> save_data(table = 'table', data = {'arg1' : ['hello', 'hello'], 'arg2' : ['world', 'world']}]) 
        '''
        self.__coms.send_request(self.__db_name, ['save_byte_data', table, data, self.__name])
        if sys_c.read_from_file:
                self.__coms.send_request(sys_c.file_listener_name, ['mark_ended', self.__name + 'byte'])
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
    def preprocess_ccsds_data(self, data):
        '''
            This function will go through the data and extract ccsds telemetry packets with valid APIDs, also detects packets with bad headers
        '''
        data = bytes().join(data) # make the list into one long sequence so it is possible to process the data.
        data = self.__extra_packet_data + data # Append extra data from the previous batch

        found_packets = []
        bad_packet_detected = False

        packet_found = False
        partial_end_packet = False

        iter_bit = 0
        while iter_bit < len(data):
            if iter_bit + sys_c.sync_word_len + sys_c.ccsds_header_len < len(data):                                                             # Check if there is enough bytes for a packet header    
                if int.from_bytes(data[iter_bit:iter_bit + sys_c.sync_word_len], 'big') == sys_c.sync_word:
                    packet_length = ((data[iter_bit + sys_c.packet_len_addr1] << 8) | data[iter_bit + sys_c.packet_len_addr2]) + 1                  # Get packet length, the packet length value is the total bytes including crc minus one, ccsds standards ¯\_(ツ)_/¯
                    if iter_bit + sys_c.sync_word_len + sys_c.ccsds_header_len + packet_length <= len(data):                                    # The whole packet is contained in this data section, append to found packets
                        packet = data[iter_bit + sys_c.sync_word_len:iter_bit + sys_c.sync_word_len + sys_c.ccsds_header_len + packet_length + 1]
                        found_packets.append(packet)
                        packet_found = True
                        iter_bit = iter_bit + sys_c.sync_word_len + sys_c.ccsds_header_len + packet_length
                    else:                                                                           # the entire packet is not in the current section
                        self.__extra_packet_data = data[iter_bit:]
                        partial_end_packet = True
                        break
                else:                    
                    if packet_found is True:                                                        # Bad packet found
                        bad_packet_detected = True
            else:                                                                                   # Not enough data for a header
                self.__extra_packet_data = data[iter_bit:]
                partial_end_packet = True
                break
            iter_bit = iter_bit + 1
        if partial_end_packet is False:
            self.__extra_packet_data = bytearray()

            
        return found_packets, bad_packet_detected
    def int_to_bytes(self, integer_value):
        '''
            converts an integer to correct size byte object 
        '''
        if integer_value == 0:
            return b'\x00'
        
        num_bytes = (integer_value.bit_length() + 7) // 8
        return integer_value.to_bytes(num_bytes, byteorder='big')
