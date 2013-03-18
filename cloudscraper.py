#!/usr/bin/env python
""" cloudscraper.py

 A tool to extract and archive usage information from the CloudTrax wifi mesh
dashboard (cloudtrax.com).

"""

from BeautifulSoup import BeautifulSoup
from time import time
import argparse
import cStringIO
import requests
import texttable
import urllib2
import ConfigParser
import Image

CONFIG_FILE = 'cloudscraper.conf'

TYPE = {'gw_down': '1',
        'relay_down': '2',
        'gw_up': '3',
        'relay_up': '4',
        'spare_gw_down': '5',
        'spare_down': '6',
        'spare_gw_up': '7',
        'spare_up': '8'}

def underline(text):
    """Returns an underlined version of the text supplied"""

    return text + '\n' + (len(text) * '-') + '\n'

def print_if_verbose(message):
    """Print the message to stdout if verbose output is requested"""
    if args.verbose:
        print timer.get_elapsed_time(), message

def render_table(data):
    """Render a text table representation of the data supplied"""

    gateway_table = texttable.Texttable()
    gateway_table.header(['Name\n(Firmware)', 'Users', 'DL MB', 'UL MB', 
                          'IP Address'])

    relay_table = texttable.Texttable()
    relay_table.header(['Name\n(Firmware)', 'Users', 'DL MB', 'UL MB', 
                        'Gateway', 'Latency\n(Hops)'])

    spare_table = texttable.Texttable()
    spare_table.header(['Name\n(Firmware)', 'Users', 'DL MB', 'UL MB', 
                        'IP Address'])
    omitted = 0

    for item in data:
        if item['type'] == TYPE['gw_up'] or item['type'] == TYPE['gw_down']:
            row = [item['name'] +'\n(' + item['fw_version'] + ')',
                   item['users_24'],
                   item['download_24'], 
                   item['upload_24'], 
                   item['gateway_ip']]

            gateway_table.add_row(row)
        elif item['type'] == TYPE['relay_up'] or item['type'] == TYPE['relay_down']:
            row = [item['name'] +'\n(' + item['fw_version'] + ')',
                   item['users_24'],
                   item['download_24'], 
                   item['upload_24'], 
                   item['gateway_name'],
                   item['latency'] + 'ms\n(' + item['hops'] + ')']

            relay_table.add_row(row)
        elif item['type'] == TYPE['spare_gw_up'] or item['type'] == TYPE['spare_gw_down'] or item['type'] == TYPE['spare_up'] or item['type'] == TYPE['spare_down']:

            row = [item['name'] +'\n(' + item['fw_version'] + ')',
                   item['users_24'],
                   item['download_24'], 
                   item['upload_24'], 
                   item['gateway_ip']]

            spare_table.add_row(row)
        else:
            omitted += 1

    render = underline('Usage for the last 24 hours')
    render += '\n\n' 'Gateway nodes' + '\n'
    render += gateway_table.draw() + '\n'
    render += '\n\n' + 'Relay nodes' + '\n'
    render += relay_table.draw() + '\n'
    render += '\n\n' + 'Spare nodes' + '\n'
    render += spare_table.draw() + '\n'
    if omitted > 0:
        render += 'Warning: There are ' + str(omitted) + ' Nodes that have been missed from this report\n'

    return render


class Timer:
    """Universal stopwatch class"""
    def __init__(self):
        # Start the clock
        self.start_time = time()

    def get_elapsed_time(self):
        """Returns the number of seconds elapsed"""
        return "%.2f" % (time() - self.start_time)

