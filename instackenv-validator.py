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

    error_count = 0
    errored_ipmi = []

    with open(args['file'], 'r') as net_file:
        env_data = json.load(net_file)

    maclist = []
    baremetal_ips = []
    for node in env_data['nodes']:
        LOG.info("Checking node %s" % node['pm_addr'])

        try:
            if len(node['pm_password']) == 0:
                LOG.error('ERROR: Password 0 length.')
        except Exception, e:
            LOG.error('ERROR: Password does not exist: %s', e)
            error_count += 1
        try:
            if len(node['pm_user']) == 0:
                LOG.error('ERROR: User 0 length.')
        except Exception, e:
            LOG.error('ERROR: User does not exist: %s', e)
            error_count += 1
        try:
            if len(node['mac']) == 0:
                LOG.error('ERROR: MAC address 0 length.')
            maclist.append(node['mac'])
        except Exception, e:
            LOG.error('ERROR: MAC address does not exist: %s', e)
            error_count += 1

        if node['pm_type'] == "pxe_ssh":
            LOG.debug("Identified virtual node")

        if node['pm_type'] == "pxe_ipmitool":
            LOG.debug("Identified baremetal node")

            cmd = 'ipmitool -R 1 -I lanplus -H %s -U %s -P %s chassis status' % (
                node['pm_addr'], node['pm_user'], node['pm_password'])
            LOG.debug("Executing: %s", cmd)
            status = os.system(cmd)
            if status != 0:
                LOG.error('ERROR: ipmitool failed')
                error_count += 1
                errored_ipmi.append(node['pm_addr'])
            baremetal_ips.append(node['pm_addr'])

    if not allUnique(baremetal_ips):
        LOG.error('ERROR: Baremetals IPs are not all unique.')
        error_count += 1
    else:
        LOG.debug('Baremetal IPs are all unique.')

    if not allUnique(maclist):
        LOG.error('ERROR: MAC addresses are not all unique.')
        error_count += 1
    else:
        LOG.debug('MAC addresses are all unique.')

    print "\n--------------------"
    if error_count == 0:
        print('SUCCESS: instackenv validator found 0 errors')
    else:
        print('FAILURE: instackenv validator found %d errors' % error_count)
        if len(errored_ipmi) > 0 :
            print('Failure to contact below addresses')
            for ipmi_addr in errored_ipmi :
                print('IPMI Address : %s' % ipmi_addr)


if __name__ == "__main__":
    sys.exit(main())
