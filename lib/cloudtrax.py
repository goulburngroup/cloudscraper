#!/usr/bin/env python
""" lib/cloudtrax.py

 CloudTrax class for CloudScraper

 Copyright (c) 2013 The Goulburn Group. All Rights Reserved.

 http://www.goulburngroup.com.au

 Written by Alex Ferrara <alex@receptiveit.com.au>

"""

from BeautifulSoup import BeautifulSoup
from random import choice
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
        self.collect_node_history()
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
                self.nodes[node.id] = node

    def collect_node_history(self):
        """Assemble 24hour node history for each network from CloudTrax."""
        path = '/history/network/{}/nodes?period=day'
        for netid in self.networks.keys():
            history = self.request(path.format(netid))
            if 'nodes' not in history:
                continue
            for nodeid, data in history['nodes'].iteritems():
                if nodeid not in self.nodes:
                    continue
                node = self.nodes[nodeid]
                if 'checkins' in data:
                    for checkin in data['checkins']:
                        node.add_checkin(**checkin)
                if 'traffic' in data:
                    node.traffic.update(data['traffic'])
                if 'metrics' in data:
                    for metrics in data['metrics']:
                        node.add_metrics(**metrics)

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


class Network(object):
    def __init__(
            self,
            id,
            name,
            node_count=None,
            new_nodes=None,
            spare_nodes=None,
            down_gateway=None,
            down_repeater=None,
            is_fcc=None,
            longitude=None,
            latitude=None,
            latest_firmware_version=None,
            ):
        self.id = id
        self.name = name
        self.node_count = node_count
        self.new_nodes = new_nodes
        self.spare_nodes = spare_nodes
        self.down_gateway = down_gateway
        self.down_repeater = down_repeater
        self.is_fcc = is_fcc
        self.location = (latitude, longitude)
        self.latest_firmware_version = latest_firmware_version

    def __cmp__(self, other):
        return cmp(self.id, other.id)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __repr__(self):
        return 'Network {} {}'.format(self.id, self.name)