class Node:
    """CloudTrax node class"""

    def __init__(self, session, values):
        """Constructor"""
        # TODO: time_since_last_checkin can be a 2 element array if down or late.
        self.nodetype = values[0][0]
        self.name = values[1][0]
        self.comment = values[1][-1]
        self.mac = values[2][0]
        self.ip = values[2][1]
        self.chan_24 = values[3][0]
        self.chan_58 = values[3][1]
        self.users_24 = values[4][0]
        self.download_24 = values[5][0]
        self.upload_24 = values[5][1]
        self.uptime = values[6][0]
        self.fw_version = values[7][0]
        self.fw_name = values[7][1]
        self.load = values[8][0]
        self.memfree = values[8][1]
        self.time_since_checkin = values[9][0]
        self.gateway_name = values[10][0]
        self.gateway_ip = values[10][1]
        self.hops = values[11][0]
        self.latency = values[12][0]

        self.time_as_gw = 0
        self.time_as_relay = 0
        self.time_offline = 0

        self.checkin_baseurl='https://www.cloudtrax.com/checkin-graph2.php?legend=0&mac='

        self.scrape_checkin_data(session)

    def get_mac(self):
        """Return the mac address of this node"""
        return self.mac

    def get_time_offline(self):
        """Return a float of the percent of time in 24hrs offline"""
        return self.time_offline

    def get_time_gw(self):
        """Return a float of the percent of time in 24hrs online as a gateway node"""
        return self.time_as_gw

    def get_time_relay(self):
        """Return a float of the percent of time in 24hrs online as a relay node"""
        return self.time_as_relay

    def scrape_checkin_data(self, session):
        """Scrape checkin information on the current node"""

        #parameters = {'mac': self.mac,
                      #'legend': '0'}

        #print_if_verbose('Requesting node checkin status')

        #request = session.get(self.checkin_baseurl + self.mac, params=parameters)

        imgdata = urllib2.urlopen(self.checkin_baseurl + self.mac).read()

        self.colour_counter = {'cccccc': 0, '1faa5f': 0, '4fdd8f': 0}

        self.checkin_img = Image.open(cStringIO.StringIO(imgdata))
        self.checkin_img_width = self.checkin_img.size[0]
        self.checkin_img_height = self.checkin_img.size[1]

        ROW = 1

        pixelmap = self.checkin_img.load()

        for col in range(0, self.checkin_img_width):
            pixel_colour = str("%x%x%x" % (pixelmap[col,ROW][0], pixelmap[col,ROW][1], pixelmap[col,ROW][2]))

            if pixel_colour in self.colour_counter.keys() and pixel_colour != '000':
                self.colour_counter[pixel_colour] += 1
            else:
                self.colour_counter[pixel_colour] = 1


        # Convert number of pixels into a percent
        self.time_as_gw = self.colour_counter['1faa5f'] / (self.checkin_img_width - 2) * 100
        self.time_as_relay = self.colour_counter['4fdd8f'] / (self.checkin_img_width - 2) * 100
        self.time_offline = self.colour_counter['cccccc'] / (self.checkin_img_width - 2) * 100

        return self.colour_counter


class CloudTrax:
    """CloudTrax connector class"""

    def __init__(self, network, verbose):
        """Constructor"""
        self.network = network
        self.nodes = []

        self.verbose = verbose
        print_if_verbose('Verbose output is turned on')

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
        self.session = requests.session()

        print_if_verbose('Logging in to CloudTrax Dashboard')

        parameters = {'account': self.username,
                      'password': self.password,
                      'status': 'View Status'}

        try:
            s = self.session.post(self.login_url, data=parameters)
            s.raise_for_status()

        except requests.exceptions.HTTPError:
            print_if_verbose('There was a HTTP error')
            exit(1)
        except requests.exceptions.ConnectionError:
            print_if_verbose('There was a connection error')
            exit(1)

        return self.session

    def get_session(self):
        """Return session id"""
        return self.session

    def get_request(self):
        """Return request id"""
        return self.request

    def get_nodes(self):
        """Return a list of nodes"""

        # Refresh the network status if the nodes list is empty
        if len(self.nodes) == 0:
            print_if_verbose('Refreshing node status from CloudTrax')
            self.refresh_network_status()

        return self.nodes

    def get_users(self):
        """Return network status"""
        if len(self.users) == 0:
            print_if_verbose('Refreshing user status from CloudTrax')
            self.refresh_users()

        return self.users

    def refresh_network_status(self):
        """Return network information scraped from CloudTrax"""
        self.nodes = []

        parameters = {'network': self.network,
                      'showall': '1',
                      'details': '1'}
    
        print_if_verbose('Requesting network status') 

        self.request = self.session.get(self.data_url, params=parameters)

        print_if_verbose('Received network status ok') 

        if self.request.status_code == 200:
            distilled_table = BeautifulSoup(self.request.content).find('table', {'id': 'mytable'})

            for row in distilled_table.findAll('tr'):
                raw_values = []

                for cell in row.findAll('td'):
                    raw_values.append(cell.findAll(text=True))

                # Watch out for blank rows
                if len(raw_values) > 0:
                    # Create a new node object for each node in the network
                    self.nodes.append([raw_values[2][0], Node(self.session, raw_values)])

        else:
            print_if_verbose('Request failed') 
            exit(self.request.status_code)

        return self.nodes


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

if args.verbose:
    timer = Timer()

if args.network:
    cloudtrax = CloudTrax(args.network[0], args.verbose)
    cloudtrax.login()

    if args.screen:
        #cloudtrax.get_user_status()
        print cloudtrax.get_nodes()
        #print render_table(cloudtrax.get_network_status())

        for node in cloudtrax.get_nodes():
            print node[0], node[1].get_time_gw(), node[1].get_time_relay(), node[1].get_time_offline()
else:
    parser.print_help()
    exit(1)

