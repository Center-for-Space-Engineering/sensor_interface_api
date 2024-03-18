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
        html = self.__soup.new_tag('html')
        head = self.__soup.new_tag('head')
        css_link = self.__soup.new_tag('link', rel='stylesheet', href='styles.css')
        head.append(css_link)

        # Create the head of the html document. 
        title_tag = self.__soup.new_tag('title')
        title_tag.string = f'https://usu.cse.spacecraftemulator.com/{self.__sensor_name}'
        head.append(title_tag)
        script1_tag = self.__soup.new_tag('script', src='page_manigure.js')
        head.append(script1_tag)
        script2_tag = self.__soup.new_tag('script', src='https://code.jquery.com/jquery-3.6.4.min.js')
        head.append(script2_tag)
        html.append(head)

        body = self.__soup.new_tag('body')

        #Create the title for the page
        outer_div = self.__soup.new_tag('div', **{'class' :'horizontal-container'})
        h1_tag = self.__soup.new_tag('h1', **{'class' :'white-text'})
        h1_tag.string = f'CSE Space Craft Emulator: Sensor interface {self.__sensor_name}'
        outer_div.append(h1_tag)
        body.append(outer_div)

        #Create tabs to go back to the main pages
        div_element = self.__soup.new_tag('div', **{'class' : 'tab-container'})
        tab1 = self.__soup.new_tag('div', **{'class' : 'tab', 'onclick' : 'open_tab(\'Status Report\')'})
        tab1.string = 'Status Report'
        div_element.append(tab1)

        tab2 = self.__soup.new_tag('div', **{'class' : 'tab', 'onclick' : 'open_tab(\'Data Stream\')'})
        tab2.string = 'Data Stream'
        div_element.append(tab2)

        tab3 = self.__soup.new_tag('div', **{'class' : 'tab', 'onclick' : 'open_tab(\'Sensor\')'})
        tab3.string = 'Sensor'
        div_element.append(tab3)

        tab4 = self.__soup.new_tag('div', **{'class' : 'tab', 'onclick' : 'open_tab(\'Command\')'})
        tab4.string = 'Command'
        div_element.append(tab4)

        body.append(div_element)

        #create the sensor report 
        sensor_report_tag = self.__soup.new_tag('div', **{'class' :'horizontal-container'})
        h1_title = self.__soup.new_tag('h1', **{'class' :'green-text'})
        h1_title.string = f'Report from {self.__sensor_name}:'
        sensor_report_tag.append(h1_title)
        body.append(sensor_report_tag)

        sensor_config_tag = (self.__soup.new_tag('div', **{'class' :'horizontal-container'}))
        h2_report_title = self.__soup.new_tag('h2', **{'class' :'orange-text'})
        h2_report_title.string = 'Configurations: '
        sensor_config_tag.append(h2_report_title)
        body.append(sensor_config_tag)

        #get all the configurations

        config_table = self.__soup.new_tag('table')
        config_table_thead = self.__soup.new_tag('thead')
        tr = self.__soup.new_tag('tr', **{'class' :'orange-text'})

        th_option =  self.__soup.new_tag('th')
        th_option.string = 'Configuration option'
        tr.append(th_option)

        th_status =  self.__soup.new_tag('th')
        th_status.string = 'Configuration status'
        tr.append(th_status)
        
        config_table_thead.append(tr)

        tbody = th_option =  self.__soup.new_tag('tbody')

        for key  in self.__config:
            tr_sub = self.__soup.new_tag('tr')

            td_option = self.__soup.new_tag('td', **{'class' :'nice_teal'})
            td_option.string = f'{key}'
            tr_sub.append(td_option)

            td_status = self.__soup.new_tag('td', **{'class' :'nice_teal'})
            td_status.string = f'{self.__config[key]}'
            tr_sub.append(td_status)


            tbody.append(tr_sub)
        config_table_thead.append(tbody)
        config_table.append(config_table_thead)
        body.append(config_table)

        if self.__config['publisher'] == 'yes':
            publisher_head = self.__soup.new_tag('h2')
            publisher_head.string = 'Last published data: '
            body.append(publisher_head)

        # Append tags to build HTML structure
        html.append(body)
        self.__soup.append(html)


    
    def generate_html_file(self, file_path):
        '''
        Generate the HTML file.

        Args:
            file_path : str : the file path where the HTML file will be saved.
        '''
        # Write HTML content to the file
        with open(file_path, "w") as file:
            file.write(self.__soup.prettify())

        return file_path

if __name__ == '__main__':
    config = {
        'publisher': 'yes',
        'Hello world' : 'NO way bio'
    }
    generator = sensor_html_page_generator('test sensor', config)
    html_file_path = generator.generate_html_file('temperature_sensor.html')