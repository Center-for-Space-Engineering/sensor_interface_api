'''
    This class enforces the correct structure onto the sub-sensors class.  
'''

#python imports
import threading
import copy

#Custom imports
from threading_python_api.threadWrapper import threadWrapper # pylint: disable=e0401


class sensor_parent(threadWrapper):
    '''
         There are a few functions that your sensor class must implement,

         __init__(self, coms) : every python class needs this.
         get_html_page : this returns a custom html page for your sensor
         set_sensor_status : Returns where the sensor is running or not. NOTE: threadWrapper has its own set_status, used by the system, so thats why the name is longer. 
         get__sensor_status : should return Running, Error, Not running. 
         get_data : Returns the last sample the sensor returned.
         make_serial_tap : sends a request to the serial listener telling it to send data to this class.
         send_tab : this function is what the serial listener calls to send the tab to this class.
         create_tab : this function creates a tab to this class.
         get_sensor_name : This function returns the name of the sensor. The users class need to implement this.
         start_publisher : Starts a data publisher on its own thread. (For active publishers only)
         publish : publishes data
         set_publish_data : the users class calls this function, it sets data to be published
    '''
    def __init__(self, coms, config) -> None:
        ############ set up the threadWrapper stuff ############
        self.__function_dict = { 
            'create_tab' : self.create_tab,
        }
        threadWrapper.__init__(self, self.__function_dict)

        ############ Sensor information ############
        self.__coms = coms
        self.__status = "Not Running"
        self.__data_received = []
        self.__data_lock = threading.Lock()
        self.__tab_requests = []
        self.__config = config
        self.__publish_data = []
        self.__publish_data_lock = threading.Lock()
        self.__publish_data 

        ############ Set up the sensor according to the config file ############
        if self.__config['serial_port'] != 'None':
                self.make_serial_tap(self.__config['serial_port'])
        if self.__config['publisher'] == 'Yes':
            pass

    def get_html_page(self):
        '''
            Returns an file path to an html file.
        '''
        raise NotImplementedError("get_html_page Not implemented, should return file path to an html file.")
    def get__sensor_status(self):
        '''
            Returns the status of the sensor, it is up to the user to set this status, this function returns that status to the server. 
        '''
        return self.__status
    def set_sensor_status(self, status):
        '''
            User calls this function to set a status, must be Running, Error, Not running.
        '''
        if status == 'Running':
            self.__status = status
        elif status == 'Error':
            self.__status = status
        elif status == 'Not running':
            self.__status = status
        else :
            raise RuntimeError(f"{status} is not a valid status.")
    def get_data(self):
        '''
            Returns the last data point collected form the sensor. 
        '''
        raise NotImplementedError("get_data Not implemented, should return last data point collected by sensor.")
    def make_serial_tap(self, name_of_class_to_make_tap):
        '''
            This requests sends a request to the class you want and then that class creates a tap for you to listen too.
        '''
        self.__coms.send_request(name_of_class_to_make_tap, ['create_tab', self.send_tap])
    def send_tap(self, data):
        '''
            This is the function that is called by the class you asked to make a tap.
        '''
        with self.__data_lock:
            self.__data_received.append(data)
    def create_tab(self, args):
        '''
            This function creates a tab, a tab will send the data it receives from the serial line to the class that created the tab.
            ARGS:
                args[0] : tab function to call.  
        '''
        self.__tab_requests.append(args[0])
    def get_sensor_name(self):
        '''
            This function returns teh name of the sensor.
        '''
        raise NotImplementedError("get_sensor_name Not implemented, should return a string name of the sensor.")
    def start_publisher(self):
        pass #TODO: call publish on an given interval on its own thread.
    def publish(self):
        with self.__publish_data_lock:
            data_copy = self.__publish_data #I am making a copy of the data here, so the data is better protected.
        for subscriber in self.__tab_requests:
            temp  = data_copy #The reason I copy that data again is so that every subscriber gets its own copy of the data it can manipulate. 
            subscriber.send_tap(temp)
          