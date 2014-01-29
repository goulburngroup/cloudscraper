#!/usr/bin/env python
""" lib/user.py

 User class for CloudScraper

 Copyright (c) 2013 The Goulburn Group. All Rights Reserved.

 http://www.goulburngroup.com.au

 Written by Alex Ferrara <alex@receptiveit.com.au>

"""

import logging

class User:
    """Wifi user class"""

    def __init__(self, values):
        """Constructor"""
        self.values = {'name': values[0][0],
                       'mac': values[0][-1],
                       'node_mac': values[1][-1],
                       #'device_vendor': values[2],
                       'rssi': values[3][0],
                       'rate': values[4][0],
                       'MCS': values[4][1],
                       'dl': int(values[5][0].replace(',', '')),
                       'ul': int(values[6][0].replace(',', '')),
                       'blocked': values[8][0],
                       'nodes': 1}

        # Node names are optional
        if len(values[1]) == 2:
            self.values['node_name'] = values[1][0]
        else:
            self.values['node_name'] = ""

        logging.info('Creating user object for ' + self.values['mac'])

    def add_usage(self, dl, ul):
        """Add client usage data to node"""
        self.values['dl'] += dl
        self.values['ul'] += ul
        self.values['nodes'] += 1

    def get_values(self):
        """Returns a bunch of values"""
        return self.values

    def get_table_row(self):
        """Returns a list of items to include in the user screen text table"""

        row = [self.values['name'] + '\n(' + self.values['mac'] + ')',
               self.values['node_name'] + '\n(' + self.values['node_mac'] + ')',
               self.values['blocked'],
               '%.2f' % (float(self.values['dl']) / 1000),
               '%.2f' % (float(self.values['ul']) / 1000)]

        return row

    def get_mac(self):
        """Returns the mac address of the client"""
        return self.values['mac']

    def get_node_name(self):
        """Returns the name of the node this client was last
           connected to"""
        return self.values['node_name']

    def get_node_mac(self):
        """Returns the mac address of the node this client was last
           connected to"""
        return self.values['node_mac']

    def get_dl(self):
        """Returns an integer representing the number of kilobytes downloaded 
           in the past 24hrs"""
        return self.values['dl']

    def get_ul(self):
        """Returns an integer representing the number of kilobytes uploaded
           in the past 24hrs"""
        return self.values['ul']
