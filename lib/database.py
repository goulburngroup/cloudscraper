#!/usr/bin/env python
""" lib/database.py

 Database class for CloudScraper

 Copyright (c) 2013 The Goulburn Group. All Rights Reserved.

 Written by Alex Ferrara <alex@receptiveit.com.au>

"""

from psycopg2.extensions import AsIs
import logging
import psycopg2

class Database:
    """Database connector class"""

    def __init__(self, config):
        """Constructor"""

        self.schema = {'users': 'id        SERIAL primary key NOT NULL, \
                                 timestamp timestamp NOT NULL default now(), \
                                 blocked   boolean NOT NULL, \
                                 name      varchar(40), \
                                 kbdown    integer NOT NULL, \
                                 kbup      integer NOT NULL, \
                                 node      macaddr NOT NULL, \
                                 mac       macaddr NOT NULL',
                       'nodes': 'id        SERIAL primary key NOT NULL, \
                                 timestamp timestamp NOT NULL default now(), \
                                 type      smallint NOT NULL, \
                                 name      varchar(40), \
                                 mac       macaddr NOT NULL, \
                                 mac       macaddr NOT NULL, \
                                 mac       macaddr NOT NULL, \
                                 mac       macaddr NOT NULL, \
                                 firmware  varchar(20) NOT NULL'}

        logging.info('Connecting to database')

        self.conn = psycopg2.connect(host=config['host'],
                                database=config['database'],
                                user=config['username'],
                                password=config['password'])

        logging.info('Creating database cursor')

        self.cursor = self.conn.cursor()

        self.create_schema()


    def table_exists(self, table):
        """Check if a particular table exists in the database"""

        logging.info('Checking if table "%s" exists', table)

        self.cursor.execute('SELECT * FROM information_schema.tables WHERE table_name=%s', (table,))

        return bool(self.cursor.rowcount)

    def create_schema(self):
        """Create the current database schema if it doesn't exist"""

        for table in self.schema:
            if not self.table_exists(table):

                logging.info('Creating "%s" table', table)

                self.cursor.execute("CREATE TABLE %s (%s);", (AsIs(table), AsIs(self.schema[table])))

                self.conn.commit()
            else:
                logging.info('Table "users" already exists')
