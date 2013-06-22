#!/usr/bin/env python
""" lib/config.py

 Config class for CloudScraper

 Copyright (c) 2013 The Goulburn Group. All Rights Reserved.

 Written by Alex Ferrara <alex@receptiveit.com.au>

"""

import ConfigParser

class Config:
    """Cloudscraper configuration class"""

    def __init__(self, network, config_file):
        """Constructor"""
        config = ConfigParser.RawConfigParser()
        config.read(config_file)

        self.url = {'base': config.get('common', 'cloudtrax_url')}

        self.url = {'login': self.url['base'] +
                             config.get('common', 'login_page'),
                     'data': self.url['base'] +
                             config.get('common', 'data_page'),
                     'user': self.url['base'] +
                             config.get('common', 'user_page'),
                     'checkin': self.url['base'] +
                             config.get('common', 'node_checkin_page')}

        self.database = {'type': config.get('database', 'type')}

        if self.database['type'] != "none":
            self.database.update({'host': config.get('database', 'host'),
                                  'database': config.get('database',
                                                         'database'),
                                  'username': config.get('database',
                                                         'username'),
                                  'password': config.get('database',
                                                         'password')})

        self.email = {'to': config.get('email', 'to'),
                      'from': config.get('email', 'from'),
                      'subject': config.get('email', 'subject'),
                      'server': config.get('email', 'server')}

        self.network = {'name': network,
                        'username': config.get(network, 'username'),
                        'password': config.get(network, 'password')}

    def get_url(self):
        """Return url config"""
        return self.url

    def get_db(self):
        """Return database config"""
        return self.database

    def get_email(self):
        """Return email config"""
        return self.email

    def get_network(self):
        """Return network config"""
        return self.network
