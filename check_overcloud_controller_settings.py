#!/usr/bin/env python

import os
import ConfigParser

MARIADB_MAX_CONNECTIONS_MIN = 4096
MARIADB_OPEN_FILES_LIMIT_MIN = 16384

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

def check_mariadb_config():
    config_file = find_mariadb_config_file()
    config = ConfigParser.SafeConfigParser()
    config.read(config_file)

    print "Checking settings in {}".format(config_file)

    if not config.has_option('mysqld', 'max_connections'):
        print "WARNING max_connections is unset, it should be at least {}" \
            .format(MARIADB_MAX_CONNECTIONS_MIN)
    elif config.getint('mysqld', 'max_connections') < MARIADB_MAX_CONNECTIONS_MIN:
        print "WARNING max_connections is {}, it should be at least {}".format(
            config.getint('mysqld', 'max_connections'),
            MARIADB_MAX_CONNECTIONS_MIN)

    if config.has_option('mysqld', 'open_files_limit') and \
            config.getint('mysqld', 'open_files_limit') < MARIADB_OPEN_FILES_LIMIT_MIN:
        print "WARNING open_files_limit is {}, it should be at least {}".format(
            config.getint('mysqld', 'open_files_limit'),
            MARIADB_OPEN_FILES_LIMIT_MIN)


check_mariadb_config()
