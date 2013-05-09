#!/usr/bin/env python
""" cloudscraper.py

 A tool to extract and archive usage information from the CloudTrax wifi mesh
dashboard (cloudtrax.com).

"""

from email.mime.text import MIMEText
from BeautifulSoup import BeautifulSoup
import argparse
import cStringIO
import logging
import requests
import smtplib
import texttable
import ConfigParser
import Image

CONFIG_FILE = '/opt/cloudscraper/cloudscraper.conf'

NODE_STATUS = {'gw_down': '1',
               'relay_down': '2',
               'gw_up': '3',
               'relay_up': '4',
               'spare_gw_down': '5',
               'spare_down': '6',
               'spare_gw_up': '7',
               'spare_up': '8'}


#
# Helper functions
#

def distill_html(content, element, identifier):
    """Accept some HTML and return the filtered output"""
    distilled_text = []
    
    if element == 'table':
        distilled_table = BeautifulSoup(content).find(element, identifier)

        for row in distilled_table.findAll('tr'):
            raw_values = []

            for cell in row.findAll('td'):
                raw_values.append(cell.findAll(text=True))

            # Watch out for blank rows
            if len(raw_values) > 0:
                # Create a new node object for each node in the network
                distilled_text.append(raw_values)

    return distilled_text


def draw_table(entity_type, entities):
    """Draws a text table representation of the data supplied"""

    header = {'gateway': ['Name\n(mac)',
                          'Users',
                          'DL MB\nUL MB',
                          'Up\n(Down)',
                          'IP Address\n(Firmware)'],
              'relay': ['Name\n(mac)',
                        'Users',
                        'DL MB\nUL MB',
                        'Gateway\n(Firmware)',
                        'Up\n(Down)',
                        'Latency\n(Hops)'],
              'spare': ['Name\n(mac)',
                        'Users',
                        'DL MB\nUL MB',
                        'Up\n(Down)',
                        'IP Address\n(Firmware)']}

    table = texttable.Texttable()
    table.header(header[entity_type])

    for entity in entities:
        if entity.get_type() == entity_type:
            table.add_row(entity.get_table_row())


    return table.draw()


def percentage(value, max_value):
    """Returns a float representing the percentage that
       value is of max_value"""

    return (float(value) * 100) / max_value



#
# Objects
#

class Config:
    """Cloudscraper configuration class"""

    def __init__(self, network, config_file):
        """Constructor"""
        config = ConfigParser.RawConfigParser()
        config.read(config_file)

        self.url = {'base': config.get('common', 'cloudtrax_url')}

        self.url = {'login': self.url['base'] +
                             config.get('common', 'login_page'),
                     'data': self.url['base'] +
                             config.get('common', 'data_page'),
                     'user': self.url['base'] +
                             config.get('common', 'user_page'),
                     'checkin': self.url['base'] +
                             config.get('common', 'node_checkin_page')}

        self.database = {'type': config.get('database', 'type')}

        if self.database['type'] != "none":
            self.database = {'database': config.get('database', 'database'),
                             'username': config.get('database', 'username'),
                             'password': config.get('database', 'password')}

        self.email = {'to': config.get('email', 'to'),
                      'from': config.get('email', 'from'),
                      'subject': config.get('email', 'subject'),
                      'server': config.get('email', 'server')}

        self.network = {'name': network,
                        'username': config.get(network, 'username'),
                        'password': config.get(network, 'password')}

    def get_url(self):
        """Return url config"""
        return self.url

    def get_database(self):
        """Return database config"""
        return self.database

    def get_email(self):
        """Return email config"""
        return self.email

    def get_network(self):
        """Return network config"""
        return self.network


