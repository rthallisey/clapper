#!/usr/bin/env python

import os
import re
import sys

MARIADB_MAX_CONNECTIONS_MIN = 4096
MARIADB_OPEN_FILES_LIMIT_MIN = 16384

HAPROXY_GLOBAL_MAXCONN_MIN = 20480
HAPROXY_DEFAULTS_MAXCONN_MIN = 4096
HAPROXY_DEFAULTS_TIMEOUT_QUEUE = '1m'
HAPROXY_DEFAULTS_TIMEOUT_CLIENT = '1m'
HAPROXY_DEFAULTS_TIMEOUT_SERVER = '1m'
HAPROXY_DEFAULTS_TIMEOUT_CHECK = '10s'

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


def check_mariadb_config():
    config_file = find_mariadb_config_file()
    config = parse_mariadb_conf(config_file)

    assert_no_less_than(MARIADB_MAX_CONNECTIONS_MIN,
                        config, 'mysqld', 'max_connections', config_file)

    if 'mysqld' in config and 'open_files_limit' in config['mysqld']:
        assert_no_less_than(MARIADB_OPEN_FILES_LIMIT_MIN,
                            config, 'mysqld', 'open_files_limit', config_file)


def check_haproxy_config():
    config_file = find_haproxy_config_file()
    config = parse_haproxy_conf(config_file)

    assert_no_less_than(HAPROXY_GLOBAL_MAXCONN_MIN,
                        config, 'global', 'maxconn', config_file)

    assert_no_less_than(HAPROXY_DEFAULTS_MAXCONN_MIN,
                        config, 'defaults', 'maxconn', config_file)

    assert_equal(HAPROXY_DEFAULTS_TIMEOUT_QUEUE,
                 config, 'defaults', 'timeout queue', config_file)

    assert_equal(HAPROXY_DEFAULTS_TIMEOUT_CLIENT,
                 config, 'defaults', 'timeout client', config_file)

    assert_equal(HAPROXY_DEFAULTS_TIMEOUT_SERVER,
                 config, 'defaults', 'timeout server', config_file)

    assert_equal(HAPROXY_DEFAULTS_TIMEOUT_CHECK,
                 config, 'defaults', 'timeout check', config_file)


def assert_equal(expected, config, section, option, config_file):
    if section not in config or option not in config[section]:
        add_warning(config_file,
                    "{} {} is unset, recommend is {}".format(
                        section, option, expected))
    elif config[section][option] != str(expected):
        add_warning(config_file,
                    "{} {} is {}, recommend is {}".format(
                        section, option, config[section][option], expected))


def assert_no_less_than(expected, config, section, option, config_file):
    if section not in config or option not in config[section]:
        add_warning(config_file,
                    "{} {} is unset, recommend at least {}".format(
                        section, option, expected))
    elif int(config[section][option]) < expected:
        add_warning(config_file,
                    "{} {} is {}, recommend at least {}".format(
                        section, option, config[section][option], expected))


def add_warning(config_file, msg):
    if config_file in warnings:
        warnings[config_file].append(msg)
    else:
        warnings[config_file] = [msg]


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
    option_regex = '^(?:\s+)(\w+(?:\s+\w+)*?)\s([\w/]*)$'
    return generic_ini_style_conf_parser(file_path, section_regex, option_regex)


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
