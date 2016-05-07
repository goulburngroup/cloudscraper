#!/usr/bin/env python
""" lib/config.py

 Config class for CloudScraper

 Copyright (c) 2013 The Goulburn Group. All Rights Reserved.

 http://www.goulburngroup.com.au

 Written by Alex Ferrara <alex@receptiveit.com.au>

"""

import ConfigParser

class Config:
    """Cloudscraper configuration class"""

    def __init__(self, config_file):
        """Constructor"""
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

        self.network = {'name': self.config.get('network', 'username'),
                        'username': self.config.get('network', 'username'),
                        'password': self.config.get('network', 'password'),
                        'recurse': self.config.getboolean('network', 'recurse'),
                        'networks': [self.config.get('network', 'name')]}


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

