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
    def __init__(self, sensor_name, config, graphs: bool = False) -> None: # pylint: disable=r0915
        self.__sensor_name = sensor_name
        self.__config = config

        ###################### Create page head ################################
        # Create a new BeautifulSoup object
        self.__soup = bs(features='html.parser')

        #build page
        html = self.__soup.new_tag('html')
        head = self.__soup.new_tag('head')
        
        css_link = self.__soup.new_tag('link', rel='stylesheet', href="{{ url_for('static', filename='styles.css') }}")
        head.append(css_link)

        script_tag_for_graphs = self.__soup.new_tag("script", **{'src' : "https://cdn.jsdelivr.net/npm/chart.js"})
        head.append(script_tag_for_graphs)


        # Create the head of the html document. 
        title_tag = self.__soup.new_tag('title')
        title_tag.string = f'https://usu.cse.spacecraftemulator.com/{self.__sensor_name}'
        head.append(title_tag)
        script1_tag = self.__soup.new_tag('script', src='page_manigure.js')
        head.append(script1_tag)
        script2_tag = self.__soup.new_tag('script', src='https://code.jquery.com/jquery-3.6.4.min.js')
        head.append(script2_tag)
        html.append(head)
        ##########################################################################

        ###################### Create body title ################################
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

        tab5 = self.__soup.new_tag('div', **{'class' : 'tab', 'onclick' : 'open_tab(\'unit_testing\')'})
        tab5.string = 'Unit test'
        div_element.append(tab5)

        tab6 = self.__soup.new_tag('div', attrs={'class': 'tab', 'onclick': "open_tab('failed_test')"})
        tab6.string = 'failed_test'
        div_element.append(tab6)

        body.append(div_element)
        ##########################################################################

        ###################### Create configuration table ################################
        #create the sensor report 
        sensor_report_tag = self.__soup.new_tag('div', **{'class' :'horizontal-container'})
        h1_title = self.__soup.new_tag('h1', **{'class' :'green-text'})
        h1_title.string = f'Report from {self.__sensor_name}:'
        sensor_report_tag.append(h1_title)
        body.append(sensor_report_tag)

        sensor_config_tag = self.__soup.new_tag('div', **{'class' :'horizontal-container'})
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
        ##########################################################################

        ###################### Create publishing report ################################
        if self.__config['publisher'] == 'yes':
            publisher_head = self.__soup.new_tag('h2', **{'class' : 'green-text'})
            publisher_head.string = 'Last published data: '
            body.append(publisher_head)

            time_pub = self.__soup.new_tag('h3', **{'id' : 'time_pub_tag','class' : 'orange-text'})
            time_pub.string = 'NA'
            body.append(time_pub)

            data_pub = self.__soup.new_tag('h3', **{'id' : 'data_pub_tag','class' : 'orange-text'})
            data_pub.string = 'NA'
            body.append(data_pub)

            script_published = self.__soup.new_tag("script")
            javascript_code = f"""
            setInterval(function() {{
                    updateDataPublish("{self.__sensor_name}");
                }}, 1000);
            """
            
            script_published.string = javascript_code
            body.append(script_published)
        ##########################################################################

        ###################### Create graphs #####################################
        if graphs: 
            #create title
            h1_tag = self.__soup.new_tag('h1', **{'class' : 'green-text'})
            h1_tag.string = 'Graphing report:'
            body.append(h1_tag)

            # Create a new div tag
            new_div_tag = self.__soup.new_tag("div")

            # Set attributes for the div tag
            new_div_tag['id'] = 'graphs'
            new_div_tag['style'] = 'display: grid; grid-template-columns: auto auto;'

            body.append(new_div_tag)

            script_graphs = self.__soup.new_tag("script")
            javascript_code = f"""
            makeGraphsSensors("{self.__sensor_name}");
            setInterval(function() {{
                    updateGraphsSensor("{self.__sensor_name}");
                }}, 1000);
            """
            
            script_graphs.string = javascript_code
            body.append(script_graphs)
        ##########################################################################

        # Append tags to build HTML structure
        html.append(body)
        self.__soup.append(html)

        # Good debugging tool if you need it 
        # h1_tag = self.__soup.new_tag('h1', **{'id' : "debug_box", 'class' : 'green-text'})
        # body.append(h1_tag)


    
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
