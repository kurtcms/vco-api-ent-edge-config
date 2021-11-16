import time
import datetime
import json
import numpy as np
import pandas as pd
import smtplib, ssl
from vco_api_client import vco_api_client
from sys import path
from os import mkdir, environ
from dotenv import load_dotenv, find_dotenv
from textwrap import dedent

class vco_api_main():
    INTERVAL_SECS = 300
    '''
    300 seconds i.e. 5 minutes interval as default for API calls
    '''

    INTERVAL_SECS_METRICS = 3600
    '''
    3600 seconds i.e. 60 minutes interval as default for the
    aggregate Edge transport metrics call
    '''

    VCO_THRESHOLD = 600
    '''
    600 seconds i.e. 10 minutes for data is often not reflected in API
    output for up 10 minutes as per the API documentation
    https://code.vmware.com/apis/1045/velocloud-sdwan-vco-api
    '''

    def __init__(self):
        if load_dotenv(find_dotenv()) == False:
            '''
            Raise a system exit on error reading environment variables
            with python-dotenv
            '''
            raise SystemExit('Problem locating the .env file')

        '''
        Read the environment variables for the parameters
        needed for the VCO client authentication
        '''
        try:
            hostname = environ['VCO_HOSTNAME']
        except KeyError:
            # Raise a system exit on error reading the hostname
            raise SystemExit('VCO_HOSTNAME is not found in the .env')

        try:
            token = environ['VCO_TOKEN']
        except KeyError:
            token = None
            try:
                # Read username and password if a token is not found
                username = environ['VCO_USERNAME']
                password = environ['VCO_PASSWORD']
            except KeyError:
                # Raise a system exit on error reading the parameters
                raise SystemExit(dedent('''\
                Neither the VCO_TOKEN nor the VCO_USERNAME and
                VCO_PASSWORD is found in the .env
                ''').replace('\n', ' '))

        '''
        Initiate the VCO client object with the API token or
        authenticate it with the username and password if a token
        is not found
        '''
        self.client = vco_client(hostname)
        if token:
            self.client.token_auth(token)
        else:
            self.client.cookies_auth(username, password, is_operator=False)

        '''
        Read and initiate the time now
        '''
        self.time_now = self.__update_time()

        '''
        Read and set the enterpriseName and enterpriseId from
        a call to the monitoring/getAggregateEdgeLinkMetrics
        '''
        self.metrics = self._get_aggre_metrics(self.INTERVAL_SECS_METRICS)
        self.ent_name = self._get_ent_name(self.metrics)
        self.ent_id = self._get_ent_id(self.metrics)

        '''
        Read and set the edgeId from a call to the
        enterprise/getEnterpriseEdges
        '''
        self.ent_edge = self._get_ent_edge()
        self.edge_id = self._get_edge_id(self.ent_edge)

    def __update_time(self):
        '''
        Return the time now minus the VCO API delay
        threshold in epoch
        '''
        time_now = int(time.time() - self.VCO_THRESHOLD)
        return time_now

    def __name_sanitised(self, name):
        '''
        Replace non-alphanumeric character in string with a dash
        for sanitisation
        '''
        return ''.join([c if c.isalnum() else '-' for c in name])

    def _get_time_e(self, interval_sec = None):
        '''
        Read the time now minus the VCO API delay threshold and
        set the start and end time accirdingly in epoch and in
        milliseconds with a default 5-minute interval unless
        otherwise specified
        '''
        if interval_sec is None:
            interval_sec = self.INTERVAL_SECS
        self.time_end_e = self.time_now * 1000
        self.time_start_e = (self.time_now - int(interval_sec)) * 1000

    def _get_time(self, interval_sec = None):
        '''
        Read the time now minus the VCO API delay threshold and
        set the start and end time in UTC and in ISO 8601 format
        with a default 5-minute interval unless otherwise specified
        '''
        if interval_sec is None:
            interval_sec = self.INTERVAL_SECS
        self.time_end = datetime.datetime.utcfromtimestamp(
                        self.time_now).isoformat()
        self.time_start = datetime.datetime.utcfromtimestamp(
                            self.time_now - int(interval_sec)).isoformat()

    def _get_aggre_metrics(self, interval_sec):
        '''
        Poll and return the aggregate Edge transport metrics
        of all the Edges given a specified time interval
        '''
        self._get_time_e(interval_sec)
        metrics = self.client.call_api(
                    'monitoring/getAggregateEdgeLinkMetrics', {
                        'interval': {
                            'start': self.time_start_e,
                            'end': self.time_end_e
                        }
        })
        return metrics

    def _get_ent_id(self, metric):
        '''
        Return the enterpriseId
        '''
        try:
            return metric[0]['link']['enterpriseId']
        except KeyError:
            # Raise a system exit on error reading the enterpriseId
            raise SystemExit('enterpriseID is not found in metric')
        except IndexError:
            # Raise a system exit on error locating the enterpriseId
            raise SystemExit('enterpriseID cannot be located in metric')
        except TypeError:
            # Raise a system exit on error accessing metric
            raise SystemExit('Problem accessing metric')

    def _get_ent_edge(self):
        '''
        Poll and return details of all the Edges given the enterpriseId
        '''
        ent_edge = self.client.call_api(
                    'enterprise/getEnterpriseEdges', {
                        'enterpriseId': self.ent_id,
                    })
        return ent_edge

    def _get_edge_id(self, ent_edge):
        '''
        Return a list of the edgeId for all the Edges given
        '''
        edge_list = []
        for each in ent_edge:
            try:
                if isinstance(each['id'], int):
                    edge_list.append(each['id'])
            except KeyError:
                pass

        if edge_list:
            return list(set(edge_list))
        else:
            # Raise a system exit on error reading the edgeID
            raise SystemExit('No edgeID is found in ent_edge')

    def _get_ent_name(self, metric):
        '''
        Return the enterpriseName
        '''
        try:
            return metric[0]['link']['enterpriseName']
        except KeyError:
            # Raise a system exit on error reading the enterpriseName
            raise SystemExit('enterpriseName is not found in metric')
        except IndexError:
            # Raise a system exit on error locating the enterpriseName
            raise SystemExit('enterpriseName cannot be located in metric')
        except TypeError:
            # Raise a system exit on error accessing metric
            raise SystemExit('Problem accessing metric')

    def _get_edge_name(self, edge_id, ent_edge):
        '''
        Return the Edge name given its ID
        '''
        try:
            for edge in ent_edge:
                if edge['id'] == edge_id:
                    return edge['name']
        except KeyError:
            pass
        # Return the Edge ID instead if the name is not found
        return edge_id

    def _get_wan_name(self, link_id, metrics):
        '''
        Return the WAN name given its ID
        '''
        try:
            for link in metrics:
                if link['linkLogicalId'] == link_id:
                    return link['link']['displayName']
        except KeyError:
            pass
        # Return the link ID instead if the name is not found
        return link_id

    def _get_wan_quality_name(self, quality):
        '''
        Return a human readable WAN qaulity name given its key
        '''
        wan_qaulity_key_value = {
            'latencyMsTx': 'Latency (upload, ms)',
            'latencyMsRx': 'Latency (download, ms)',
            'jitterMsTx': 'Jitter (upload, ms)',
            'jitterMsRx': 'Jitter (download, ms)',
            'lossPctTx': 'Packet Loss (upload, %)',
            'lossPctRx': 'Packet Loss (download, %)'
        }
        for key in wan_qaulity_key_value:
            if key == quality:
                return wan_qaulity_key_value[key]
        # Return the WAN qaulity key instead if the name is not found
        return quality

    def __get_wan_quality(self, edge_id, min_per_sample,
    interval_sec = None, time_offset = None, indiv_score = True):
        '''
        Return the quality of the WAN associated with
        an Edge given its ID and a specified time interval
        '''
        self._get_time_e(interval_sec)
        wan_quality = self.client.call_api(
            'linkQualityEvent/getLinkQualityEvents', {
            'enterpriseId': self.ent_id,
            'edgeId': edge_id,
            'interval': {
                'start': self.time_start_e if time_offset == None
                    else self.time_start_e - time_offset,
                'end': self.time_end_e if time_offset == None
                    else self.time_end_e - time_offset,
            },
            'minutesPerSample': min_per_sample,
            'individualScores': indiv_score
        })
        return wan_quality

    def _get_wan_quality_dataframe(self, min_per_sample,
    interval_sec = None, time_offset = None):
        '''
        Return the quality of the WAN associated with
        all the Edges given a specified time interval
        as pandas DataFrames
        '''
        wan_quality_dataframe = {}
        for edge in self.edge_id:
            wan_quality = self.__get_wan_quality(edge, min_per_sample,
                interval_sec, time_offset)
            wan = {}
            for wan_id in wan_quality:
                if not wan_id == 'overallLinkQuality':
                    dict = []
                    try:
                        for timeseries in wan_quality[wan_id]['timeseries']:
                            try:
                                timeseries['timestamp']
                                timeseries['metadata']['detail']
                            except KeyError:
                                pass
                            else:
                                sample = {'timestamp': timeseries['timestamp']}
                                sample.update(timeseries['metadata']['detail'])
                            if sample: dict.append(sample)
                    except KeyError:
                        pass
                    if dict:
                        wan[wan_id] = pd.DataFrame.from_dict(dict)
            if wan:
                wan_quality_dataframe[edge] = wan

        if wan_quality_dataframe:
            return wan_quality_dataframe
        else:
            # Raise a system exit on error reading the WAN quality
            raise SystemExit('Of all the Edges no WAN quality is found')

    def _email_wan_anomaly(self, email_msg):
        '''
        Send an email notification given a email subject and body
        '''
        ssl_context = ssl.create_default_context()

        '''
        Read the environment variables for the parameters
        needed for the VCO client authentication
        '''
        try:
            email_sslp = environ['EMAIL_SSL_PORT']
            email_smtp = environ['EMAIL_SMTP_SERVER']
            email_sender = environ['EMAIL_SENDER']
            email_receiver = environ['EMAIL_RECEIVER']
            email_sender_pw = environ['EMAIL_SENDER_PASSWORD']
        except KeyError:
            # Raise a system exit on error reading the parameters
            raise SystemExit(dedent('''\
            Either one or all of EMAIL_SSL_PORT, EMAIL_SMTP_SERVER
            EMAIL_SENDER, EMAIL_RECEIVER and EMAIL_SENDER_PASSWORD
            is not found in the .env
            ''').replace('\n', ' '))

        with smtplib.SMTP_SSL(email_smtp, email_sslp,
        context=ssl_context) as server:
            server.login(email_sender, email_sender_pw)
            server.sendmail(email_sender, email_receiver, email_msg)

    def detect_wan_anomaly(self, min_per_sample, interval_sec_present,
    interval_sec_hist):
        '''
        Detect WAN anomoly by comparing the means of the upload and
        download latency, jitter and packet loss of a recent timeframe
        to a historical baseline of given durations. Send an email
        notification with the details should an anomoly be found.
        '''
        if min(interval_sec_present, interval_sec_hist) / 60 < min_per_sample:
            '''
            Raise a system exit if either sampling durations
            is smaller than the sampling interval in minutes
            '''
            raise SystemExit('Sampling duration is smaller than the sampling interval')

        wan_quality_dataframe_present = self._get_wan_quality_dataframe(
                                        min_per_sample,
                                        interval_sec_present)
        wan_quality_dataframe_hist = self._get_wan_quality_dataframe(
                                        min_per_sample,
                                        interval_sec_hist, interval_sec_present)
        wan_anomaly = ''
        for edge in wan_quality_dataframe_present:
            for wan in wan_quality_dataframe_present[edge]:
                for quality in wan_quality_dataframe_present[edge][wan]:
                    if not quality == 'timestamp':
                        '''
                        WAN anomaly detection requires the WAN quality
                        to be present in interval_sec_hist as well as
                        interval_sec_present for obvious reason. The
                        for-loop attests to its existence in
                        interval_sec_present which leaves
                        interval_sec_hist to be checked.
                        '''
                        try:
                            wan_quality_dataframe_hist[edge][wan][quality]
                        except KeyError:
                            pass
                        else:
                            wan_quality_present_mean = \
                                wan_quality_dataframe_present[edge][wan][quality].mean()
                            wan_quality_hist_mean = \
                                wan_quality_dataframe_hist[edge][wan][quality].mean()
                            wan_quality_hist_std = \
                                wan_quality_dataframe_hist[edge][wan][quality].std()
                            wan_quality_hist_std_factor = 2

                            if wan_quality_present_mean \
                            > wan_quality_hist_mean \
                            + wan_quality_hist_std * wan_quality_hist_std_factor:
                                wan_anomaly_msg = '''\
                                %s of WAN %s between Edge %s and its associated
                                Gateway is found to be %s and is %s standard
                                deviation(s) away from the mean of %s and
                                standard deviation of %s of the %s minute(s) before.
                                ''' % (
                                self._get_wan_quality_name(quality),
                                self._get_wan_name(wan, self.metrics),
                                self._get_edge_name(edge, self.ent_edge),
                                str(round(wan_quality_present_mean, 2)),
                                str(round(wan_quality_hist_std_factor, 2)),
                                str(round(wan_quality_hist_mean, 2)),
                                str(round(wan_quality_hist_std, 2)),
                                str(round(interval_sec_hist / 60), 2))

                                wan_anomaly_msg = dedent(wan_anomaly_msg).replace('\n', ' ')
                                wan_anomaly += wan_anomaly_msg + '\n'
        if wan_anomaly:
            self._get_time()
            email_msg = 'Subject: WAN Anomoly Alert' \
                        + '\n\n' \
                        + 'As of ' + self.time_end + ' UTC:' \
                        + '\n' \
                        + wan_anomaly
            self._email_wan_anomaly(email_msg)

    def get_ent_events(self, interval_sec = None):
        '''
        Poll and return events given the enterpriseId and a specified
        time interval
        '''
        self._get_time(interval_sec)
        events = self.client.call_api('event/getEnterpriseEvents',
                    {
                        'enterpriseId': self.ent_id,
                        'interval': {
                            'start': self.time_start,
                            'end': self.time_end
                    }
        })
        try:
            return events['data']
        except KeyError:
            raise SystemExit('Event is not found in getEnterpriseEvents')

    def get_ent_fw_logs(self, interval_sec = None):
        '''
        Poll and return firewall logs given the enterpriseId and a
        specified time interval
        '''
        self._get_time(interval_sec)
        fw_logs = self.client.call_api(
                    'firewall/getEnterpriseFirewallLogs', {
                        'enterpriseId': self.ent_id,
                        'interval': {
                            'start': self.time_start,
                            'end': self.time_end
                    }
        })
        try:
            return fw_logs['data']
        except KeyError:
            raise SystemExit('Firewall log is not found in getEnterpriseFirewallLogs')


    def get_ent_edge_config(self):
        '''
        Poll and return the Edge config moodule given the
        enterpriseId and the edgeId
        '''
        edge_configs = {}
        for edge in self.edge_id:
            edge_config = self.client.call_api(
                            'edge/getEdgeConfigurationStack', {
                                'enterpriseId': self.ent_id,
                                'edgeId': edge
                            })
            edge_configs[self._get_edge_name(edge,
                self.ent_edge)] = edge_config

        if edge_configs:
            return edge_configs
        else:
            raise SystemExit('No Edge config is found in getEdgeConfigurationStack')

    def write_ent_edge_config(self, edge_configs):
        '''
        Write each of the Edge config stacks as JSON files in a
        directory named by the sanitised enterpriseName, and nested
        in a number of subdirectories named respectively by the year,
        the month and the day, and finally by the the full date and
        time now to ease access.
        .
        └── enterpriseName/
            └── Year/
                └── Month/
                    └── Date/
                        └── YYYY-MM-DD-HH-MM-SS/
                            ├── edgeName1.json
                            ├── edgeName2.json
                            ├── edgeName3.json
                            └── edgeName4.json
        '''
        ent_name_sanitised = self.__name_sanitised(self.ent_name)
        time_stamp = time.strftime('%Y-%m-%d-%H-%M-%S',
                        time.gmtime(self.__update_time()))
        date_time = datetime.datetime.strptime(time_stamp,
                    '%Y-%m-%d-%H-%M-%S')

        ent_edge_config_dir_list = [ent_name_sanitised,
                                    date_time.year,
                                    date_time.month,
                                    date_time.day,
                                    time_stamp]

        ent_edge_config_dir = path[0] + '/'

        for i in range(len(ent_edge_config_dir_list)):
            ent_edge_config_dir += str(ent_edge_config_dir_list[i]) + '/'

            try:
                mkdir(ent_edge_config_dir)
            except FileExistsError:
                pass

        for each in edge_configs:
            each_sanitised = self.__name_sanitised(each)
            with open(ent_edge_config_dir + each_sanitised + '.json',
            'w') as f:
                f.write(json.dumps(edge_configs[each]))

    def write_ent_events(self, events):
        '''
        Write each of the event in a JSON file named 'events' in
        a directory by the name of the sanitised enterpriseName.
        Each event will be logged in a new line in the JSON file.
        .
        └── enterpriseName/
            └── events.json
        '''
        if events:
            ent_name_sanitised = self.__name_sanitised(self.ent_name)
            ent_event_dir = path[0] + '/' + ent_name_sanitised + '/'
            ent_event_file_name = 'events'

            try:
                mkdir(ent_event_dir)
            except FileExistsError:
                pass

            event = ''
            for each in events:
                event += json.dumps(each) + '\n'

            with open(ent_event_dir + ent_event_file_name + '.json',
            'a') as f:
                f.write(event)
