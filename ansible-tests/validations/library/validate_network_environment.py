#!/usr/bin/env python

import itertools
import netaddr
import os.path
import yaml

import six

from ansible.module_utils.basic import *


def validate(netenv_path):
    with open(netenv_path, 'r') as net_file:
        network_data = yaml.load(net_file)

    errors = []

    cidrinfo = {}
    poolsinfo = {}
    vlaninfo = {}
    routeinfo = {}
    bondinfo = {}

    for name, relative_path in six.iteritems(network_data.get('resource_registry', {})):
        if name.endswith("Net::SoftwareConfig"):
            nic_config_path = os.path.join(os.path.dirname(netenv_path),
                                           relative_path)
            errors.extend(
                check_nic_configs(name, nic_config_path))

    for item, data in six.iteritems(network_data.get('parameter_defaults', {})):
        if item.endswith('NetCidr'):
            cidrinfo[item] = data
        elif item.endswith('AllocationPools'):
            poolsinfo[item] = data
        elif item.endswith('NetworkVlanID'):
            vlaninfo[item] = data
        elif item == 'ExternalInterfaceDefaultRoute':
            routeinfo = data
        elif item == 'BondInterfaceOvsOptions':
            bondinfo = data

    errors.extend(check_cidr_overlap(cidrinfo.values()))
    errors.extend(
        check_allocation_pools_pairing(
            network_data.get('parameter_defaults', {}), poolsinfo))
    errors.extend(check_vlan_ids(vlaninfo))

    return errors


def check_nic_configs(resource, path):
    errors = []
    nic_data = {}
    try:
        with open(path, 'r') as nic_file:
            nic_data = yaml.load(nic_file)
    except IOError:
        errors.append('The resource "{}" reference file does not exist: "{}"'
                      .format(resource, path))

    # Look though every resources bridges and make sure there is only a single
    # bond per bridge and only 1 interface per bridge if there are no bonds.
    for name, resource in six.iteritems(nic_data.get('resources', {})):
        bridges = resource['properties']['config']['os_net_config']['network_config']
        for bridge in bridges:
            if bridge['type'] == 'ovs_bridge':
                bond_count = 0
                interface_count = 0
                for bond in bridge['members']:
                    if bond['type'] == 'ovs_bond':
                        bond_count += 1
                    if bond['type'] == 'interface':
                        interface_count += 1
                if bond_count == 2:
                    errors.append(
                        'Invalid bonding: There are 2 bonds for '
                        ' bridge {} of resource {} in {}'.format(
                            bridge['name'], name, path))
                if bond_count == 0 and interface_count > 1:
                    errors.append(
                        'Invalid interface: When not using a bond, '
                        'there can only be 1 interface for bridge {} '
                        'of resource {} in {}'.format(
                            bridge['name'], name, path))
    return errors


def check_cidr_overlap(networks):
    errors = []
    objs = []
    for x in networks:
        try:
            objs += [netaddr.IPNetwork(x.decode('utf-8'))]
        except ValueError:
            errors.append('Invalid address: {}'.format(x))

    for net1, net2 in itertools.combinations(objs, 2):
        if (net1 in net2 or net2 in net1):
            errors.append(
                'Overlapping networks detected {} {}'.format(net1, net2))
    return errors


def check_allocation_pools_pairing(filedata, pools):
    errors = []
    for poolitem, pooldata in six.iteritems(pools):
        pool_objs = []
        for dict_range in pooldata:
            try:
                pool_objs.append(netaddr.IPRange(
                    netaddr.IPAddress(dict_range['start']),
                    netaddr.IPAddress(dict_range['end'])))
            except Exception:
                errors.append("Invalid format of the ip range in {}: {}".format(
                    poolitem, dict_range))

        subnet_item = poolitem.split('AllocationPools')[0] + 'NetCidr'
        try:
            subnet_obj = netaddr.IPNetwork(
                filedata[subnet_item].decode('utf-8'))
        except ValueError:
            errors.append('Invalid address: {}'.format(subnet_item))

        for ranges in pool_objs:
            for range in ranges:
                if range not in subnet_obj:
                    errors.append('Allocation pool {} {} outside of subnet'
                                  '{}: {}'.format(poolitem,
                                                  pooldata,
                                                  subnet_item,
                                                  subnet_obj))
                    break
    return errors


def check_vlan_ids(vlans):
    errors = []
    invertdict = {}
    for k, v in six.iteritems(vlans):
        if v not in invertdict:
            invertdict[v] = k
        else:
            errors.append('Vlan ID {} ({}) already exists in {}'.format(
                v, k, invertdict[v]))
    return errors


def main():
    module = AnsibleModule(argument_spec=dict(
        path=dict(required=True, type='str')
    ))

    netenv_path = module.params.get('path')

    if not os.path.isfile(netenv_path):
        module.exit_json(
            changed=True,
            warnings=["Could not validate network environment.",
                      "File '{}' not found.".format(netenv_path)]
        )

    errors = validate(netenv_path)

    if errors:
        module.fail_json(msg="\n".join(errors))
    else:
        module.exit_json(msg="No errors found for the '{}' file.".format(
            netenv_path))


if __name__ == '__main__':
    main()
