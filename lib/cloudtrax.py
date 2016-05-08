#!/usr/bin/env python
""" lib/cloudtrax.py

 CloudTrax class for CloudScraper

 Copyright (c) 2013 The Goulburn Group. All Rights Reserved.

 http://www.goulburngroup.com.au

 Written by Alex Ferrara <alex@receptiveit.com.au>

"""

from BeautifulSoup import BeautifulSoup
from random import choice
from lib.node import Network, Node, Client
import cStringIO
import hashlib
import hmac
import json
import logging
import requests
import string
import texttable
import time
import pygal
import Image


NONCE_CHARS = string.uppercase + string.lowercase + string.digits


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


def percentage(value, max_value):
    """Returns a float representing the percentage that
       value is of max_value"""

    return (float(value) * 100) / max_value


def make_nonce(length=32):
    """Return a randomly-generated alphanumeric string."""
    return ''.join([choice(NONCE_CHARS) for x in range(length)])


class CloudTrax:
    """CloudTrax connector class"""

    def __init__(self, config):
        self.networks = dict()
        self.nodes = dict()
        self.clients = dict()
        self.usage = [0, 0]
        self.alerting = []

        self.config = config
        self.url = self.config.get('api', 'url')
        if self.url.endswith('/'):
            self.url = self.url[:-1]

        self.key = self.config.get('api', 'key')
        self.secret = self.config.get('api', 'secret')
        self.version = self.config.get('api', 'version')

        self.collect_networks()
        self.collect_nodes()
        self.collect_clients()

    def request(self, path, method='GET', data=None):
        """Issue a request to the CloudTrax API and return the response content."""
        funcname = method.lower()
        if not hasattr(requests, funcname):
            logging.error("Invalid method type {}: No such function in 'requests'.".format(method))

        url = self.url + path

        auth = 'key={},timestamp={},nonce={}'.format(
                self.key,
                int(round(time.time())),
                make_nonce()
                )
        sigstr = auth + path
        jsondata = None
        if data is not None:
            jsondata = json.dumps(data)
            sigstr += jsondata
        sighmac = hmac.new(self.secret, sigstr, hashlib.sha256)
        sig = sighmac.hexdigest()

        headers = {
                'OpenMesh-API-Version': self.version,
                'Content-Type': 'application/json',
                'Authorization': auth,
                'Signature': sig,
                }
        logging.info("{} {}".format(method, url))
        func = getattr(requests, funcname)
        response = func(url, headers=headers, data=jsondata)
        if response.ok:
            if response.headers['content-type'] == 'application/json':
                return json.loads(response.text)
            else:
                return response.text
        else:
            logging.error("{} {} {}".format(
                response.status_code, response.reason, response.text))
            exit(response.status_code)

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

    def get_nodes(self):
        """Return a list of the collected Network objects."""
        return self.networks.values()

    def get_nodes(self):
        """Return a list of the collected Node objects."""
        return self.nodes.values()

    def get_users(self):
        """Return a list of user objects"""
        return self.users

    def get_usage(self):
        """Return network usage"""
        return self.usage

    def collect_networks(self):
        """Assemble network information from CloudTrax."""
        nets = self.request('/network/list')
        for data in nets['networks']:
            network = Network(**data)
            self.networks[network.id] = network

    def collect_nodes(self):
        """Assemble node information for each network from CloudTrax."""
        path = '/node/network/{}/list'
        for netid in self.networks.keys():
            nodes = self.request(path.format(netid))
            for key, data in nodes['nodes'].iteritems():
                node = Node(key, netid, **data)
                self.nodes[node.mac] = node

    def collect_clients(self):
        """Assemble client information for each network from CloudTrax."""
        path = '/history/network/{}/clients'
        for netid in self.networks.keys():
            self.clients[netid] = dict()
            clients = self.request(path.format(netid))
            if 'clients' not in clients:
                continue
            for key, data in clients['clients'].iteritems():
                client = Client(key, netid, **data)
                self.clients[netid][client.mac] = client

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
