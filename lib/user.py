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