class Node(object):
    def __init__(
            self,
            id,
            network,
            name=None,
            description=None,
            role=None,
            spare=None,
            down=None,
            mac=None,
            ip=None,
            lan_info=None,
            anonymous_ip=None,
            selected_gateway=None,
            gateway_path=None,
            channels=None,
            ht_modes=None,
            hardware=None,
            flags=None,
            latitude=None,
            longitude=None,
            mesh_version=None,
            connection_keeper_status=None,
            custom_sh_approved=None,
            expedite_upgrade=None,
            firmware_version=None,
            neighbors=None,
            load=None,
            memfree=None,
            upgrade_status=None,
            last_checkin=None,
            uptime=None,
            ):
        self.checkins = []
        self.metrics = []
        self.traffic = dict()
        self.status_checkins = {'none': 0}

        self.id = int(id)
        self.network = network
        self.name = name
        self.description = description
        self.role = role
        self.spare = spare
        self.down = down
        self.mac = mac
        self.ip = ip
        self.lan_info = lan_info
        self.anonymous_ip = anonymous_ip
        self.selected_gateway = selected_gateway
        self.gateway_path = gateway_path
        self.channels = channels
        self.ht_modes = ht_modes
        self.hardware = hardware
        self.flags = flags
        self.location = (latitude, longitude)
        self.mesh_version = mesh_version
        self.connection_keeper_status = connection_keeper_status
        self.custom_sh_approved = custom_sh_approved
        self.expedite_upgrade = expedite_upgrade
        self.firmware_version = firmware_version
        self.neighbors = neighbors
        self.load = load
        self.memfree = memfree
        self.upgrade_status = upgrade_status
        self.last_checkin = last_checkin
        self.uptime = uptime

    def __repr__(self):
        return 'Node {}/{} {} {}'.format(
                self.network,
                self.id,
                self.mac,
                self.name)

    def __cmp__(self, other):
        return cmp(self.id, other.id)

    def add_checkin(self, time, status=None):
        """Checkins are stored as (time, status) tuples.

        We maintain a frequency count of each status as checkins are added.
        """
        self.checkins.append((time, status))
        if status is None:
            status = 'none'
        if status in self.status_checkins:
            self.status_checkins[status] += 1
        else:
            self.status_checkins[status] = 1

    def add_metrics(self, time, speed=None):
        """Store metrics as (time, speed) tuples."""
        self.metrics.append((time, speed))

    def add_gw_usage(self, dl, ul):
        """Add internet usage to node"""
        self.values['gw_dl'] += dl
        self.values['gw_ul'] += ul

    def add_usage(self, dl, ul):
        """Add client usage data to node"""
        self.values['dl'] += dl
        self.values['ul'] += ul
        self.values['users'] += 1

        if self.is_gateway():
            self.values['gw_dl'] += dl
            self.values['gw_ul'] += ul
            return 'self'
        else:
            return self.values['gateway_name']

    def get_name(self):
        """Return the name of this node"""
        return self.values['name']

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
        return self.role

    def get_table_row(self):
        """Returns a list of items that match up to the screen text table
           for the node type"""

        if self.is_gateway():
            row = [self.values['name'] + '\n(' + self.values['mac'] + ')',
                   str(self.values['users']),
                   '%.2f' % (float(self.values['dl']) / 1000) + '\n(' +
                       '%.2f' % (float(self.values['ul']) / 1000) + ')',
                   '%.2f' % (float(self.values['gw_dl']) / 1000) + '\n(' +
                       '%.2f' % (float(self.values['gw_ul']) / 1000) + ')',
                   '%.2f' % (self.checkin_data[0]) + '%\n(' +
                       '%.2f' % (100 - self.checkin_data[0]) + '%)',
                   self.values['gateway_ip'] + '\n(' +
                       self.values['fw_version'] + ')']

        if self.is_spare():
            row = [self.values['name'] + '\n(' + self.values['mac'] + ')',
                   str(self.values['users']),
                   '%.2f' % (float(self.values['dl']) / 1000) + '\n(' +
                       '%.2f' % (float(self.values['ul']) / 1000) + ')',
                   '%.2f' % (self.checkin_data[0]) + '%\n(' +
                       '%.2f' % (100 - self.checkin_data[0]) + '%)',
                   self.values['gateway_ip'] + '\n(' +
                       self.values['fw_version'] + ')']

        elif self.is_relay():
            row = [self.values['name'] + '\n(' + self.values['mac'] + ')',
                   str(self.values['users']),
                   '%.2f' % (float(self.values['dl']) / 1000) + '\n(' +
                       '%.2f' % (float(self.values['ul']) / 1000) + ')',
                   self.values['gateway_name'] + '\n(' +
                       self.values['fw_version'] + ')',
                   '%.2f' % (self.checkin_data[1]) + '%\n(' +
                       '%.2f' % (100 - self.checkin_data[1]) + '%)',
                   self.values['latency'] + 'ms\n(' + self.values['hops'] + ')']

        return row

    def get_values(self):
        """Return all values of this node"""
        return self.values

    def get_gw_usage(self):
        """Return the internet usage for this node"""
        return (self.values['gw_dl'], self.values['gw_ul'])

    def get_usage(self):
        """Return the data transfer for this node"""
        return (self.values['dl'], self.values['ul'])

    def is_alerting(self):
        """Return True if node is altering"""
        return not self.is_spare() and self.checkin_data[2] > 0

    def is_gateway(self):
        return self.role == 'gateway'

    def is_relay(self):
        return self.role == 'repeater'

    def is_spare(self):
        return self.spare


class Client(object):
    def __init__(
            self,
            mac,
            network,
            cid=None,
            band=None,
            bitrate=None,
            channel_width=None,
            link=None,
            mcs=None,
            signal=None,
            traffic=None,
            wifi_mode=None,
            last_name=None,
            last_node=None,
            last_seen=None,
            name=None,
            name_override=None,
            blocked=None,
            os=None,
            os_version=None,
            ):
        self.mac = mac
        self.network = network
        self.cid = cid
        self.band = band
        self.bitrate = bitrate
        self.channel_width = channel_width
        self.link = link
        self.mcs = mcs
        self.signal = signal
        self.traffic = traffic
        self.wifi_mode = wifi_mode
        self.last_name = last_name
        self.last_node = last_node
        self.last_seen = last_seen
        self.name = name
        self.name_override = name_override
        self.blocked = blocked
        self.os = os
        self.os_version = os_version

    def __repr__(self):
        return 'Client {}/{}'.format(
                self.network,
                self.mac)

    def __unicode__(self):
        return self.name

    def __str__(self):
        return unicode(self).encode('utf-8')

    def get_total_traffic(self):
        """Return a 2-tuple of total bytes down and up."""
        down = 0
        up = 0
        if self.traffic:
            for ssid in self.traffic.values():
                down += ssid['bdown']
                up += ssid['bup']
        return (down, up)

    def get_total_download(self):
        return self.get_total_traffic()[0]

    def get_total_upload(self):
        return self.get_total_traffic()[1]
