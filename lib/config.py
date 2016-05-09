#!/usr/bin/env python
"""lib/config.py

Configuration module for cloudscraper.

© 2016 The Goulburn Group http://www.goulburngroup.com.au, all rights reserved.

Authors:
    Alex Ferrara <alex@receptiveit.com.au>
    Brendan Jurd <direvus@gmail.com>
"""
import ConfigParser


class Config:
    def __init__(self, config_file):
        self.config = ConfigParser.RawConfigParser()
        self.config.read(config_file)

        self.database = {'type': self.config.get('database', 'type')}

        if self.database['type'] != "none":
            self.database.update({'host': self.config.get('database', 'host'),
                                  'database': self.config.get('database',
                                                         'database'),
                                  'username': self.config.get('database',
                                                         'username'),
                                  'password': self.config.get('database',
                                                         'password')})

        self.email = dict(self.config.items('email'))

    def get(self, section, key):
        return self.config.get(section, key)

    def get_db(self):
        """Return database config"""
        return self.database

    def get_email(self):
        """Return email config"""
        return self.email

    def get_network(self):
        """Return network config"""
        return self.network

    def get_node_settings(self, node_name):
        """Return network quota config"""
        if not self.config.has_section(node_name):
            node_name = 'net_default'

        return dict(self.config.items(node_name))

    def set_network(self, network):
        """Set a single network"""
        self.network['name'] = network
        self.network['recurse'] = False

