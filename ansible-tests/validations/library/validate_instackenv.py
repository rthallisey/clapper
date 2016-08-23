#!/usr/bin/env python

import json
import os.path
import subprocess
import sys

from ansible.module_utils.basic import *


def unique(collection):
    '''Returns True if there are no repeating items in the collection.'''
    return len(collection) == len(set(collection))


def contact_node(address, username, password):
    '''Try to connect to the node using `ipmitool`.

    Returns `False` on failure and `True` on success or when `ipmitool` is not
    available (this check is optional).
    '''
    cmd = ['ipmitool', '-R', '1', '-I', 'lanplus',
           '-H', address, '-U', username, '-P', password,
           'chassis', 'status']
    try:
        status = subprocess.call(cmd)
        return status == 0
    except OSError:
        # the `ipmitool` command is not available. Since it's optional, treat
        # this as a success.
        return True


def validate_instackenv(instackenv_path):
    with open(instackenv_path, 'r') as net_file:
        env_data = json.load(net_file)

    errors = []

    maclist = []
    baremetal_ips = []
    for node in env_data['nodes']:
        try:
            if len(node['pm_password']) == 0:
                errors.append('Password 0 length.')
        except Exception, e:
            errors.append('Password does not exist: {}'.format(e))
        try:
            if len(node['pm_user']) == 0:
                errors.append('User is an empty string.')
        except Exception, e:
            errors.append('User does not exist: {}'.format(e))
        try:
            if len(node['mac']) == 0:
                errors.append('No MAC addresses were specified.')
            maclist.extend(node['mac'])
        except Exception, e:
            errors.append('MAC address does not exist: {}'.format(e))

        if node['pm_type'] == "pxe_ssh":
            pass  # Identified virtual node

        if node['pm_type'] == "pxe_ipmitool":
            baremetal_ips.append(node['pm_addr'])
            # Identified baremetal node, try to contact it with ipmitool
            if not contact_node(
                    node['pm_addr'], node['pm_user'], node['pm_password']):
                errors.append(
                    "Could not connect to the '{}' node.".format(node['pm_addr']))

    if not unique(baremetal_ips):
        errors.append('Baremetals IPs are not all unique.')

    if not unique(maclist):
        errors.append('MAC addresses are not all unique.')

    return errors


def main():
    module = AnsibleModule(argument_spec=dict(
        path=dict(required=True, type='str')
    ))

    instackenv_path = module.params.get('path')

    if not os.path.isfile(instackenv_path):
        module.exit_json(
            changed=True,
            warnings=["Could not find file '{}'.".format(instackenv_path)],
        )

    errors = validate_instackenv(instackenv_path)

    if errors:
        module.fail_json(msg="\n".join(errors))
    else:
        module.exit_json(
            msg="No errors found for the '{}' file.".format(instackenv_path))


if __name__ == '__main__':
    main()
