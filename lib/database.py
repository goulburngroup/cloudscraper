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
                logging.info("Storing data for %r", net)
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
                logging.info("Storing data for %r", node)
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
                    'traffic': json.dumps(node.traffic),
                    'download': node.total_download,
                    'upload': node.total_upload,
                    }
                cur.execute(self.NODE_UPDATE_SQL, params)
                if cur.rowcount == 0:
                    cur.execute(self.NODE_INSERT_SQL, params)
                cur.execute(self.NODE_LOG_SQL, (node.id,))

                for time, values in node.checkins.iteritems():
                    params = {
                        'node': node.id,
                        'time': time,
                        'status': values['status'],
                        'speed': values['speed'],
                        }
                    cur.execute(self.CHECKIN_UPDATE_SQL, params)
                    if cur.rowcount == 0:
                        cur.execute(self.CHECKIN_INSERT_SQL, params)
            for client in cloudtrax.get_clients():
                logging.info("Storing data for %r", client)
                params = {
                    'mac': client.mac,
                    'network': client.network,
                    'cid': client.cid,
                    'band': client.band,
                    'bitrate': json.dumps(client.bitrate),
                    'channel_width': client.channel_width,
                    'link': client.link,
                    'mcs': json.dumps(client.mcs),
                    'signal': json.dumps(client.signal),
                    'traffic': json.dumps(client.traffic),
                    'download': client.total_download,
                    'upload': client.total_upload,
                    'wifi_mode': client.wifi_mode,
                    'last_name': client.last_name,
                    'last_node': client.last_node,
                    'last_seen': client.last_seen,
                    'name': client.name,
                    'name_override': client.name_override,
                    'blocked': client.blocked,
                    'os': client.os,
                    'os_version': client.os_version,
                    }
                cur.execute(self.CLIENT_UPDATE_SQL, params)
                if cur.rowcount == 0:
                    cur.execute(self.CLIENT_INSERT_SQL, params)
                cur.execute(self.CLIENT_LOG_SQL, {
                    'mac': client.mac,
                    'network': client.network})

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
            '    uptime, traffic, download, upload) '
            'SELECT '
            '    id, network, name, description, role, spare, down, '
            '    mac, ip, lan_info, anonymous_ip, selected_gateway, '
            '    gateway_path, channels, ht_modes, hardware, flags, '
            '    latitude, longitude, mesh_version, connection_keeper_status, '
            '    custom_sh_approved, expedite_upgrade, firmware_version, '
            '    neighbors, load, memfree, upgrade_status, last_checkin, '
            '    uptime, traffic, download, upload '
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
            '    uptime = %(uptime)s, '
            '    traffic = %(traffic)s, '
            '    download = %(download)s, '
            '    upload = %(upload)s '
            'WHERE id = %(id)s;')
    NODE_INSERT_SQL = (
            'INSERT INTO node ('
            '    id, network, name, description, role, spare, down, '
            '    mac, ip, lan_info, anonymous_ip, selected_gateway, '
            '    gateway_path, channels, ht_modes, hardware, flags, '
            '    latitude, longitude, mesh_version, connection_keeper_status, '
            '    custom_sh_approved, expedite_upgrade, firmware_version, '
            '    neighbors, load, memfree, upgrade_status, last_checkin, '
            '    uptime, traffic, download, upload) '
            'VALUES ('
            '    %(id)s, %(network)s, %(name)s, %(description)s, %(role)s, '
            '    %(spare)s, %(down)s, %(mac)s, %(ip)s, %(lan_info)s, '
            '    %(anonymous_ip)s, %(selected_gateway)s, %(gateway_path)s, '
            '    %(channels)s, %(ht_modes)s, %(hardware)s, %(flags)s, '
            '    %(latitude)s, %(longitude)s, %(mesh_version)s, '
            '    %(connection_keeper_status)s, %(custom_sh_approved)s, '
            '    %(expedite_upgrade)s, %(firmware_version)s, %(neighbors)s, '
            '    %(load)s, %(memfree)s, %(upgrade_status)s, %(last_checkin)s, '
            '    %(uptime)s, %(traffic)s, %(download)s, %(upload)s);')

    CLIENT_LOG_SQL = (
            'INSERT INTO client_log ('
            '    mac, network, cid, band, bitrate, channel_width, link, mcs, '
            '    signal, traffic, download, upload, wifi_mode, last_name, '
            '    last_node, last_seen, name, name_override, blocked, os, '
            '    os_version)'
            'SELECT '
            '    mac, network, cid, band, bitrate, channel_width, link, mcs, '
            '    signal, traffic, download, upload, wifi_mode, last_name, '
            '    last_node, last_seen, name, name_override, blocked, os, '
            '    os_version '
            'FROM client '
            'WHERE mac = %(mac)s AND network = %(network)s;')
    CLIENT_UPDATE_SQL = (
            'UPDATE client '
            'SET '
            '    cid = %(cid)s, '
            '    band = %(band)s, '
            '    bitrate = %(bitrate)s, '
            '    channel_width = %(channel_width)s, '
            '    link = %(link)s, '
            '    mcs = %(mcs)s, '
            '    signal = %(signal)s, '
            '    traffic = %(traffic)s, '
            '    download = %(download)s, '
            '    upload = %(upload)s, '
            '    wifi_mode = %(wifi_mode)s, '
            '    last_name = %(last_name)s, '
            '    last_node = %(last_node)s, '
            '    last_seen = %(last_seen)s, '
            '    name = %(name)s, '
            '    name_override = %(name_override)s, '
            '    blocked = %(blocked)s, '
            '    os = %(os)s, '
            '    os_version = %(os_version)s '
            'WHERE mac = %(mac)s AND network = %(network)s;')
    CLIENT_INSERT_SQL = (
            'INSERT INTO client ('
            '    mac, network, cid, band, bitrate, channel_width, link, mcs, '
            '    signal, traffic, download, upload, wifi_mode, last_name, '
            '    last_node, last_seen, name, name_override, blocked, os, '
            '    os_version) '
            'VALUES ('
            '    %(mac)s, %(network)s, %(cid)s, %(band)s, %(bitrate)s, '
            '    %(channel_width)s, %(link)s, %(mcs)s, %(signal)s, '
            '    %(traffic)s, %(download)s, %(upload)s, %(wifi_mode)s, '
            '    %(last_name)s, %(last_node)s, %(last_seen)s, %(name)s, '
            '    %(name_override)s, %(blocked)s, %(os)s, %(os_version)s);')

    CHECKIN_UPDATE_SQL = (
            'UPDATE node_checkin '
            'SET status = %(status)s, speed = %(speed)s '
            'WHERE node = %(node)s AND time = %(time)s;')
    CHECKIN_INSERT_SQL = (
            'INSERT INTO node_checkin (node, time, status, speed) '
            'VALUES (%(node)s, %(time)s, %(status)s, %(speed)s);')

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
                'uptime text, '
                'traffic text, '
                'download int, '
                'upload int'),
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
                'traffic text, '
                'download int, '
                'upload int, '
                'PRIMARY KEY (time, id)'),
            ('client',
                'mac macaddr, '
                'network int, '
                'cid text, '
                'band text, '
                'bitrate text, '
                'channel_width int, '
                'link text, '
                'mcs text, '
                'signal text, '
                'traffic text, '
                'download int, '
                'upload int, '
                'wifi_mode text, '
                'last_name text, '
                'last_node macaddr, '
                'last_seen timestamptz, '
                'name text, '
                'name_override text, '
                'blocked bool, '
                'os text, '
                'os_version text, '
                'PRIMARY KEY (mac, network)'),
            ('client_log',
                'time timestamptz NOT NULL DEFAULT now(), '
                'mac macaddr, '
                'network int, '
                'cid text, '
                'band text, '
                'bitrate text, '
                'channel_width int, '
                'link text, '
                'mcs text, '
                'signal text, '
                'traffic text, '
                'download int, '
                'upload int, '
                'wifi_mode text, '
                'last_name text, '
                'last_node macaddr, '
                'last_seen timestamptz, '
                'name text, '
                'name_override text, '
                'blocked bool, '
                'os text, '
                'os_version text, '
                'PRIMARY KEY (time, mac, network)'),
            ('node_checkin',
                'node int NOT NULL, '
                'time timestamptz NOT NULL, '
                'status text, '
                'speed int, '
                'PRIMARY KEY (node, time)')
            ]
