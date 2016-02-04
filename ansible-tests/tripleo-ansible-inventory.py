#!/usr/bin/env python

# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
# Copyright 2016 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# TODO(mandre)
# Make it possible to specify which plan to generate inventory for
# Get info from ironic for hosts prior to deployment
# Get info from nova for more accurate addresses
# Only add host if it is up according to nova

from __future__ import print_function

import argparse
import json
import os
import re
import sys

from oslo_config import cfg

opts = [
    cfg.StrOpt('host', help='List details about the specific host'),
    cfg.BoolOpt('list', help='List active hosts'),
    cfg.StrOpt('username'),
    cfg.StrOpt('password'),
    cfg.StrOpt('auth-url'),
    cfg.StrOpt('project-name'),
    cfg.StrOpt('group-regex'),
]

try:
    from heatclient.v1 import client as heat_client
except ImportError:
    print('heatclient is required',file=sys.stderr)
    sys.exit(1)
try:
    from keystoneclient.v3 import client as keystone_client
except ImportError:
    print('keystoneclient is required', file=sys.stderr)
    sys.exit(1)


def _parse_config():
    default_config = os.environ.get('TRIPLEO_INVENTORY_CONFIG')
    if default_config:
        default_config = [default_config]

    configs = cfg.ConfigOpts()
    configs.register_cli_opts(opts)
    configs(prog='tripleo-ansible-inventory',
            default_config_files=default_config)
    if configs.auth_url is None:
        if "OS_AUTH_URL" in os.environ:
            configs.auth_url = os.environ.get('OS_AUTH_URL')
        else:
            print('ERROR: auth-url not defined and OS_AUTH_URL environment variable missing, unable to proceed.', file=sys.stderr)
            sys.exit(1)
    if configs.username is None:
        if "OS_USERNAME" in os.environ:
            configs.username = os.environ.get('OS_USERNAME')
    if configs.password is None:
        if "OS_PASSWORD" in os.environ:
            configs.password = os.environ.get('OS_PASSWORD')
    if configs.project_name is None:
        if "OS_TENANT_NAME" in os.environ:
            configs.project_name = os.environ.get('OS_TENANT_NAME')
    if '/v2.0' in configs.auth_url:
        configs.auth_url = configs.auth_url.replace('/v2.0', '/v3')
    return configs


class TripleoInventory(object):
    def __init__(self, configs):
        self.configs = configs
        self._ksclient = None
        self._hclient = None


    def fetch_stack_resources(self, stack, resource_name):
        heatclient = self.hclient
        ret = []
        try:
            resource_id = heatclient.resources.get(stack, resource_name).physical_resource_id
            for resource in heatclient.resources.list(resource_id):
                node = heatclient.resources.get(resource_id, resource.resource_name)
                node_address = node.attributes['tenant_ip_address']
                ret.append(node_address)
        except:
            # Ignore non existent stacks or resources
            pass
        return ret


    def list(self):
        ret = {'undercloud': {
               'hosts': ['localhost'],
                'vars': {
                    'ansible_connection': 'local'
                },
            }
        }
        controller_group = self.fetch_stack_resources('overcloud', 'Controller')
        if controller_group:
            ret['controller'] = controller_group

        compute_group = self.fetch_stack_resources('overcloud', 'Compute')
        if compute_group:
            ret['compute'] = compute_group

        if any([controller_group, compute_group]):
            ret['overcloud'] = {
                'children': list(set(ret.keys()) - set(['undercloud'])),
                'vars': {
                    'ansible_ssh_user': 'heat-admin',
                    'ansible_become': True,
                }
            }

        print(json.dumps(ret))


    def host(self):
        # TODO(mandre)
        print(json.dumps({}))

    @property
    def ksclient(self):
        if self._ksclient is None:
            try:
                self._ksclient = keystone_client.Client(
                    auth_url=self.configs.auth_url,
                    username=self.configs.username,
                    password=self.configs.password,
                    project_name=self.configs.project_name)
                self._ksclient.authenticate()
            except Exception, e:
                print("Error connecting to Keystone: {}".format(e.message),
                      file=sys.stderr)
                sys.exit(1)
        return self._ksclient

    @property
    def hclient(self):
        if self._hclient is None:
            ksclient = self.ksclient
            endpoint = ksclient.service_catalog.url_for(
                service_type='orchestration', endpoint_type='publicURL')
            try:
                self._hclient = heat_client.Client(
                    endpoint=endpoint,
                    token=ksclient.auth_token)
            except Exception, e:
                print("Error connecting to Heat: {}".format(e.message),
                      file=sys.stderr)
                sys.exit(1)
        return self._hclient


def main():
    configs = _parse_config()
    inventory = TripleoInventory(configs)
    if configs.list:
        inventory.list()
    elif configs.host:
        inventory.host()
    sys.exit(0)

if __name__ == '__main__':
    main()
