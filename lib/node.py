#!/usr/bin/env python
""" lib/node.py

 Node class for CloudScraper

 Copyright (c) 2013 The Goulburn Group. All Rights Reserved.

 http://www.goulburngroup.com.au

 Written by Alex Ferrara <alex@receptiveit.com.au>

"""


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
        return cmp(self.name, other.name)

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
        return self.node_type

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