class CloudTrax:
    """CloudTrax connector class"""

    def __init__(self, config):
        """Constructor"""
        self.nodes = []
        self.users = []

        self.session = requests.session()

        logging.info('Verbose output is turned on')

        self.url = config.get_url()
        self.network = config.get_network()


    def login(self):
        """Method to login and create a web session"""

        logging.info('Logging in to CloudTrax Dashboard')

        parameters = {'account': self.network['username'],
                      'password': self.network['password'],
                      'status': 'View Status'}

        try:
            request = self.session.post(self.url['login'], data=parameters)
            request.raise_for_status()

        except requests.exceptions.HTTPError:
            logging.error('There was a HTTP error')
            exit(1)
        except requests.exceptions.ConnectionError:
            logging.error('There was a connection error')
            exit(1)

        return self.session

    def get_checkin_data(self, node_mac):
        """Scrape checkin information on the current node"""

        parameters = {'mac': node_mac,
                      'legend': '0'}

        logging.info('Requesting node checkin status for ' + node_mac)

        request = self.session.get(self.url['checkin'], params=parameters)

        colour_counter = {'cccccc': 0, '1faa5f': 0, '4fdd8f': 0}

        checkin_img = Image.open(cStringIO.StringIO(request.content))

        row = 1

        pixelmap = checkin_img.load()

        for col in range(0, checkin_img.size[0]):
            pixel_colour = str("%x%x%x" % (pixelmap[col, row][0],
                                           pixelmap[col, row][1],
                                           pixelmap[col, row][2]))

            if pixel_colour in colour_counter.keys():
                colour_counter[pixel_colour] += 1
            else:
                colour_counter[pixel_colour] = 1

        # Convert number of pixels into a percent
        time_as_gw = percentage(colour_counter['1faa5f'],
                                checkin_img.size[0] - 2)
        time_as_relay = percentage(colour_counter['4fdd8f'],
                                   checkin_img.size[0] - 2)
        time_offline = percentage(colour_counter['cccccc'],
                                  checkin_img.size[0] - 2)

        return (time_as_gw, time_as_relay, time_offline)

    def get_session(self):
        """Return session id"""
        return self.session

    def get_nodes(self):
        """Return a list of nodes"""

        # Refresh the network status if the nodes list is empty
        if len(self.nodes) == 0:
            logging.info('Refreshing node status from CloudTrax')
            self.refresh_nodes()

        return self.nodes

    def get_users(self):
        """Return network status"""
        if len(self.users) == 0:
            logging.info('Refreshing user statistics from CloudTrax')
            self.refresh_users()

        return self.users

    def refresh_nodes(self):
        """Return network information scraped from CloudTrax"""
        self.nodes = []

        parameters = {'network': self.network['name'],
                      'showall': '1',
                      'details': '1'}
    
        logging.info('Requesting network status') 

        request = self.session.get(self.url['data'], params=parameters)

        logging.info('Received network status ok') 

        if request.status_code == 200:
            for raw_values in distill_html(request.content, 'table',
                                           {'id': 'mytable'}):
                self.nodes.append(Node(raw_values,
                    self.get_checkin_data(raw_values[2][0])))

        else:
            logging.error('Request failed') 
            exit(request.status_code)

        return self.nodes

    def refresh_users(self):
        """Return a list of wifi user statistics scraped from CloudTrax"""
        self.users = []

        parameters = {'network': self.network['name']}
    
        logging.info('Requesting user statistics') 

        request = self.session.get(self.url['user'], params=parameters)

        logging.info('Received user statistics ok') 


        if request.status_code == 200:
            for raw_values in distill_html(request.content, 'table',
                                           {'class': 'inline sortable'}):
                self.users.append(User(raw_values))

        else:
            logging.error('Request failed') 
            exit(request.status_code)

        return self.users

    def report_nodes(self):
        """Return a string containing a pretty nodes report"""
        report = 'Node statistics for the last 24 hours\n'
        report += '-------------------------------------\n\n'

        self.get_nodes()

        report += 'Gateway nodes\n'
        report += draw_table('gateway', self.nodes)
        report += '\n\n'
        report += 'Relay nodes\n'
        report += draw_table('relay', self.nodes)
        report += '\n\n'
        report += 'Spare nodes\n'
        report += draw_table('spare', self.nodes)
        report += '\n\n'

        return report

    def report_users(self):
        """Return a string containing a pretty user report"""
        report = 'User statistics for the last 24 hours\n'
        report += '-------------------------------------\n\n'
        report += 'Users\n'

        table = texttable.Texttable()
        table.header(['Name\n(mac)',
                      'Last seen on',
                      'Blocked',
                      'MB Down',
                      'MB Up'])

        self.get_users()

        for user in self.users:
            table.add_row(user.get_table_row())

        report += table.draw()
        report += '\n\n'

        return report


