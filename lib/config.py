#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
"""lib/config.py

Configuration module for cloudscraper.

© 2016 The Goulburn Group http://www.goulburngroup.com.au, all rights reserved.

Authors:
    Alex Ferrara <alex@receptiveit.com.au>
    Brendan Jurd <direvus@gmail.com>
"""
from ConfigParser import RawConfigParser


class Config(RawConfigParser):
    def __init__(self, config_file):
        RawConfigParser.__init__(self)
        self.read(config_file)

    def get_db(self):
        """Return database config."""
        return dict(self.items('database'))

    def get_email(self):
        """Return email config"""
        return dict(self.items('email'))
