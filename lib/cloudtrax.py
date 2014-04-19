#!/usr/bin/env python
""" lib/cloudtrax.py

 CloudTrax class for CloudScraper

 Copyright (c) 2013 The Goulburn Group. All Rights Reserved.

 http://www.goulburngroup.com.au

 Written by Alex Ferrara <alex@receptiveit.com.au>

"""

from BeautifulSoup import BeautifulSoup
from lib.node import Node
from lib.user import User
import cStringIO
import logging
import requests
import texttable
import pygal
import Image


#
# Helper functions
#

def draw_table(entity_type, entities):
    """Draws a text table representation of the data supplied"""

    header = {'gateway': ['Name\n(mac)',
                          'Users',
                          'DL MB\n(UL MB)',
                          'GWDL MB\n(GWUL MB)',
                          'Up\n(Down)',
                          'IP Address\n(Firmware)'],
              'relay': ['Name\n(mac)',
                        'Users',
                        'DL MB\n(UL MB)',
                        'Gateway\n(Firmware)',
                        'Up\n(Down)',
                        'Latency\n(Hops)'],
              'spare': ['Name\n(mac)',
                        'Users',
                        'DL MB\n(UL MB)',
                        'Up\n(Down)',
                        'IP Address\n(Firmware)']}

    table = texttable.Texttable()
    table.header(header[entity_type])

    for entity in entities:
        if entities[entity].get_type() == entity_type:
            table.add_row(entities[entity].get_table_row())

    return table.draw()


def distill_html(content, element, identifier):
    """Accept some HTML and return the filtered output"""
    distilled_text = []

    trimed_content = BeautifulSoup(content).find(element, identifier)

    if element == 'table':

        try:
            for row in trimed_content.findAll('tr'):
                raw_values = []

                for cell in row.findAll('td'):
                    raw_values.append(cell.findAll(text=True))

                # Watch out for blank rows
                if len(raw_values) > 0:
                    # Create a new node object for each node in the network
                    distilled_text.append(raw_values)

        except AttributeError:
            pass

    if element == 'select':

        try:
            for row in trimed_content.findAll('option', text=True):
                if len(row) > 0:
                    distilled_text.append(row)

        except AttributeError:
            pass

    return distilled_text


def percentage(value, max_value):
    """Returns a float representing the percentage that
       value is of max_value"""

    return (float(value) * 100) / max_value


