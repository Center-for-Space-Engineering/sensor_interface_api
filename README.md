
# Sensor interface overview
The Sensors are a little like the server where they are meant to have things adding dynamical to them. However unlike the server, the sensors are made to listen and publish data to each other. Their are two main goals with the sensors:\
1. Create processing chains for our data
2. Create a structure that unit test can be applied to. 

Unlike other README's I am not going to go through ever function and what it does, rather I am going to give an over view of each class and what role it plays. I also have provided extensive documentation on how to build with this repo in the `HOWTO.md`, or the `HOWTO.md` in `ground_station` repo. 

## `collect_sensors`
This class will search the `sensor_interface_api` folder and find any file beginning with `sobj_` it then imports that python class. This is how the user can add there own `sobj_` files to create new sensors. 

## `sensor_parent`
This class is meant to be inherited by the sensors that the users make. It has a ton of features built into it. Everything from automatic graphing, to html page generation, and publishing and subscribing models. 

Functions:
1. `__init__` : every python class needs this.
2. `get_html_page` : this returns a custom html page for your sensor
3. `set_sensor_status` : Returns where the sensor is running or not. NOTE: threadWrapper has its own set_status, used by the system, so thats why the name is longer. 
4. `get_sensor_status` : should return Running, Error, Not running. 
5. `get_data_received` : Returns the last sample the sensor returned.
6. `get_taps` : Returns a list of taps that the user has requested for this class. 
7. `process_data` : This is the function that is called when the data_received event is called. 
8. `make_data_tap` : sends a request to the serial listener telling it to send data to this class.
9. `send_tab` : this function is what the serial listener calls to send the tab to this class.
10. `create_tab` : this function creates a tab to this class.
11. `get_sensor_name` : This function returns the name of the sensor. The users class need to implement this.
12. `start_publisher` : Starts a data publisher on its own thread. (For active publishers only)
13. `publish` : publishes data
14. `set_publish_data` : the users class calls this function, it sets data to be published.
15. `has_been_published` : Returns a bool that is true if the data has been publish and false otherwise. 
16. `event_listener` : this function waits for events to happen then it calls the function corresponding to that event
17. `publish_data` : Notifies the system that data is published of the given data type. 
18. `add_graph_data` : adds an x and y point
19. `get_data_report` : returns the data report to the webpage
20. `get_graph_names` : returns the list of graphs for this sensor
21. `get_last_published_data` : returns the last thing published and the time it was published at.
22. `preprocess_data` : this function may work for you if your data comes in in chucks, and needs to be put back together. See the function docer string. 
23. `set_thread_status` : set the status for your processing threads. 
24. `get_data_name` : return data name
25. `save_byte_data` : saves byte data into the database.
26. `save_data` : saves data into the database. 

## `sensor_html_page_generator`
This class is how our pages can automatically generate html pages with graphs and such for our web server. It is not complicated there is just a lot going on.  

## Compiling README.md with pandocs
    To compile .md to a pdf: pandoc -s README.md -V geometry:margin=1in -o README.pdf
    To compile to a stand alone html doc: pandoc  --metadata title="README" -s --self-contained README.md -o README.html

## Linting
This is the method that is used to check the code and make sure it fits coding stander and best practice. The package is called `pylint` and can be installed with \
``` python
    pip install pylint  
```
or 
```python
    pip3 install pylint 
```
depending on context. The command to run `pylint` is:
```python
    python3 -m pylint --jobs 0 --rcfile .pylintrc <name of python file or folder>
```