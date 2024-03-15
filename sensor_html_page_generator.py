'''
    This modules takes in information from the users config parameter in the main file and
    then generates a sensor html page. 
'''
from bs4 import BeautifulSoup as bs
class sensor_html_page_generator():
    '''
        This will generate an html page and then returns its file path when requested.

        ARGS:
            sensor_name : the name of the sensor, it will play into the name of the html file generated.
            config : this is the users presets they made. 
    '''
    def __init__(self, sensor_name, config) -> None:
        self.__sensor_name = sensor_name
        self.__config = config

        # Create a new BeautifulSoup object
        self.__soup = bs(features='html.parser')

        #build page
        self.__html = self.__soup.new_tag('html')
        self.__head = self.__soup.new_tag('head')
        self.__title = self.__soup.new_tag('title')
        self.__title.string = f'CSE Space Craft Emulator: Sensor interface {self.__sensor_name}'
        self.__body = self.__soup.new_tag('body')
        self.__h1 = self.__soup.new_tag('h1')
        self.__h1.string = 'Shopping List'
        self.__ul = self.__soup.new_tag('ul')

        if self.__config['publisher'] == 'yes':
            publisher_head = self.__soup.new_tag('h2')
            publisher_head.string = 'Last published data: '
            self.__body.append()