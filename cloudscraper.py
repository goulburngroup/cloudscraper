#!/usr/bin/env python
""" cloudscraper.py

 A tool to extract and archive usage information from the CloudTrax wifi mesh
dashboard (cloudtrax.com).

"""

from requests import session
from BeautifulSoup import BeautifulSoup
import argparse
import ConfigParser

CONFIG_FILE = 'cloudscraper.conf'

class CloudTrax:
    """CloudTrax connector class"""

    def __init__(self, network, verbose):
        """Constructor"""
        self.network = network
        self.network_status = []

        self.verbose = verbose
        self.print_if_verbose('Verbose output is turned on')

        self.config = ConfigParser.RawConfigParser()
        self.config.read(CONFIG_FILE)

        self.cloudtrax_url = self.config.get('common', 'cloudtrax_url')
        self.login_url = self.cloudtrax_url + self.config.get('common', 'login_page')
        self.data_url = self.cloudtrax_url + self.config.get('common', 'data_page')
        self.user_url = self.cloudtrax_url + self.config.get('common', 'user_page')

        self.username = self.config.get(self.network, 'username')
        self.password = self.config.get(self.network, 'password')

    def login(self):
        """Method to login and create a web session"""
        self.session = session()

        self.print_if_verbose('Logging in to CloudTrax Dashboard')

        s = self.session.post(self.login_url, 
                              data={'account': self.username,
                                    'password': self.password,
                                    'status': 'View Status'})

        s.raise_for_status()

        return self.session

    def get_session(self):
        """Return session id"""
        return self.session

    def get_request(self):
        """Return request id"""
        return self.request

    def get_network_status(self):
        """Return network status"""
        if len(self.network_status) == 0:
            self.print_if_verbose('Refreshing network status from CloudTrax')

            self.refresh_network_status()

        return self.network_status

    def refresh_network_status(self):
        """Return network information scraped from CloudTrax"""
        self.network_status = []

        parameters = {'network': self.network,
                      'showall': '1',
                      'details': '1'}
    
        self.request = self.session.get(self.data_url, params=parameters)

        if self.request.status_code == 200:
            distilled_table = BeautifulSoup(self.request.content).find('table', {'id': 'mytable'})

            for row in distilled_table.findAll('tr'):
                raw_values = []

                for cell in row.findAll('td'):
                    raw_values.append(cell.findAll(text=True))

                # Watch out for blank rows
                if len(raw_values) > 0:
                    # TODO: time_since_last_checkin can be a 2 element array if down or late.
                    self.network_status.append({'type': raw_values[0][0],
                                   'name': raw_values[1][0],
                                   'comment': raw_values[1][-1],
                                   'mac': raw_values[2][0],
                                   'ip': raw_values[2][1],
                                   'chan_24': raw_values[3][0],
                                   'chan_58': raw_values[3][1],
                                   'users_24': raw_values[4][0],
                                   'download_24': raw_values[5][0],
                                   'upload_24': raw_values[5][1],
                                   'uptime': raw_values[6][0],
                                   'fw_version': raw_values[7][0],
                                   'fw_name': raw_values[7][1],
                                   'load': raw_values[8][0],
                                   'memfree': raw_values[8][1],
                                   'time_since_checkin': raw_values[9][0],
                                   'gateway_name': raw_values[10][0],
                                   'gateway_ip': raw_values[10][1],
                                   'hops': raw_values[11][0],
                                   'latency': raw_values[12][0]})

        else:
            exit(1)

        return self.network_status

    def print_if_verbose(self, message):
        """Print the message to stdout if verbose output is requested"""
        if self.verbose:
            print message
    
       
#
# Program starts here!
#

parser = argparse.ArgumentParser(description='Statistics scraper for the CloudTrax controller')
parser.add_argument('-n', '--network', nargs=1, 
                    help='The wifi network name on CloudTrax')
parser.add_argument('-f', '--file', nargs=1, 
                    help='Store the output to a file')
parser.add_argument('-d', '--database', nargs=1, 
                    help='Store the output to a database')
parser.add_argument('-s', '--screen', action='store_true', default=False, 
                    help='Display the output to stdout')
parser.add_argument('-v', '--verbose', action='store_true', default=False, 
                    help='Be Verbose')
parser.add_argument('-N', '--network-status', help='Get the network status')
parser.add_argument('-U', '--usage-stats', help='Get the usage statistics')
args = parser.parse_args()

if args.network:
    cloudtrax = CloudTrax(args.network[0], args.verbose)
    cloudtrax.login()

    if args.screen:
        tmp = cloudtrax.get_network_status()
        for t in tmp:
            print t['name']
else:
    parser.print_help()
    exit(1)

