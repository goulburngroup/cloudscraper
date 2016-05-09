#!/usr/bin/env python
# vim: set fileencoding=utf-8 :
"""lib/cloudtrax.py

Database abstraction module for cloudscraper.

© 2016 The Goulburn Group http://www.goulburngroup.com.au, all rights reserved.

Authors:
    Alex Ferrara <alex@receptiveit.com.au>
    Brendan Jurd <direvus@gmail.com>
"""
from psycopg2.extensions import AsIs
import psycopg2
import logging
import json


def get_connection(dbtype, **kwargs):
    """Return a Database subclass instance for the given type."""
    if (dbtype == 'pgsql' or
            dbtype.startswith('postgres') or
            dbtype.startswith('psycopg')):
        return Postgres(**kwargs)
    raise ValueError("Database type {} not recognised.".format(dbtype))


class Database(object):
    def store_data(self, cloudtrax):
        """Store data from a CloudTrax instance in the database."""
        raise NotImplemented()


class Postgres(Database):
    def __init__(self, database,
            host=None, port=5432,
            username=None, password=None, schema='public', **kwargs):
        self.conn = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password)
        self.conn.autocommit = True
        self.schema = schema
        with self.conn.cursor() as cur:
            cur.execute('SET search_path TO {};'.format(self.schema))
        self.create_schema()

    def store_data(self, cloudtrax):
        """Store data from a CloudTrax instance in the database."""
        with self.conn.cursor() as cur:
            for net in cloudtrax.get_networks():
                params = {
                    'id': net.id,
                    'name': net.name,
                    'node_count': net.node_count,
                    'new_nodes': net.new_nodes,
                    'spare_nodes': net.spare_nodes,
                    'down_gateway': net.down_gateway,
                    'down_repeater': net.down_repeater,
                    'is_fcc': net.is_fcc,
                    'latitude': net.location[0],
                    'longitude': net.location[1],
                    'latest_firmware_version': net.latest_firmware_version,
                    }
                cur.execute(self.NETWORK_UPDATE_SQL, params)
                if cur.rowcount == 0:
                    cur.execute(self.NETWORK_INSERT_SQL, params)
                cur.execute(self.NETWORK_LOG_SQL, (net.id,))
            for node in cloudtrax.get_nodes():
                params = {
                    'id': node.id,
                    'network': node.network,
                    'name': node.name,
                    'description': node.description,
                    'role': node.role,
                    'spare': node.spare,
                    'down': node.down,
                    'mac': node.mac,
                    'ip': node.ip,
                    'lan_info': json.dumps(node.lan_info),
                    'anonymous_ip': node.anonymous_ip,
                    'selected_gateway': json.dumps(node.selected_gateway),
                    'gateway_path': json.dumps(node.gateway_path),
                    'channels': json.dumps(node.channels),
                    'ht_modes': json.dumps(node.ht_modes),
                    'hardware': node.hardware,
                    'flags': node.flags,
                    'latitude': node.location[0],
                    'longitude': node.location[1],
                    'mesh_version': node.mesh_version,
                    'connection_keeper_status': node.connection_keeper_status,
                    'custom_sh_approved': node.custom_sh_approved,
                    'expedite_upgrade': node.expedite_upgrade,
                    'firmware_version': node.firmware_version,
                    'neighbors': json.dumps(node.neighbors),
                    'load': node.load,
                    'memfree': node.memfree,
                    'upgrade_status': node.upgrade_status,
                    'last_checkin': node.last_checkin,
                    'uptime': node.uptime,
                    }
                cur.execute(self.NODE_UPDATE_SQL, params)
                if cur.rowcount == 0:
                    cur.execute(self.NODE_INSERT_SQL, params)
                cur.execute(self.NODE_LOG_SQL, (node.id,))

    def table_exists(self, table):
        """Return whether the given table exists in the database."""
        with self.conn.cursor() as cur:
            cur.execute(self.CHECK_TABLE_SQL, (self.schema, table))
            return (cur.rowcount > 0)

    def create_schema(self):
        """Create missing tables in the database schema."""
        for table, definition in self.TABLES:
            if not self.table_exists(table):
                logging.info("Table '%s' is absent, creating it ...", table)
                with self.conn.cursor() as cur:
                    cur.execute("CREATE TABLE {} ({});".format(
                        table, definition))

    CHECK_TABLE_SQL = (
            'SELECT table_name '
            'FROM information_schema.tables '
            'WHERE table_schema = %s AND table_name = %s;')

    NETWORK_LOG_SQL = (
            'INSERT INTO network_log ('
            '    id, name, node_count, new_nodes, spare_nodes, '
            '    down_gateway, down_repeater, is_fcc, '
            '    latitude, longitude, latest_firmware_version) '
            'SELECT '
            '    id, name, node_count, new_nodes, spare_nodes, '
            '    down_gateway, down_repeater, is_fcc, '
            '    latitude, longitude, latest_firmware_version '
            'FROM network '
            'WHERE id = %s;')
    NETWORK_UPDATE_SQL = (
            'UPDATE network '
            'SET '
            '    name = %(name)s, '
            '    node_count = %(node_count)s, '
            '    new_nodes = %(new_nodes)s, '
            '    spare_nodes = %(spare_nodes)s, '
            '    down_gateway = %(down_gateway)s, '
            '    down_repeater = %(down_repeater)s, '
            '    is_fcc = %(is_fcc)s, '
            '    latitude = %(latitude)s, '
            '    longitude = %(longitude)s, '
            '    latest_firmware_version = %(latest_firmware_version)s '
            'WHERE id = %(id)s;')
    NETWORK_INSERT_SQL = (
            'INSERT INTO network ('
            '    id, name, node_count, new_nodes, spare_nodes, '
            '    down_gateway, down_repeater, is_fcc, '
            '    latitude, longitude, latest_firmware_version) '
            'VALUES ('
            '    %(id)s, %(name)s, %(node_count)s, %(new_nodes)s, '
            '    %(spare_nodes)s, %(down_gateway)s, %(down_repeater)s, '
            '    %(is_fcc)s, %(latitude)s, %(longitude)s, '
            '    %(latest_firmware_version)s);')

    NODE_LOG_SQL = (
            'INSERT INTO node_log ('
            '    id, network, name, description, role, spare, down, '
            '    mac, ip, lan_info, anonymous_ip, selected_gateway, '
            '    gateway_path, channels, ht_modes, hardware, flags, '
            '    latitude, longitude, mesh_version, connection_keeper_status, '
            '    custom_sh_approved, expedite_upgrade, firmware_version, '
            '    neighbors, load, memfree, upgrade_status, last_checkin, '
            '    uptime) '
            'SELECT '
            '    id, network, name, description, role, spare, down, '
            '    mac, ip, lan_info, anonymous_ip, selected_gateway, '
            '    gateway_path, channels, ht_modes, hardware, flags, '
            '    latitude, longitude, mesh_version, connection_keeper_status, '
            '    custom_sh_approved, expedite_upgrade, firmware_version, '
            '    neighbors, load, memfree, upgrade_status, last_checkin, '
            '    uptime '
            'FROM node '
            'WHERE id = %s;')
    NODE_UPDATE_SQL = (
            'UPDATE node '
            'SET '
            '    network = %(network)s, '
            '    name = %(name)s, '
            '    description = %(description)s, '
            '    role = %(role)s, '
            '    spare = %(spare)s, '
            '    down = %(down)s, '
            '    mac = %(mac)s, '
            '    ip = %(ip)s, '
            '    lan_info = %(lan_info)s, '
            '    anonymous_ip = %(anonymous_ip)s, '
            '    selected_gateway = %(selected_gateway)s, '
            '    gateway_path = %(gateway_path)s, '
            '    channels = %(channels)s, '
            '    ht_modes = %(ht_modes)s, '
            '    hardware = %(hardware)s, '
            '    flags = %(flags)s, '
            '    latitude = %(latitude)s, '
            '    longitude = %(longitude)s, '
            '    mesh_version = %(mesh_version)s, '
            '    connection_keeper_status = %(connection_keeper_status)s, '
            '    custom_sh_approved = %(custom_sh_approved)s, '
            '    expedite_upgrade = %(expedite_upgrade)s, '
            '    firmware_version = %(firmware_version)s, '
            '    neighbors = %(neighbors)s, '
            '    load = %(load)s, '
            '    memfree = %(memfree)s, '
            '    upgrade_status = %(upgrade_status)s, '
            '    last_checkin = %(last_checkin)s, '
            '    uptime = %(uptime)s '
            'WHERE id = %(id)s;')
    NODE_INSERT_SQL = (
            'INSERT INTO node ('
            '    id, network, name, description, role, spare, down, '
            '    mac, ip, lan_info, anonymous_ip, selected_gateway, '
            '    gateway_path, channels, ht_modes, hardware, flags, '
            '    latitude, longitude, mesh_version, connection_keeper_status, '
            '    custom_sh_approved, expedite_upgrade, firmware_version, '
            '    neighbors, load, memfree, upgrade_status, last_checkin, '
            '    uptime) '
            'VALUES ('
            '    %(id)s, %(network)s, %(name)s, %(description)s, %(role)s, '
            '    %(spare)s, %(down)s, %(mac)s, %(ip)s, %(lan_info)s, '
            '    %(anonymous_ip)s, %(selected_gateway)s, %(gateway_path)s, '
            '    %(channels)s, %(ht_modes)s, %(hardware)s, %(flags)s, '
            '    %(latitude)s, %(longitude)s, %(mesh_version)s, '
            '    %(connection_keeper_status)s, %(custom_sh_approved)s, '
            '    %(expedite_upgrade)s, %(firmware_version)s, %(neighbors)s, '
            '    %(load)s, %(memfree)s, %(upgrade_status)s, %(last_checkin)s, '
            '    %(uptime)s);')

    TABLES = [
            ('network',
                'id int PRIMARY KEY, '
                'name text, '
                'node_count int, '
                'new_nodes int, '
                'spare_nodes int, '
                'down_gateway int, '
                'down_repeater int, '
                'is_fcc bool, '
                'longitude numeric, '
                'latitude numeric, '
                'latest_firmware_version text'),
            ('network_log',
                'time timestamptz NOT NULL DEFAULT now(), '
                'id int NOT NULL, '
                'name text, '
                'node_count int, '
                'new_nodes int, '
                'spare_nodes int, '
                'down_gateway int, '
                'down_repeater int, '
                'is_fcc bool, '
                'longitude numeric, '
                'latitude numeric, '
                'latest_firmware_version text, '
                'PRIMARY KEY (time, id)'),
            ('node',
                'id int PRIMARY KEY, '
                'network int, '
                'name text, '
                'description text, '
                'role text, '
                'spare bool, '
                'down bool, '
                'mac macaddr, '
                'ip inet, '
                'lan_info text, '
                'anonymous_ip bool, '
                'selected_gateway text, '
                'gateway_path text, '
                'channels text, '
                'ht_modes text, '
                'hardware text, '
                'flags int, '
                'latitude numeric, '
                'longitude numeric, '
                'mesh_version text, '
                'connection_keeper_status text, '
                'custom_sh_approved bool, '
                'expedite_upgrade bool, '
                'firmware_version text, '
                'neighbors text, '
                'load text, '
                'memfree int, '
                'upgrade_status text, '
                'last_checkin timestamptz, '
                'uptime text'),
            ('node_log',
                'time timestamptz NOT NULL DEFAULT now(), '
                'id int, '
                'network int, '
                'name text, '
                'description text, '
                'role text, '
                'spare bool, '
                'down bool, '
                'mac macaddr, '
                'ip inet, '
                'lan_info text, '
                'anonymous_ip bool, '
                'selected_gateway text, '
                'gateway_path text, '
                'channels text, '
                'ht_modes text, '
                'hardware text, '
                'flags int, '
                'latitude numeric, '
                'longitude numeric, '
                'mesh_version text, '
                'connection_keeper_status text, '
                'custom_sh_approved bool, '
                'expedite_upgrade bool, '
                'firmware_version text, '
                'neighbors text, '
                'load text, '
                'memfree int, '
                'upgrade_status text, '
                'last_checkin timestamptz, '
                'uptime text, '
                'PRIMARY KEY (time, id)'),
            ]

