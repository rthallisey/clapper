#!/usr/bin/env python
# curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
# python get-pip.py

import argparse
import logging
import sys
import os
import json

logging.basicConfig()
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)  # JPEELER: change to INFO later


def argParser():
    parser = argparse.ArgumentParser(description='Clapper')

    parser.add_argument('-f', '--file',
                        help='path to instack json environment file',
                        type=str,
                        default='instackenv.json')

    return vars(parser.parse_args())


def allUnique(x):
    seen = list()
    return not any(i in seen or seen.append(i) for i in x)


def main():
    args = argParser()

    with open(args['file'], 'r') as net_file:
        env_data = json.load(net_file)
        #LOG.debug('\n' + json.dumps(env_data))

    for data in env_data:
        print data

    maclist = []
    for node in env_data['nodes']:
        try:
            if len(node['pm_password']) == 0:
                LOG.error('ERROR: Password 0 length.')
        except Exception, e:
            LOG.error('ERROR: Password does not exist: %s', e)
        try:
            if len(node['pm_user']) == 0:
                LOG.error('ERROR: User 0 length.')
        except Exception, e:
            LOG.error('ERROR: User does not exist: %s', e)
        try:
            if len(node['mac']) == 0:
                LOG.error('ERROR: MAC address 0 length.')
            maclist.append(node['mac'])
        except Exception, e:
            LOG.error('ERROR: MAC address does not exist: %s', e)
        cmd = 'ipmitool -I lanplus -H %s -U %s -k "%s"' % (node['pm_addr'],
              node['pm_user'], node['pm_password'])
        print("Executing:", cmd)
        os.system(cmd)

    if not allUnique(maclist):
        LOG.error('ERROR: MAC addresses are not all unique.')


if __name__ == "__main__":
    sys.exit(main())