class Database:
    """Database connector class"""

    def __init__(self, config):
        """Constructor"""
        pass


class Node:
    """CloudTrax node class"""
    def __init__(self, values, checkin_data):
        """Constructor"""
        if values[0][0] == NODE_STATUS['gw_up']:
            self.node_type = 'gateway'
            self.node_status = 'up'
        elif values[0][0] == NODE_STATUS['gw_down']:
            self.node_type = 'gateway'
            self.node_status = 'down'
        elif values[0][0] == NODE_STATUS['relay_up']:
            self.node_type = 'relay'
            self.node_status = 'down'
        elif values[0][0] == NODE_STATUS['relay_down']:
            self.node_type = 'relay'
            self.node_status = 'down'
        elif values[0][0] == NODE_STATUS['spare_gw_up']:
            self.node_type = 'spare'
            self.node_status = 'up'
        elif values[0][0] == NODE_STATUS['spare_gw_down']:
            self.node_type = 'spare'
            self.node_status = 'down'
        elif values[0][0] == NODE_STATUS['spare_up']:
            self.node_type = 'spare'
            self.node_status = 'up'
        elif values[0][0] == NODE_STATUS['spare_down']:
            self.node_type = 'spare'
            self.node_status = 'down'

        self.values = {'name': values[1][0],
                       'comment': values[1][-1],
                       'mac': values[2][0],
                       'ip': values[2][1],
                       'chan_24': values[3][0],
                       'chan_58': values[3][1],
                       'users': values[4][0],
                       'dl': values[5][0],
                       'ul': values[5][1],
                       'uptime': values[6][0],
                       'fw_version': values[7][0],
                       'fw_name': values[7][1],
                       'load': values[8][0],
                       'memfree': values[8][1],
                       'last_checkin': values[9][-1],
                       'gateway_name': values[10][0],
                       'gateway_ip': values[10][1],
                       'hops': values[11][0],
                       'latency': values[12][0]}

        self.checkin_data = checkin_data

    def get_mac(self):
        """Return the mac address of this node"""
        return self.values['mac']

    def get_time_offline(self):
        """Return a float of the percent of time in 24hrs offline"""
        return self.checkin_data[2]

    def get_time_gw(self):
        """Return a float representing the percent of time in 24hrs online
           as a gateway node"""
        return self.checkin_data[0]

    def get_time_relay(self):
        """Return a float representing the percent of time in 24hrs online
           as a relay node"""
        return self.checkin_data[1]

    def get_type(self):
        """Return a string that describes the node type."""
        return self.node_type

    def get_table_row(self):
        """Returns a list of items that match up to the screen text table
           for the node type"""

        if self.node_type == 'gateway' or self.node_type == 'spare':
            row = [self.values['name'] + '\n(' + self.values['mac'] + ')',
                   self.values['users'],
                   self.values['dl'] + '\n(' + self.values['ul'] + ')',
                   '%.2f' % (self.checkin_data[0]) + '%\n(' + 
                       '%.2f' % (100 - self.checkin_data[0]) + '%)',
                   self.values['gateway_ip'] + '\n(' +
                       self.values['fw_version'] + ')']

        elif self.node_type == 'relay':
            row = [self.values['name'] + '\n(' + self.values['mac'] + ')',
                   self.values['users'],
                   self.values['dl'] + '\n(' + self.values['ul'] + ')',
                   self.values['gateway_name'] + '\n(' + 
                       self.values['fw_version'] + ')',
                   '%.2f' % (self.checkin_data[1]) + '%\n(' + 
                       '%.2f' % (100 - self.checkin_data[1]) + '%)',
                   self.values['latency'] + 'ms\n(' + self.values['hops'] + ')']

        return row


