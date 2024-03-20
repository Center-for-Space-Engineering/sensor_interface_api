'''
    This class enforces the correct structure onto the sub-sensors class.  
'''

#python imports
import threading
import copy
import time
import re

#Custom imports
from threading_python_api.threadWrapper import threadWrapper # pylint: disable=e0401
from sensor_interface_api.sensor_html_page_generator import sensor_html_page_generator # pylint: disable=e0401

class sensor_parent(threadWrapper, sensor_html_page_generator):
    '''
         There are a few functions that your sensor class must implement,

         __init__(self, coms) : every python class needs this.
         get_html_page : this returns a custom html page for your sensor
         set_sensor_status : Returns where the sensor is running or not. NOTE: threadWrapper has its own set_status, used by the system, so thats why the name is longer. 
         get__sensor_status : should return Running, Error, Not running. 
         get_data : Returns the last sample the sensor returned.
         get_taps : Returns a list of taps that the user has requested for this class. 
         process_data : This is the function that is called when the data_received event is called. 
         make_data_tap : sends a request to the serial listener telling it to send data to this class.
         send_tab : this function is what the serial listener calls to send the tab to this class.
         create_tab : this function creates a tab to this class.
         get_sensor_name : This function returns the name of the sensor. The users class need to implement this.
         start_publisher : Starts a data publisher on its own thread. (For active publishers only)
         publish : publishes data
         set_publish_data : the users class calls this function, it sets data to be published
         event_listener : this function waits for events to happen then it calls the function corresponding to that event
         publish_data : Notifies the system that data is published of the given data type. 
 
         ARGS:
            coms : the message handler, that almost every class uses in this system.
            config : the configuration created by the user. 
            name : name of this sensor
            event_dict : any events the user wishes to add. 
    '''
    def __init__(self, coms, config:dict, name:str, events_dict:dict = {}) -> None:
        ###################### Sensor information ################################
        self.__coms = coms
        self.__status_lock = threading.Lock()
        self.__status = "Not Running"
        self.__data_received = []
        self.__data_lock = threading.Lock()
        self.__tab_requests = []
        self.__config = config
        self.__publish_data = []
        self.__publish_data_lock = threading.Lock()
        self.__publish_data
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
        ##########################################################################

        ############ Set up the sensor according to the config file ############
        if self.__config['tap_request'] is not None:
                for request in self.__config['tap_request']:
                    self.make_data_tap(request)
                self.__taps = self.__config['tap_request']
        else :
            self.__taps = ['None']
        if self.__config['publisher'] == 'yes':
            if self.__config['passive_active'] == 'passive':
                self.__events['data_received_event'] = self.process_data
            else :
                self.__active = True
                self.start_publisher()
        ##########################################################################
        ##################### set up the threadWrapper stuff #####################
        self.__function_dict = { 
            'create_tab' : self.create_tab,
        }
        threadWrapper.__init__(self, self.__function_dict, self.__events)
        ##########################################################################
        ################## set up the html page generation stuff #################
        sensor_html_page_generator.__init__(self, self.__name, self.__config)
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
    def process_data(self):
        '''
            This function gets called when the data_received event happens. NOTE: It should be short, because it holds up this whole
            thread. If you have large amounts of processing have this function create another thread and process the data on that. 
        '''
        raise NotImplementedError("process_data Not implemented, should process that last data received (data is stored in the __data_received variable).")

    def get_data(self):
        '''
            Returns the last data point collected form the sensor. 
        '''
        raise NotImplementedError("get_data Not implemented, should return last data point collected by sensor.")
    def make_data_tap(self, name_of_class_to_make_tap):
        '''
            This requests sends a request to the class you want and then that class creates a tap for you to listen too.
        '''
        with self.__name_lock:
            temp_name_token = self.__name
        self.__coms.send_request(name_of_class_to_make_tap, ['create_tap', self.send_tap, temp_name_token])
    def send_tap(self, data):
        '''
            This is the function that is called by the class you asked to make a tap.
        '''
        with self.__data_lock:
            self.__data_received.append(data)
        threadWrapper.set_event(self, 'data_received_event')
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
        self.__tab_requests.append(args[0])
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
                for subscriber in self.__tab_requests:
                    temp  = data_copy #The reason I copy that data again is so that every subscriber gets its own copy of the data it can manipulate. 
                    subscriber.send_tap(temp)
                time.sleep(interval_pub)
        else :
            with self.__publish_data_lock:
                data_copy = self.__publish_data #I am making a copy of the data here, so the data is better protected.
            for subscriber in self.__tab_requests:
                temp  = data_copy #The reason I copy that data again is so that every subscriber gets its own copy of the data it can manipulate. 
                subscriber.send_tap(temp)
