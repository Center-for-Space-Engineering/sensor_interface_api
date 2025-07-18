'''
    This module is for processing packets that are defined in the telemetry Dictionary 
'''
import copy
from typing import Optional
from bitarray import bitarray
from datetime import datetime, timedelta, timezone
import bisect

from sensor_interface_api.sensor_parent import sensor_parent # pylint: disable=e0401
import system_constants as sensor_config # pylint: disable=e0401
from logging_system_display_python_api.logger import loggerCustom as logger

class sobj_packet_processor(sensor_parent):
    '''
        This model is generic packet processor, one of these classes is created for each packet that is defined in the yaml. It will create 
        database tables for the granules in the packets then saves them into the database. 
    '''
    def __init__(self, coms, name, packet_config_dict:dict, apid:str) -> None:
        self.__name = name
        self.__coms = coms
        self.__packet_config = packet_config_dict
        self.__packet_nmemonic = self.__packet_config['Mnemonic']
        self.__apid = apid #this is the  sensor name 
        sensor_config.sensors_config[self.__name].update(self.__packet_config) # every processor uses the same general config
        self.__config = sensor_config.sensors_config[self.__name]
        self.__config['apid'] = self.__apid
        self.__name = self.__packet_nmemonic + self.__config['extention']
        # self.__count = 0
        self.__logger = logger(f'logs/{self.__name}.txt')

        self.__table_structure = {}

        self.__colms_list = [['temp', 0, 'uint'] for _ in range(self.__packet_config['Channels'])]
        if self.__name in sensor_config.time_correlation:
            self.__colms_list.append(['PPS_UTC', 0, 'mysql_micro_datetime', 'nullable'])
            self.__colms_list.append(['PPSS_EPOCH', 0, 'mysql_micro_datetime', 'nullable'])
            # self.__colms_list.append(['PPSS_EPOCH', 0, 'mysql_micro_datetime', 'nullable'])
            self.__colms_list.append(['PPSR_EPOCH', 0, 'mysql_milli_datetime', 'nullable'])
        self.__colms_list.append(['time_STM_CLK', 0, 'bigint'])
        self.__colms_list.append(['time_RTC', 0, 'uint'])
        self.__colms_list.append(['time_STM_CLK_UTC', 0, 'mysql_micro_datetime', "secondary_index"])
        self.__colms_list.append(['time_RTC_UTC', 0, 'mysql_milli_datetime', "secondary_index"])
        self.__colms_list.append(['received_at', 0, 'uint', "nullable"])
        self.__colms_list.append(['packet_count', 0, 'uint'])
        self.__colms_list.append(['granule_index', 0, 'uint'])
        self.__unpacking_map = [0  for _ in range(self.__packet_config['Channels'])]

        # Get length of PPSW and PPSM in bytes
        if self.__name in sensor_config.time_correlation:
            sensor_config.PPSS_len = int(self.__packet_config["granule definition"]["PPSS"]["Word Length (bits)"] / 8)
            sensor_config.PPSR_len = int(self.__packet_config["granule definition"]["PPSR"]["Word Length (bits)"] / 8)
            
            sensor_config.PPSW_len = int(self.__packet_config["granule definition"]["PPSW"]["Word Length (bits)"] / 8)
            sensor_config.PPSM_len = int(self.__packet_config["granule definition"]["PPSM"]["Word Length (bits)"] / 8)

        # Get length of PPSW and PPSM in bytes
        if self.__name in sensor_config.time_correlation:
            sensor_config.PPSS_len = int(self.__packet_config["granule definition"]["PPSS"]["Word Length (bits)"] / 8)
            sensor_config.PPSR_len = int(self.__packet_config["granule definition"]["PPSR"]["Word Length (bits)"] / 8)
            
            sensor_config.PPSW_len = int(self.__packet_config["granule definition"]["PPSW"]["Word Length (bits)"] / 8)
            sensor_config.PPSM_len = int(self.__packet_config["granule definition"]["PPSM"]["Word Length (bits)"] / 8)

        converted = True

        for key in self.__packet_config["granule definition"]:
            try : 
                if self.__packet_config["granule definition"][key]['Signed']:
                    self.__colms_list[int (self.__packet_config["granule definition"][key]['Order'] - 1)][2] = 'int'
                if int (self.__packet_config["granule definition"][key]['Order'] - 1) >= self.__packet_config['Channels']: # some timnes we have granules that have tbh parts
                    continue
                self.__colms_list[int (self.__packet_config["granule definition"][key]['Order'] - 1)][0] =  key
                self.__unpacking_map[int (self.__packet_config["granule definition"][key]['Order'] - 1)] = int(self.__packet_config["granule definition"][key]['Word Length (bits)'])
            except ValueError: # we cant convert the dictionary raise an error
                converted = False
                print(f"Warning can not convert type for apid {self.__apid}")
            except Exception as e: #pylint: disable=w0718
                converted = False
                print(f"Warning convertion faild for apid {self.__apid} Error: {e}")
        if converted is True :
            self.__table_structure[f"{self.__name}"] = self.__colms_list

        self.__buffer = {}

        #!!! check this here - is it still looking at the right columns??
        for i in range(len(self.__colms_list)-2): # ignore last two position since they are system clock and rtc values
            self.__buffer[self.__colms_list[i][0]] =  [0xFFFFFFFF for _ in range(self.__packet_config['Granule count'])]
        if self.__name in sensor_config.time_correlation:
            self.__buffer["PPS_UTC"] = [(sensor_config.PPS_UTC) for _ in range(self.__packet_config['Granule count'])]
            self.__buffer["PPSS_EPOCH"] = [(sensor_config.PPSS_epoch) for _ in range(self.__packet_config['Granule count'])]
            self.__buffer["PPSR_EPOCH"] = [(sensor_config.PPSR_epoch) for _ in range (self.__packet_config['Granule count'])]

        self.__buffer["time_STM_CLK"] = [bytearray(sensor_config.system_clock) for _ in range(self.__packet_config['Granule count'])]
        self.__buffer["time_RTC"] = [bytearray(sensor_config.real_time_clock) for _ in range(self.__packet_config['Granule count'])]

        self.__buffer["time_STM_CLK_UTC"] = [bytearray(sensor_config.system_clock_utc) for _ in range(self.__packet_config['Granule count'])]  # !!! what do I put inside the brackets?
        self.__buffer["time_RTC_UTC"] = [bytearray(sensor_config.real_time_clock_utc) for _ in range(self.__packet_config['Granule count'])]   #do I want 
        self.__buffer["received_at"] = [bytearray(sensor_config.received_at) for _ in range(self.__packet_config['Granule count'])]
        self.__buffer["packet_count"] = [bytearray(sensor_config.packet_count) for _ in range(self.__packet_config['Granule count'])]
        self.__buffer["granule_index"] = [j for j in range(self.__packet_config['Granule count'])]

        if self.__config['extention'] not in sensor_config.time_correlation_tables:
            sensor_config.time_correlation_tables[self.__config['extention']] = []

        # NOTE: if you change the table_structure, you need to clear the database/dataTypes.dtobj and database/dataTypes_backup.dtobj DO NOT delete the file, just delete everything in side the file.
        sensor_parent.__init__(self, coms=self.__coms, config= self.__config, name=self.__name, max_data_points=100, db_name = sensor_config.database_name, table_structure=self.__table_structure)
        sensor_parent.set_sensor_status(self, 'Running')
        self.__logger.send_log(f"Setup complete{self.__name}")
        # self.__logger.send_log(f"Setup complete{self.__packet_nmemonic}")
    def process_data(self, _):
        '''
            This function gets called when one of the tap request gets any data. 

            NOTE: This function always gets called no matter with tap gets data. 
        '''
        self.__logger.send_log(f"Process data for {self.__name=} | {self.__config=}")
        data = sensor_parent.get_data_received(self, self.__config['tap_request'][0])[self.__packet_nmemonic]
        buffer_dict_to_publish = {
        }
        for packet in data:
            if len(packet) > 0:
                # print(f"APID: {self.__apid}\n\tPacket {packet}")
                packet_count = ((packet[2] << 8) | (packet[3])) & 0x3FFF
                sys_clk_ms = (packet[sensor_config.ccsds_header_len+1] << 24) | (packet[sensor_config.ccsds_header_len+2] << 16) | (packet[sensor_config.ccsds_header_len+3] << 8) | (packet[sensor_config.ccsds_header_len+4])
                real_time_clk_s = (packet[sensor_config.ccsds_header_len+sensor_config.system_clock+1] << 16) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock+2] << 8) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock+3])
                cur_position_bits = int((sensor_config.ccsds_header_len+1 + sensor_config.system_clock + sensor_config.real_time_clock) * 8)
                packet_bits = bitarray()
                packet_bits.frombytes(packet)

                granule_rate_hz = self.__packet_config['G. Rate']
                granule_period_ms: float = 1 / granule_rate_hz * 1000 if granule_rate_hz != 0 else 0.0

                for j in range(self.__packet_config['Granule count']):
                    granule_delta_ms: float = j * granule_period_ms
                    granule_sys_clk_ms: int = sys_clk_ms + int(granule_delta_ms)
                    granule_real_time_clk_s: int = real_time_clk_s + int(granule_delta_ms / 1000)

                    self.__buffer['time_STM_CLK'][j] = granule_sys_clk_ms
                    self.__buffer['time_RTC'][j] = granule_real_time_clk_s

                    # Update PPS_UTC and, if necessary, PPSS and PPSR epochs
                    if self.__name in sensor_config.time_correlation:
                        # Updating PPS_UTC
                        #get PPS packet for the correct board
                        PPSS = (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+sensor_config.PPSW_len+sensor_config.PPSM_len+1] << 24) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+sensor_config.PPSW_len+sensor_config.PPSM_len+2] << 16) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+sensor_config.PPSW_len+sensor_config.PPSM_len+3] << 8) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+sensor_config.PPSW_len+sensor_config.PPSM_len+4])
                        PPSR = (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+sensor_config.PPSW_len+sensor_config.PPSM_len+sensor_config.PPSS_len+1] << 16) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+sensor_config.PPSW_len+sensor_config.PPSM_len+sensor_config.PPSS_len+2] << 8) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+sensor_config.PPSW_len+sensor_config.PPSM_len+sensor_config.PPSS_len+3])

                        gps_week = (packet[sensor_config.ccsds_header_len + sensor_config.system_clock + sensor_config.real_time_clock+ 1] << 8) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+2]) # Value is dubious
                        gps_milli = (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+sensor_config.PPSW_len+1] << 24) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+sensor_config.PPSW_len+2] << 16) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+sensor_config.PPSW_len+3] << 8) | (packet[sensor_config.ccsds_header_len+sensor_config.system_clock + sensor_config.real_time_clock+sensor_config.PPSW_len+4])
            
                        if gps_week != 0 and gps_milli != 0:
                            leap_seconds = 18

                            newPPS_UTC = (datetime(1980, 1, 6, 0 , 0) + timedelta(weeks=gps_week) + timedelta(milliseconds=gps_milli) - timedelta(seconds=leap_seconds))
                            PPSS_epoch = newPPS_UTC- timedelta(milliseconds=PPSS)
                            PPSR_epoch = newPPS_UTC- timedelta(seconds=PPSR)

                            # sensor_config.PPS_UTC = newPPS_UTC
                            # sensor_config.PPSS_epoch = PPSS_epoch
                            # sensor_config.PPSR_epoch = PPSR_epoch

                            self.__buffer['PPS_UTC'][j] = newPPS_UTC.strftime('%Y-%m-%d %H:%M:%-S.%f')
                            self.__buffer['PPSS_EPOCH'][j] = PPSS_epoch.strftime('%Y-%m-%d %H:%M:%-S.%f')
                            self.__buffer['PPSR_EPOCH'][j] = PPSR_epoch.strftime('%Y-%m-%d %H:%M:%-S.%f')[:-3]

                            time_correlation_table_entry = {
                                'PPSR' : PPSR,
                                'PPSS' : PPSS,
                                'PPS_UTC' : newPPS_UTC,
                                # 'PPSS_EPOCH' : PPSS_epoch,
                                # 'PPSR_EPOCH' : PPSR_epoch,
                            }

                            bisect.insort(sensor_config.time_correlation_tables[self.__config['extention']], time_correlation_table_entry, key=lambda e: (e['PPSR'], e['PPSS']))
                        else:
                            self.__buffer['PPS_UTC'][j]    = None # Swenson recommended None / null so the field comes in empty into the database
                            self.__buffer['PPSS_EPOCH'][j] = None # Swenson recommended None / null so the field comes in empty into the database
                            self.__buffer['PPSR_EPOCH'][j] = None # Swenson recommended None / null so the field comes in empty into the database

                            # sensor_config.PPS_UTC = None

                    # Update UTC times        
                    # self.__buffer['time_STM_CLK_UTC'][j] = self.to_UTC(granule_sys_clk_ms, is_RTC=False).strftime('%Y-%m-%d %H:%M:%-S.%f')
                    # self.__buffer['time_RTC_UTC'][j] = self.to_UTC(granule_real_time_clk_s, is_RTC=True).strftime('%Y-%m-%d %H:%M:%-S.%f')[:-3]
                    # granule_system_clk_utc, granule_real_time_clk_utc = self.utcs_from_clks(granule_sys_clk_ms, granule_real_time_clk_s)
                    graunule_system_clk_utc, graunule_real_time_clk_utc = self.utcs_from_clks(granule_sys_clk_ms, granule_real_time_clk_s)
                    self.__buffer['time_STM_CLK_UTC'][j] = graunule_system_clk_utc.strftime('%Y-%m-%d %H:%M:%-S.%f')
                    self.__buffer['time_RTC_UTC'][j] = graunule_real_time_clk_utc.strftime('%Y-%m-%d %H:%M:%-S.%f')[:-3]
                    self.__buffer['received_at'][j] = datetime.now(timezone.utc).timestamp()

                    # self.__logger.send_log(f"Clocks updated to UTC at time {datetime.fromtimestamp(self.__buffer['received_at'][j])}")
                    self.__buffer['packet_count'][j] = packet_count

                    for i in range(len(self.__unpacking_map)): # pylint: disable=C0200
                        # print(f"APID: {self.__apid}\tPacket length: {len(packet)}\tPacket length bits: {len(packet_bits)}\tcolmslist curr: {self.__colms_list[i]}\t cur_position: {cur_position_bits}\tcurpostiion+unpacking: {cur_position_bits+self.__unpacking_map[i]}")
                        temp = packet_bits[cur_position_bits:cur_position_bits+self.__unpacking_map[i]]
                        if len(temp) > 32: #all of these need to be an unit 32 or smaller. 
                            self.__buffer[self.__colms_list[i][0]][j] = 0
                            # self.__logger.send_log(f'Unpacking packet {self.__packet_nmemonic} got too large of bin size at {self.__colms_list[i][0]}, must be 32 bits or smaller but has size {self.__unpacking_map[i]}.')
                        else :
                            if self.__colms_list[i][2] == 'int' and temp[0] == 1:
                                while len(temp) < 32:
                                    temp.insert(0,1)
                                self.__buffer[self.__colms_list[i][0]][j] = int.from_bytes(temp, signed = True)
                            else:
                                self.__buffer[self.__colms_list[i][0]][j] = self.bitarray_to_int(temp) | 0x00000000
                        cur_position_bits += self.__unpacking_map[i]

                # save to db and publish 
                buf_copy = copy.deepcopy(self.__buffer)
                sensor_parent.save_data(self, table=f"{self.__name}", data=buf_copy)

                #lets save the data into a dictionary
                all_keys_set = set(self.__buffer.keys()).union(buffer_dict_to_publish.keys())

                for key in all_keys_set:
                    buffer_dict_to_publish[key] = self.__buffer.get(key, []) + buffer_dict_to_publish.get(key, [])

                # flush the buffer
                for key in self.__buffer: # pylint: disable=C0206
                    if not key == 'granule_index':
                        for byte_storage in range(len(self.__buffer[key])):
                            self.__buffer[key][byte_storage] = 0xFFFFFFFF
        sensor_parent.set_publish_data(self, data=buffer_dict_to_publish)
        sensor_parent.publish(self)
        
    def bitarray_to_int(self, bit_array):
        '''
            converts bitarray into and int
        '''
        result = 0
        for bit in bit_array:
            result = (result << 1) | bit
        return result

    # def to_UTC(self, gps_clock, is_RTC):
    #     '''
    #         converts given time into utc time

    #         returned obj is datetime obj
    #     '''
    #     if is_RTC:
    #         new_datetime = (sensor_config.PPSR_epoch) + timedelta(seconds=gps_clock)
    #         return  new_datetime
    #     else:
    #         new_datetime = (sensor_config.PPSS_epoch) + timedelta(milliseconds=gps_clock)
    #         return new_datetime
        
    def utcs_from_clks(self, system_clk_ms: int, real_time_clk_s: int) -> tuple[datetime, datetime]:
        '''
            Returns the absolute UTC datetime given the system and real-time clocks.
            This is accomplished by first looking up the most recent time correlation entry before or at the time of these clock values (ordered by real-time and then system clock values).
            The entry contains a synchronized UTC datetime, originally calculated from PPS message values.
            Finally, an appropriate delta is added to yield the desired UTC datetime that corresponds to the given clock values.
        '''
        # https://docs.python.org/3/library/bisect.html#searching-sorted-lists
        search_key = (real_time_clk_s, system_clk_ms)
        i = bisect.bisect_right( \
            sensor_config.time_correlation_tables[self.__config['extention']], \
            search_key, \
            key=lambda e: (e['PPSR'], e['PPSS']) \
        ) - 1
        if i not in range(len(sensor_config.time_correlation_tables[self.__config['extention']])):
            return datetime.fromtimestamp(0), datetime.fromtimestamp(0)
            # return None

        time_correlation_table_entry = sensor_config.time_correlation_tables[self.__config['extention']][i]
        baseUTCdatetime: datetime = time_correlation_table_entry['PPS_UTC']

        system_clk_delta_ms = system_clk_ms - time_correlation_table_entry['PPSS']
        real_time_clk_delta_s = real_time_clk_s - time_correlation_table_entry['PPSR']

        system_clk_utc = baseUTCdatetime + timedelta(milliseconds=system_clk_delta_ms)
        real_time_clk_utc = baseUTCdatetime + timedelta(seconds=real_time_clk_delta_s)

        return system_clk_utc, real_time_clk_utc

        # # If the system clock delta doesn't make sense or conflicts with the real-time clock delta, prefer the latter.
        # if system_clk_delta_ms < 0 or system_clk_delta_ms > real_time_clk_s * 1000:
        #     return baseUTCdatetime + timedelta(seconds=real_time_clk_delta_s)
        
        # # Otherwise, use the system clock delta for more accuracy
        # return baseUTCdatetime + timedelta(milliseconds=system_clk_delta_ms)
