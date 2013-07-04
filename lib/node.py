#!/usr/bin/env python
""" lib/node.py

 Node class for CloudScraper

 Copyright (c) 2013 The Goulburn Group. All Rights Reserved.

 http://www.goulburngroup.com.au

 Written by Alex Ferrara <alex@receptiveit.com.au>

"""

NODE_STATUS = {'gw_down': '1',
               'relay_down': '2',
               'gw_up': '3',
               'relay_up': '4',
               'spare_gw_down': '5',
               'spare_down': '6',
               'spare_gw_up': '7',
               'spare_up': '8'}

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

        self.values = {'status': values[0][0],
                       'name': values[1][0],
                       'comment': values[1][-1],
                       'mac': values[2][0],
                       'ip': values[2][1],
                       'chan_24': values[3][0],
                       'chan_58': values[3][1],
                       'users': 0,
                       'dl': 0,
                       'ul': 0,
                       'gw_dl': 0,
                       'gw_ul': 0,
                       'uptime': values[6][0],
                       'uptime_percent': checkin_data[3],
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

    def is_gateway(self):
        """Return True if node is a gateway node"""
        return self.node_type == 'gateway'

    def is_relay(self):
        """Return True if node is a relay node"""
        return self.node_type == 'relay'

    def is_spare(self):
        """Return True if node is a spare node"""
        return self.node_type == 'spare'
