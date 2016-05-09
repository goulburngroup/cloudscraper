#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
"""lib/cloudtrax.py

CloudTrax API classes for cloudscraper.

These classes implement select parts of the API described at
    https://github.com/cloudtrax/docs

The primary purpose of this module is to extract network, node, and client
information from the API, and make it available in easily digested Python
objects, for storage and/or analysis.

© 2016 The Goulburn Group http://www.goulburngroup.com.au, all rights reserved.

Authors:
    Alex Ferrara <alex@receptiveit.com.au>
    Brendan Jurd <direvus@gmail.com>
"""
from random import choice
import hashlib
import hmac
import json
import logging
import requests
import string
import time


NONCE_CHARS = string.uppercase + string.lowercase + string.digits


def make_nonce(length=32):
    """Return a randomly-generated alphanumeric string."""
    return ''.join([choice(NONCE_CHARS) for x in range(length)])


class CloudTrax(object):
    """CloudTrax API connector.

    This class offers methods to connect to the CloudTrax API and collect data
    about networks, nodes, clients and historical statistics, and stores them
    as objects, from whence they are available for reporting or insertion into
    persistent storage.
    """
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

    def request(self, path, method='GET', data=None):
        """Issue a request to the CloudTrax API and return the response content."""
        funcname = method.lower()
        if not hasattr(requests, funcname):
            logging.error("Invalid method type %s: No such function in 'requests'.", method)

        url = self.url + path

        auth = 'key={},timestamp={},nonce={}'.format(
                self.key,
                int(round(time.time())),
                make_nonce(),
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
        logging.info("%s %s", method, url)
        func = getattr(requests, funcname)
        response = func(url, headers=headers, data=jsondata)
        if response.ok:
            if response.headers['content-type'] == 'application/json':
                return json.loads(response.text)
            else:
                return response.text
        else:
            logging.error("%s %s %s",
                    response.status_code, response.reason, response.text)
            exit(response.status_code)

    def collect_networks(self):
        """Assemble network information from CloudTrax."""
        nets = self.request('/network/list')
        logging.info("Got %s networks", len(nets['networks']))
        for data in nets['networks']:
            network = Network(**data)
            self.networks[network.id] = network

    def collect_nodes(self):
        """Assemble node information for each network from CloudTrax."""
        path = '/node/network/{}/list'
        for netid in self.networks.keys():
            nodes = self.request(path.format(netid))
            logging.info("Got %s nodes for network %s.", len(nodes['nodes']), netid)
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

    def get_alerting(self):
        """Return a list of alerting nodes"""
        return self.alerting

    def get_networks(self):
        """Return a list of the collected Network objects."""
        return self.networks.values()

    def get_nodes(self):
        """Return a list of the collected Node objects."""
        return self.nodes.values()


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

        if flags is None or flags == '':
            self.flags = None
        if flags.startswith('0x'):
            self.flags = int(flags, 16)
        else:
            self.flags = flags

    def __repr__(self):
        return 'Node {}/{} {} {}'.format(
                self.network,
                self.id,
                self.mac,
                self.name)

    def __cmp__(self, other):
        return cmp(self.id, other.id)

    def add_checkin(self, timeslice, status=None):
        """Add a checkin as a (timeslice, status) tuple.

        Status may be None, in which case there was no checkin during the time
        sample.

        We maintain a frequency count of each status as checkins are added.
        """
        self.checkins.append((timeslice, status))
        if status is None:
            status = 'none'
        if status in self.status_checkins:
            self.status_checkins[status] += 1
        else:
            self.status_checkins[status] = 1

    def add_metrics(self, timeslice, speed=None):
        """Add a metrics as a (timeslice, speed) tuple."""
        self.metrics.append((timeslice, speed))

    @property
    def is_alerting(self):
        """Return whether node is in an alert state."""
        return not self.spare and self.down

    @property
    def is_gateway(self):
        return self.role == 'gateway'

    @property
    def is_relay(self):
        return self.role == 'repeater'

    @property
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
