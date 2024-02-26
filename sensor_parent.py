'''
    This class enforces the correct structure onto the sub-sensors class.  
'''

#python imports
import threading

class sensor_parent():
    '''
         There are a few functions that your sensor class must implement,

         __init__(self, coms) : every python class needs this.
         get_html_page : this returns a custom html page for your sensor
         get_status : should return Running, Error, Not running. 
         get_data : Returns the last sample the sensor returned.
         make_serial_tap : sends a request to the serial listener telling it to send data to this class.
         send_tab : this function is what the serial listener calls to send the tab to this class.
         create_tab : this function creates a tab to this class.

    '''
    def __init__(self, coms) -> None:
        self.__coms = coms
        self.__status = "Not Running"
        self.__data_received = []
        self.__data_lock = threading.Lock()
        self.__tab_requests = []
    def get_html_page(self):
        '''
            Returns an file path to an html file.
        '''
        raise NotImplementedError("get_html_page Not implemented, should return file path to an html file.")
    def get_status(self):
        '''
            Returns the status of the sensor, it is up to the user to set this status, this function returns that status to the server. 
        '''
        return self.__status
    def set_status(self, status):
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
          