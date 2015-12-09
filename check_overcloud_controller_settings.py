#!/usr/bin/env python

import os
import re
import sys

MARIADB_MAX_CONNECTIONS_MIN = 4096
MARIADB_OPEN_FILES_LIMIT_MIN = 16384

HAPROXY_GLOBAL_MAXCONN_MIN = 20480
HAPROXY_DEFAULT_MAXCONN_MIN = 4096

warnings = {}

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

# ConfigParser chokes on both mariadb and haproxy files. Luckily They have
# a syntax approaching ini config file so they are relatively easy to parse.
# This generic ini style config parser is not perfect -- it can ignore some
# valid options --  but good enough for our use case.
def generic_ini_style_conf_parser(file_path, section_regex, option_regex):
    config = {}
    current_section = None
    with open(file_path) as config_file:
        for line in config_file:
            match_section = re.match(section_regex, line)
            if match_section:
                current_section = match_section.group(1)
                config[current_section] = {}
            match_option = re.match(option_regex, line)
            if match_option and current_section:
                config[current_section][match_option.group(1)] = match_option.group(2)
    return config

def parse_mariadb_conf(file_path):
    section_regex = '^\[(\w+)\]'
    option_regex = '^(?:\s*)(\w+)(?:\s*=\s*)?(.*)$'
    return generic_ini_style_conf_parser(file_path, section_regex, option_regex)

def parse_haproxy_conf(file_path):
    section_regex = '^(\w+)'
    option_regex = '^(?:\s+)(\w+)\s(.*)$'
    return generic_ini_style_conf_parser(file_path, section_regex, option_regex)

def check_mariadb_config():
    config_file = find_mariadb_config_file()
    config = parse_mariadb_conf(config_file)

    if 'mysqld' not in config or \
            'max_connections' not in config['mysqld']:
        add_warning(config_file,
                    "max_connections is unset, recommend at least {}".format(
                        MARIADB_MAX_CONNECTIONS_MIN))
    elif int(config['mysqld']['max_connections']) < MARIADB_MAX_CONNECTIONS_MIN:
        add_warning(config_file,
                    "max_connections is {}, recommend at least {}".format(
                        int(config['mysqld']['max_connections']),
                        MARIADB_MAX_CONNECTIONS_MIN))

    if 'mysqld' in config and 'open_files_limit' in config['mysqld'] and \
            int(config['mysqld']['open_files_limit']) < MARIADB_OPEN_FILES_LIMIT_MIN:
        add_warning(config_file,
                    "open_files_limit is {}, recommend at least {}".format(
                        int(config['mysqld']['open_files_limit']),
                        MARIADB_OPEN_FILES_LIMIT_MIN))


def check_haproxy_config():
    config_file = find_haproxy_config_file()
    config = parse_haproxy_conf(config_file)

    if 'global' not in config or \
            'maxconn' not in config['global']:
        add_warning(config_file,
                    "global maxconn is unset, recommend at least {}".format(
                        HAPROXY_GLOBAL_MAXCONN_MIN))
    elif int(config['global']['maxconn']) < HAPROXY_GLOBAL_MAXCONN_MIN:
        add_warning(config_file,
                    "global maxconn is {}, recommend at least {}".format(
                        int(config['global']['maxconn']),
                        HAPROXY_GLOBAL_MAXCONN_MIN))

    if 'defaults' not in config or \
            'maxconn' not in config['defaults']:
        add_warning(config_file,
                    "defaults maxconn is unset, recommend at least {}".format(
                        HAPROXY_DEFAULT_MAXCONN_MIN))
    elif int(config['defaults']['maxconn']) < HAPROXY_DEFAULT_MAXCONN_MIN:
        add_warning(config_file,
                    "defaults maxconn is {}, recommend at least {}".format(
                        int(config['defaults']['maxconn']),
                        HAPROXY_DEFAULT_MAXCONN_MIN))

def add_warning(config_file, msg):
    if config_file in warnings:
        warnings[config_file].append(msg)
    else:
        warnings[config_file] = [msg]

def print_summary():
    for element in warnings:
        print "Found potential issues in {}:".format(element)
        for warn in warnings[element]:
            print "\t* {}".format(warn)


check_mariadb_config()
check_haproxy_config()

print_summary()

if len(warnings) > 0:
    sys.exit(1)