class User:
    """Wifi user class"""

    def __init__(self, values):
        """Constructor"""
        self.values = {'name': values[0][0],
                       'mac': values[0][-1],
                       'node_name': values[1][0],
                       'node_mac': values[1][1],
                       'rssi': values[3][0],
                       'rate': values[4][0],
                       'MCS': values[4][1],
                       'kb_down': values[5][0].replace(',', ''),
                       'kb_up': values[6][0].replace(',', ''),
                       'blocked': values[8][0]}
                       #'device_vendor': values[2]}

        logging.info('Creating user object for ' + self.values['mac'])

    def get_values(self):
        """Returns a bunch of values"""
        return self.values

    def get_table_row(self):
        """Returns a list of items to include in the user screen text table"""

        row = [self.values['name'] + '\n(' + self.values['mac'] + ')',
               self.values['node_name'] + '\n(' + self.values['node_mac'] + ')',
               self.values['blocked'],
               '%.2f' % (self.get_dl()),
               '%.2f' % (self.get_ul())]

        return row

    def get_dl(self):
        """Returns a float representing the number of megabytes downloaded 
           in the past 24hrs"""
        return float(self.values['kb_down']) / 1000

    def get_ul(self):
        """Returns a float representing the number of megabytes uploaded
           in the past 24hrs"""
        return float(self.values['kb_up']) / 1000


#
# Program starts here!
#

parser = argparse.ArgumentParser(description = 'Statistics scraper for the ' +
                                               'CloudTrax controller')
parser.add_argument('-d', '--database',
                    action = 'store_true',
                    default = False, 
                    help = 'Store the output to a database')
parser.add_argument('-e', '--email',
                    action = 'store_true',
                    default = False, 
                    help = 'Email the output')
parser.add_argument('-f', '--file',
                    nargs = 1, 
                    help = 'Store the output to a file')
parser.add_argument('-n', '--network',
                    nargs = 1, 
                    help = 'The wifi network name on CloudTrax')
parser.add_argument('-s', '--screen',
                    action = 'store_true',
                    default = False, 
                    help = 'Display the output to stdout')
parser.add_argument('-v', '--verbose',
                    action = 'store_true',
                    default = False, 
                    help = 'Be Verbose')
parser.add_argument('-N', '--network-status',
                    action = 'store_true',
                    default = False,
                    help = 'Get the network status')
parser.add_argument('-U', '--usage',
                    action = 'store_true',
                    default = False,
                    help = 'Get the usage statistics')
args = parser.parse_args()

# Set up logging
if args.verbose:
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.basicConfig(level=logging.WARNING,
                        format='%(asctime)s - %(levelname)s - %(message)s')

if args.network:
    # We need to know to output the result
    if not (args.database or args.email or args.file or args.screen):
        parser.error('No output defined')

    # We need to know what kind of information to include
    # TODO: by adding args.database here, we potentially have a problem
    # if we also have args.screen or args.email as well. We might fix
    # this by making those options mutally exclusive.
    if not (args.database or args.network_status or args.usage):
        parser.error('What do you want to know?')

    config = Config(args.network[0], CONFIG_FILE)

    cloudtrax = CloudTrax(config)
    cloudtrax.login()

    msg = ""

    if args.network_status:
        msg += cloudtrax.report_nodes()

    if args.usage:
        msg += cloudtrax.report_users()

    if args.database:
        logging.info('Processing database output')
        pass

    if args.screen:
        logging.info('Processing screen output')
        print msg

    if args.email:
        logging.info('Processing email output')
        email = MIMEText('<pre>' + msg + '</pre>', 'html')
        email['Subject'] = config.get_email()['subject']
        email['From'] = config.get_email()['from']
        email['To'] = config.get_email()['to']

        # Send the message via our own SMTP server, but don't include the
        # envelope header.
        mailer = smtplib.SMTP(config.get_email()['server'])
        mailer.sendmail(config.get_email()['from'],
                        config.get_email()['to'].split(),
                        email.as_string())
        mailer.quit()

    if args.file:
        logging.info('Processing file output')
        fileout = open(args.file[0], 'w')
        fileout.write(msg)
        fileout.close()

else:
    parser.error('You must provide a network')

