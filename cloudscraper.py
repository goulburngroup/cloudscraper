#!/usr/bin/env python
""" cloudscraper.py

 A tool to extract and archive usage information from the CloudTrax wifi mesh
dashboard (cloudtrax.com).

 Copyright (c) 2013 The Goulburn Group. All Rights Reserved.

 http://www.goulburngroup.com.au

 Written by Alex Ferrara <alex@receptiveit.com.au>


"""

from lib.cloudtrax import CloudTrax
from lib.config import Config
from lib.database import Database
from lib.mail import Email

import argparse
import datetime
import logging
import pygal

CONFIG_FILE = '/opt/cloudscraper/cloudscraper.conf'

parser = argparse.ArgumentParser(description = 'Statistics scraper for the ' +
                                               'CloudTrax controller')
parser.add_argument('-c', '--scrape',
                    action = 'store_true',
                    default = False, 
                    help = 'Scrape (collect) data from CloudTrax')
parser.add_argument('-d', '--database',
                    action = 'store_true',
                    default = False, 
                    help = 'Store the output to a database')
parser.add_argument('-e', '--email',
                    action = 'store_true',
                    default = False, 
                    help = 'Email the output')
parser.add_argument('-n', '--network',
                    nargs = 1, 
                    help = 'Force one network with no recursion')
parser.add_argument('-r', '--report',
                    nargs = 1, 
                    help = 'Produce a report from database statistics [day|month|year]')
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

if args.scrape and args.report:
    #TODO: We might be able to do this later...
    parser.error('You cannot scrape data and report history at the same time')

# Parse configuration file
config = Config(CONFIG_FILE)

if args.network:
    config.set_network(args.network[0])

if args.scrape:
    # We need to know to output the result
    if not (args.database or args.email or args.screen):
        parser.error('No output defined')

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

        email = Email(config.get_email())

        usage = cloudtrax.get_usage()
        today = datetime.date.today()

        # TODO: This should be moved to the configuration file.
        graphs = [['node', '24hr node usage', False, 'png'],
                  ['node', '24hr internet usage', True, 'png'],
                  ['user', '24hr internet usage', True, 'png']]

        html_part = "<h2>%s</h2>\n" % config.get_email()['title']
        html_part += "<h3>%s</h3>\n" % today.strftime('%A, %d %B %Y')
        html_part += '<br>\n'
        html_part += "<b>Total users:</b> %s<br>\n" % len(users)
        html_part += '<br>\n'
        html_part += "<b>Total downloads:</b> %s <i>KB</i><br>\n" % '{:,}'.format(usage[0])
        html_part += "<b>Total uploads:</b> %s <i>KB</i><br>\n" % '{:,}'.format(usage[1])
        html_part += '<br>\n'

        for count in range(len(graphs)):
            html_part += "<img src=\"cid:image%s\">" % (count + 1)

        html_part += '<br>'
        html_part += '<pre>'
        html_part += msg
        html_part += '</pre>'

        email.attach_html(html_part)

        for graph in graphs:
            image = cloudtrax.graph(graph[0], graph[1], graph[2], graph[3])
            email.attach_image(image)

        email.send()

elif args.report:
    logging.info('Producing report - %s' % args.report[0])

    database = Database(config.get_db())

    if args.report[0] == 'year':
        interval = '1 year'
    elif args.report[0] == 'month':
        interval = '1 month'
    else:
        interval = '1 day'

    msg = "<h2>Users by day</h2>"

    for count in range(1):
        msg += "<img src=\"cid:image%s\">" % (count + 1)

    msg += "<pre>"

    days = []
    users = []
    dlkb = []
    ulkb = []

    for record in database.get_past_stats(interval):
        msg += "%s - %s users - %s kb downloaded - %s kb uploaded\n" % record
        days.append("%s/%s" % (record[0].day, record[0].month))
        users.append(record[1])
        dlkb.append(record[2])
        ulkb.append(record[3])

    msg += "</pre>"

    if args.email:
        email = Email(config.get_email())
        email.attach_html(msg)

        # Create usage graph
        line_chart = pygal.Line()
        line_chart.title = 'Users by day'
        line_chart.x_labels = map(str, days)
        line_chart.add('Users', users)

        email.attach_image(line_chart.render_to_png())
        email.send()
else:
    parser.error('You must either scrape data or produce a report')

