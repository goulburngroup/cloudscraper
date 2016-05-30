#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
"""cloudscraper.py

A command-line tool to extract, store and analyse usage information from the
CloudTrax wifi mesh API http://api.cloudtrax.com.

© 2016 The Goulburn Group http://www.goulburngroup.com.au, all rights reserved.

Authors:
    Alex Ferrara <alex@receptiveit.com.au>
    Brendan Jurd <direvus@gmail.com>
"""
from lib.cloudtrax import CloudTrax
from lib.config import Config
from lib.database import get_connection
from lib.mail import Email

import argparse
import datetime
import logging
import pygal


LOGFORMAT = '%(asctime)s - %(levelname)s - %(message)s'


parser = argparse.ArgumentParser(description='CloudTrax API scraper')
parser.add_argument(
        '-c', '--config',
        nargs=1,
        metavar='filename',
        default='/opt/cloudscraper/cloudscraper.conf',
        help='configuration filename')
parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='increase verbosity')
parser.add_argument(
        '-n', '--no-history',
        action='store_true',
        help='do not collect historical data')
args = parser.parse_args()

if args.verbose > 1:
    loglevel = logging.DEBUG
elif args.verbose > 0:
    loglevel = logging.INFO
else:
    loglevel = logging.WARNING

logging.basicConfig(level=loglevel, format=LOGFORMAT)

config = Config(args.config)
cloudtrax = CloudTrax(config)
cloudtrax.collect_networks()
cloudtrax.collect_nodes()
if not args.no_history:
    cloudtrax.collect_node_history()
    cloudtrax.collect_clients()
dbconf = config.get_db()
database = get_connection(dbconf['type'], **dbconf)
database.store_data(cloudtrax)
