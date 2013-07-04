#!/usr/bin/env python
""" cloudscraper.py

 A tool to extract and archive usage information from the CloudTrax wifi mesh
dashboard (cloudtrax.com).

 Copyright (c) 2013 The Goulburn Group. All Rights Reserved.

 http://www.goulburngroup.com.au

 Written by Alex Ferrara <alex@receptiveit.com.au>


"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from lib.cloudtrax import CloudTrax
from lib.config import Config
from lib.database import Database

import argparse
import datetime
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

        email_subject = config.get_email()['subject']
        email_from = config.get_email()['from']
        email_to = config.get_email()['to']

        usage = cloudtrax.get_usage()
        today = datetime.date.today()

        email = MIMEMultipart('related')
        email['Subject'] = email_subject
        email['From'] = email_from
        email['To'] = email_to
        email.preamble = 'This is a multi-part message in MIME format.'

        # Encapsulate the plain and HTML versions of the message body
        # in an 'alternative' part, so message agents can decide which
        # they want to display.

        msg_alternative = MIMEMultipart('alternative')
        email.attach(msg_alternative)

        #msg_text = MIMEText('This is the alternative plain text message.')
        #msg_alternative.attach(msg_text)

        # TODO: This should be moved to the configuration file.
        graphs = [['node', '24hr node usage', False, 'png'],
                  ['node', '24hr internet usage', True, 'png'],
                  ['user', '24hr internet usage', True, 'png']]

        html_part = "<h2>%s</h2>" % config.get_email()['title']
        html_part += "<h3>%s</h3>" % today.strftime('%A, %d %B %Y')
        html_part += '<br>'
        html_part += "<b>Total users:</b> %s<br>" % len(users)
        html_part += '<br>'
        html_part += "<b>Total downloads:</b> %s <i>KB</i><br>" % '{:,}'.format(usage[0])
        html_part += "<b>Total uploads:</b> %s <i>KB</i><br>" % '{:,}'.format(usage[1])
        html_part += '<br>'

        for count in range(len(graphs)):
            html_part += "<img src=\"cid:image%s\">" % (count + 1)

        html_part += '<br>'
        html_part += '<pre>'
        html_part += msg
        html_part += '</pre>'

        msg_text = MIMEText(html_part, 'html')
        msg_alternative.attach(msg_text)

        counter = 1

        for graph in graphs:
            image = cloudtrax.graph(graph[0], graph[1], graph[2], graph[3])

            msg_image = MIMEImage(image)
            msg_image.add_header('Content-ID', "<image%s>" % counter)

            email.attach(msg_image)

            counter += 1

        logging.info('Connecting to SMTP server')

        mailer = smtplib.SMTP(config.get_email()['server'])

        if 'username' in config.get_email().keys():
            logging.info('Authenticating to SMTP server')
            mailer.login(config.get_email()['username'],
                         config.get_email()['password'])

        mailer.sendmail(email_from, email_to.split(), email.as_string())
        mailer.quit()

    if args.file:
        logging.info('Processing file output')
        fileout = open(args.file[0], 'w')
        fileout.write(msg)
        fileout.close()

else:
    parser.error('You must provide a network')

