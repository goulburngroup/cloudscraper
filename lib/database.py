#!/usr/bin/env python
""" lib/database.py

 Database class for CloudScraper

 Copyright (c) 2013 The Goulburn Group. All Rights Reserved.

 http://www.goulburngroup.com.au

 Written by Alex Ferrara <alex@receptiveit.com.au>

"""

import logging
from psycopg2.extensions import AsIs
import psycopg2

class Database:
    """Database connector class"""

    def __init__(self, config):

        self.backend = None

        if config['type'] == 'pgsql':
            self.backend = Postgres(config)

        else:
            raise Exception('Database type is unknown.')

    def add_records(self, nodes, users):
        """Add a node in the database"""
        return self.backend.add_records(nodes, users)

    def get_past_stats(self, interval):
        """Retrieve past statistics from the database
        
        This method retrieves the following by day,
        - Unique users
        - Total downloads in kb
        - Total uploads in kb"""
        return self.backend.get_past_stats(interval)


class Postgres:
    """Postgres database class"""

    def __init__(self, config):
        """Constructor"""

        self.schema = {'users': 'id        SERIAL primary key NOT NULL, \
                                 timestamp timestamp NOT NULL default now(), \
                                 blocked   boolean NOT NULL, \
                                 name      varchar(40), \
                                 mac       macaddr NOT NULL, \
                                 kbdown    integer NOT NULL, \
                                 kbup      integer NOT NULL, \
                                 node      macaddr NOT NULL', \
                       'nodes': 'id        SERIAL primary key NOT NULL, \
                                 timestamp timestamp NOT NULL default now(), \
                                 status    smallint NOT NULL, \
                                 name      varchar(40), \
                                 gateway   varchar(40), \
                                 mac       macaddr NOT NULL, \
                                 users     smallint NOT NULL, \
                                 gwkbdown  integer NOT NULL, \
                                 gwkbup    integer NOT NULL, \
                                 kbdown    integer NOT NULL, \
                                 kbup      integer NOT NULL, \
                                 uptime    numeric(5,2) NOT NULL, \
                                 firmware  varchar(20) NOT NULL'}

        logging.info('Connecting to database')

        self.conn = psycopg2.connect(host=config['host'],
                                database=config['database'],
                                user=config['username'],
                                password=config['password'])

        logging.info('Creating database cursor')

        self.cursor = self.conn.cursor()

        self.create_schema()


    def add_records(self, nodes, users):
        """Add a node in the Postgres database"""

        for node in nodes:
            self.cursor.execute("""INSERT INTO nodes(status,
                                                     name,
                                                     gateway,
                                                     mac,
                                                     users,
                                                     gwkbdown,
                                                     gwkbup,
                                                     kbdown,
                                                     kbup,
                                                     uptime,
                                                     firmware)
                                             VALUES (%(status)s,
                                                     %(name)s,
                                                     %(gateway_name)s,
                                                     %(mac)s,
                                                     %(users)s,
                                                     %(gw_dl)s,
                                                     %(gw_ul)s,
                                                     %(dl)s,
                                                     %(ul)s,
                                                     %(uptime_percent)s,
                                                     %(fw_version)s)""",
                                                     nodes[node].get_values())

        for user in users:
            self.cursor.execute("""INSERT INTO users(blocked,
                                                     name,
                                                     mac,
                                                     kbdown,
                                                     kbup,
                                                     node)
                                             VALUES (%(blocked)s,
                                                     %(name)s,
                                                     %(mac)s,
                                                     %(dl)s,
                                                     %(ul)s,
                                                     %(node_mac)s)""",
                                                     users[user].get_values())

        self.conn.commit()


    def get_past_stats(self, interval):
        """Postgres implementation of this method"""
        self.cursor.execute("""SELECT date(timestamp) as date,
                                      count(distinct(mac)) as users,
                                      sum(kbdown) as kbdown,
                                      sum(kbup) as kbup
                                 FROM users
                                WHERE timestamp > now() - INTERVAL %s AND
                                      timestamp < now()
                             GROUP BY date
                             ORDER BY date""", (interval, ))

        return self.cursor


    def table_exists(self, table):
        """Check if a particular table exists in the database"""

        logging.info('Checking if table "%s" exists', table)

        self.cursor.execute('SELECT * FROM information_schema.tables \
                                     WHERE table_name=%s', (table,))

        return bool(self.cursor.rowcount)


    def create_schema(self):
        """Create the current database schema if it doesn't exist"""

        for table in self.schema:
            if not self.table_exists(table):

                logging.info('Creating "%s" table', table)

                self.cursor.execute("CREATE TABLE %s (%s);",
                                   (AsIs(table), AsIs(self.schema[table])))

                self.conn.commit()
            else:
                logging.info('Table "%s" already exists', table)
