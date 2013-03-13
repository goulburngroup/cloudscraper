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

CLOUDTRAX_BASE = 'https://cloudtrax.com/'
LOGIN_URL = 'dashboard.php'
DATA_URL = 'nodes_attnt2.php'
USER_URL = 'users2.php'


class CloudTrax:
    """CloudTrax connector class"""

    def __init__(self, network):
        """Constructor"""
        self.network = network

        self.config = ConfigParser.RawConfigParser()
        self.config.read(CONFIG_FILE)
        self.username = self.config.get(self.network, 'username')
        self.password = self.config.get(self.network, 'password')

    def login(self):
        """Method to login and create a web session"""
        self.session = session()
        s = self.session.post(CLOUDTRAX_BASE + LOGIN_URL, 
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
        """Return network information scraped from CloudTrax"""
        self.network_status = []

        self.request = self.session.get(CLOUDTRAX_BASE + DATA_URL,
                                        params={'network': self.network,
                                                'showall': '1',
                                                'details': '1'})

        if self.request.status_code == 200:
            distilled_table = BeautifulSoup(self.request.content).find('table', {'id': 'mytable'})

            for row in distilled_table.findAll('tr'):
                raw_values = []

                for cell in row.findAll('td'):
                    raw_values.append(cell.findAll(text=True))

                # Watch out for blank rows
                if len(raw_values) > 0:
                    # TODO: time_since_last_checkin can be a 2 element array if down.
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
    
       
#
# Program starts here!
#

parser = argparse.ArgumentParser(description='Statistics scraper for the CloudTrax controller')
parser.add_argument('-n', '--network', nargs=1, help='The wifi network name on CloudTrax')
parser.add_argument('-f', '--file', nargs=1, help='Store the output to a file')
parser.add_argument('-d', '--database', nargs=1, help='Store the output to a database')
parser.add_argument('-s', '--screen', action='store_true', default=False, help='Display the output to stdout')
parser.add_argument('-N', '--network-status', help='Get the network status')
parser.add_argument('-U', '--usage-stats', help='Get the usage statistics')
args = parser.parse_args()

if args.network:
    cloudtrax = CloudTrax(args.network[0])
    cloudtrax.login()
    print cloudtrax.get_network_status()
else:
    parser.print_help()
    exit(1)

