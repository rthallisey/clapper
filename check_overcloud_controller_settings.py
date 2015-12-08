#!/usr/bin/env python

import os
import ConfigParser
import re
import sys

MARIADB_MAX_CONNECTIONS_MIN = 4096
MARIADB_OPEN_FILES_LIMIT_MIN = 16384

HAPROXY_GLOBAL_MAXCONN_MIN = 20480
HAPROXY_DEFAULT_MAXCONN_MIN = 4096

def find_mariadb_config_file():
    potential_locations = [
        '/etc/my.cnf.d/galera.cnf',
        '/etc/my.cnf.d/server.cnf',
        '/etc/my.cnf',
    ]
    for filepath in potential_locations:
        if os.access(filepath, os.R_OK):
            return filepath

    raise Exception(
        "Can't find mariadb config at %s" %
        potential_locations
    )

def find_haproxy_config_file():
    potential_locations = [
        '/etc/haproxy/haproxy.cfg',
    ]
    for filepath in potential_locations:
        if os.access(filepath, os.R_OK):
            return filepath

    raise Exception(
        "Can't find haproxy config at %s" %
        potential_locations
    )

def check_mariadb_config():
    config_file = find_mariadb_config_file()
    config = ConfigParser.SafeConfigParser()
    config.read(config_file)

    print "Checking settings in {}".format(config_file)

    if not config.has_option('mysqld', 'max_connections'):
        print "WARNING max_connections is unset, recommend at least {}" \
            .format(MARIADB_MAX_CONNECTIONS_MIN)
    elif config.getint('mysqld', 'max_connections') < MARIADB_MAX_CONNECTIONS_MIN:
        print "WARNING max_connections is {}, recommend at least {}".format(
            config.getint('mysqld', 'max_connections'),
            MARIADB_MAX_CONNECTIONS_MIN)

    if config.has_option('mysqld', 'open_files_limit') and \
            config.getint('mysqld', 'open_files_limit') < MARIADB_OPEN_FILES_LIMIT_MIN:
        print "WARNING open_files_limit is {}, recommend at least {}".format(
            config.getint('mysqld', 'open_files_limit'),
            MARIADB_OPEN_FILES_LIMIT_MIN)

def check_haproxy_config():
    config_file = find_haproxy_config_file()
    config = parse_haproxy_conf(config_file)

    print "Checking settings in {}".format(config_file)

    if 'global' not in config or \
            'maxconn' not in config['global']:
        print "WARNING global maxconn is unset, recommend at least {}" \
            .format(HAPROXY_GLOBAL_MAXCONN_MIN)
    elif int(config['global']['maxconn']) < HAPROXY_GLOBAL_MAXCONN_MIN:
        print "WARNING global maxconn is {}, recommend at least {}".format(
            int(config['global']['maxconn']),
            HAPROXY_GLOBAL_MAXCONN_MIN)

    if 'defaults' not in config or \
            'maxconn' not in config['defaults']:
        print "WARNING defaults maxconn is unset, recommend at least {}" \
            .format(HAPROXY_DEFAULT_MAXCONN_MIN)
    elif int(config['defaults']['maxconn']) < HAPROXY_DEFAULT_MAXCONN_MIN:
        print "WARNING defaults maxconn is {}, recommend at least {}".format(
            int(config['defaults']['maxconn']),
            HAPROXY_DEFAULT_MAXCONN_MIN)

def parse_haproxy_conf(file_path):
    config = {}
    current_section = None
    with open(file_path) as config_file:
        for line in config_file:
            match_section = re.match('^(\w+)', line)
            if match_section:
                current_section = match_section.group(1)
                config[current_section] = {}
            match_option = re.match('^(?:\s+)(\w+)\s(.*)$', line)
            if match_option and current_section:
                config[current_section][match_option.group(1)] = match_option.group(2)
    return config


check_mariadb_config()
check_haproxy_config()
