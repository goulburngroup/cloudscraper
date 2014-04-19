#!/usr/bin/env python
""" lib/network.py

 Network class for CloudScraper

 Copyright (c) 2013 The Goulburn Group. All Rights Reserved.

 http://www.goulburngroup.com.au

 Written by Alex Ferrara <alex@receptiveit.com.au>

"""

class Network:
    """Cloudscraper network class"""

    def __init__(self):
        """Constructor"""
        self.var = "blah"

    def get_settings(self, node_name):
        """Return network quota config"""
        if not self.config.has_section(node_name):
            node_name = 'net_default'

        return dict(self.config.items(node_name))

    def get_var(self):
        """Return var config"""
        return self.var
