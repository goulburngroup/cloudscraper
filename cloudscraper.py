#!/usr/bin/env python
""" cloudscraper.py

 A tool to extract and archive usage information from the CloudTrax wifi mesh
dashboard (cloudtrax.com).

 Copyright (c) 2013 The Goulburn Group. All Rights Reserved.

 http://www.goulburngroup.com.au

 Written by Alex Ferrara <alex@receptiveit.com.au>


"""

from email.mime.text import MIMEText
from lib.cloudtrax import CloudTrax
from lib.config import Config
from lib.database import Database

import argparse
import logging
import smtplib

CONFIG_FILE = '/opt/cloudscraper/cloudscraper.conf'

parser = argparse.ArgumentParser(description = 'Statistics scraper for the ' +
                                               'CloudTrax controller')
parser.add_argument('-d', '--database',
                    action = 'store_true',
                    default = False, 
                    help = 'Store the output to a database')
parser.add_argument('-e', '--email',
                    action = 'store_true',
                    default = False, 
                    help = 'Email the output')
parser.add_argument('-f', '--file',
                    nargs = 1, 
                    help = 'Store the output to a file')
parser.add_argument('-n', '--network',
                    nargs = 1, 
                    help = 'The wifi network name on CloudTrax')
parser.add_argument('-s', '--screen',
                    action = 'store_true',
                    default = False, 
                    help = 'Display the output to stdout')
parser.add_argument('-v', '--verbose',
                    action = 'store_true',
                    default = False, 
                    help = 'Be Verbose')
args = parser.parse_args()

# Set up logging
if args.verbose:
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')
else:
    logging.basicConfig(level=logging.WARNING,
                        format='%(asctime)s - %(levelname)s - %(message)s')

if args.network:
    # We need to know to output the result
    if not (args.database or args.email or args.file or args.screen):
        parser.error('No output defined')

    config = Config(args.network[0], CONFIG_FILE)

    cloudtrax = CloudTrax(config)
    nodes = cloudtrax.get_nodes()
    users = cloudtrax.get_users()

    msg = ""
    msg += cloudtrax.report_summary()
    msg += cloudtrax.report_nodes()
    msg += cloudtrax.report_users()

    if args.database:
        logging.info('Processing database output')
        database = Database(config.get_db())

        database.add_records(nodes, users)

    if args.screen:
        logging.info('Processing screen output')
        print msg

    if args.email:
        logging.info('Processing email output')
        email = MIMEText('<pre>' + msg + '</pre>', 'html')
        email['Subject'] = config.get_email()['subject']
        email['From'] = config.get_email()['from']
        email['To'] = config.get_email()['to']

        # Send the message via our own SMTP server, but don't include the
        # envelope header.
        mailer = smtplib.SMTP(config.get_email()['server'])
        mailer.sendmail(config.get_email()['from'],
                        config.get_email()['to'].split(),
                        email.as_string())
        mailer.quit()

    if args.file:
        logging.info('Processing file output')
        fileout = open(args.file[0], 'w')
        fileout.write(msg)
        fileout.close()

else:
    parser.error('You must provide a network')