class CloudTrax:
    """CloudTrax connector class"""

    def __init__(self, config):
        """Constructor"""
        self.nodes = dict()
        self.users = dict()
        self.usage = [0, 0]
        self.alerting = []

        self.session = requests.session()

        logging.info('Verbose output is turned on')

        self.config = config
        self.url = self.config.get_url()
        self.network = self.config.get_network()

        self.login()

        self.collect_nodes()
        self.collect_users()


    def login(self):
        """Method to login and create a web session"""

        logging.info('Logging in to CloudTrax Dashboard')

        parameters = {'login': self.network['username'],
                      'login-pw': self.network['password'],
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

        # If the login referes to a master network with recursion,
        # we need to iterate through them to get our stats
        if self.network['recurse']:
            networks = distill_html(request.content, 
                                    'select',
                                    {'name': 'networks'})

            for network in networks:

                network = str(network).split(' ', 1)[0]

                if network not in self.network['networks']:
                    self.network['networks'].append(network)

        return self.session

    def get_alerting(self):
        """Return a list of alerting nodes"""
        return self.alerting

    def get_checkin_data(self, node_mac):
        """Scrape checkin information on the current node"""

        parameters = {'mac': node_mac,
                      'legend': '0'}

        logging.info('Requesting node checkin status for %s', node_mac)

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
        time_online = time_as_gw + time_as_relay

        return (time_as_gw, time_as_relay, time_offline, time_online)

    def get_session(self):
        """Return session id"""
        return self.session

    def get_sub_networks(self):
        """Return a list of networks associated with this login"""
        return self.sub_networks

    def get_nodes(self):
        """Return a list of node objects"""
        return self.nodes

    def get_users(self):
        """Return a list of user objects"""
        return self.users

    def get_usage(self):
        """Return network usage"""
        return self.usage

    def collect_nodes(self):
        """Return network information scraped from CloudTrax"""

        for network in self.network['networks']:
            parameters = {'id': network,
                          'showall': '1',
                          'details': '1'}
    
            logging.info('Requesting network status') 

            request = self.session.get(self.url['data'], params=parameters)

            logging.info('Received network status ok') 

            if request.status_code == 200:
                for raw_values in distill_html(request.content, 'table',
                                               {'id': 'mytable'}):

                    node = Node(raw_values,
                                self.get_checkin_data(raw_values[2][0]),
                                network)

                    if node.is_alerting():
                        logging.info('%s is alerting' % (node))
                        self.alerting.append(node)

                    self.nodes[node.get_mac()] = node

            else:
                logging.error('Request failed') 
                exit(request.status_code)

        return self.nodes

    def collect_users(self):
        """Return a list of wifi user statistics scraped from CloudTrax"""

        for network in self.network['networks']:
            parameters = {'id': network}
    
            logging.info('Requesting user statistics') 

            request = self.session.get(self.url['user'], params=parameters)

            logging.info('Received user statistics ok') 


            if request.status_code == 200:
                for raw_values in distill_html(request.content, 'table',
                                               {'class': 'inline sortable'}):

                    user = User(raw_values)
                    usage_dl = user.get_dl()
                    usage_ul = user.get_ul()
                    user_mac = user.get_mac()
                    node_mac = user.get_node_mac()

                    if user_mac in self.users.keys():
                        self.users[user_mac].add_usage(usage_dl, usage_ul)
                    else:
                        self.users[user_mac] = user

                    gateway = self.nodes[node_mac].add_usage(usage_dl, 
                                                             usage_ul)

                    if gateway != 'self' and gateway != 'not reported':
                        self.nodes[node_mac].add_gw_usage(usage_dl, usage_ul)

                    self.usage[0] += usage_dl
                    self.usage[1] += usage_ul

            else:
                logging.error('Request failed') 
                exit(request.status_code)

        return self.users

    def graph(self, graph_type, title, arg, img_format='svg'):
        """Return a rendered graph"""
        
        if graph_type == 'node':
            graph = self.graph_node_usage(arg)
        elif graph_type == 'user':
            graph = self.graph_user_usage()
        else:
            logging.error('Unknown graph type')
            exit(1)

        graph.title = title

        if img_format == 'png':
            return graph.render_to_png()

        return graph.render()

    def graph_node_usage(self, gw_only=False):
        """Return a node graph"""

        graph_object = pygal.Pie()

        for node in self.nodes:
            if gw_only:
                if self.nodes[node].is_gateway():
                    graph_object.add(self.nodes[node].get_name(), self.nodes[node].get_gw_usage())
            else:
                graph_object.add(self.nodes[node].get_name(), self.nodes[node].get_usage())

        return graph_object

    def graph_user_usage(self, gw_only=False):
        """Return a user graph"""

        graph_object = pygal.XY(stroke=False)

        for user in self.users:
            graph_object.add(user, [(self.users[user].get_dl(),
                                    self.users[user].get_ul())])

        return graph_object

    def report_summary(self):
        """Return a string containing a pretty summary report"""
        report = 'Summary statistics for the last 24 hours\n'
        report += '----------------------------------------\n\n'
        if len(self.alerting) > 0:
            report += "*** Warning - %s nodes are alerting ***\n\n" % (len(self.alerting))

        report += "Total users: %d\n" % len(self.users)

        report += "Total downloads (MB): %.2f\n" % (float(self.usage[0]) / 1000)
        report += "Total uploads (MB): %.2f\n" % (float(self.usage[1]) / 1000)
        report += '\n\n'

        return report

    def report_nodes(self):
        """Return a string containing a pretty nodes report"""
        report = 'Node statistics for the last 24 hours\n'
        report += '-------------------------------------\n\n'

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
                      'DL MB',
                      'UL MB'])

        self.get_users()

        for user in self.users:
            table.add_row(self.users[user].get_table_row())

        report += table.draw()
        report += '\n\n'

        return report
