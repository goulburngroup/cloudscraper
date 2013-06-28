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
                       'node_name': values[1][0],
                       'node_mac': values[1][1],
                       #'device_vendor': values[2],
                       'rssi': values[3][0],
                       'rate': values[4][0],
                       'MCS': values[4][1],
                       'kb_down': int(values[5][0].replace(',', '')),
                       'kb_up': int(values[6][0].replace(',', '')),
                       'blocked': values[8][0]}

        logging.info('Creating user object for ' + self.values['mac'])

    def get_values(self):
        """Returns a bunch of values"""
        return self.values

    def get_table_row(self):
        """Returns a list of items to include in the user screen text table"""

        row = [self.values['name'] + '\n(' + self.values['mac'] + ')',
               self.values['node_name'] + '\n(' + self.values['node_mac'] + ')',
               self.values['blocked'],
               '%.2f' % (float(self.values['kb_down']) / 1000),
               '%.2f' % (float(self.values['kb_up']) / 1000)]

        return row

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
        return self.values['kb_down']

    def get_ul(self):
        """Returns an integer representing the number of kilobytes uploaded
           in the past 24hrs"""
        return self.values['kb_up']
