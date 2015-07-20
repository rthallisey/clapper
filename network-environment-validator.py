#!/usr/bin/env python
# curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
# python get-pip.py

import argparse
import ipaddress
import itertools
import logging
import sys
import yaml

logging.basicConfig()
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)  # JPEELER: change to INFO later


def argParser():
    parser = argparse.ArgumentParser(description='Clapper')

    parser.add_argument('-n', '--netenv',
                        help='path to network environment file',
                        type=str,
                        default='network-environment.yaml')

    return vars(parser.parse_args())


def main():
    args = argParser()

    cidrinfo = {}
    poolsinfo = {}
    vlaninfo = {}
    routeinfo = {}
    bondinfo = {}

    with open(args['netenv'], 'r') as net_file:
        network_data = yaml.load(net_file)
        LOG.debug('\n' + yaml.dump(network_data))

    for item in network_data['resource_registry']:
        data = network_data['resource_registry'][item]
        LOG.debug(data)

        NIC_validate(item, data)

    for item in network_data['parameter_defaults']:
        data = network_data['parameter_defaults'][item]

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

    check_cidr_overlap(cidrinfo.values())
    check_allocation_pools_pairing(network_data['parameter_defaults'],
                                   poolsinfo)
    check_vlan_ids(vlaninfo)


def check_cidr_overlap(networks):
    objs = []
    for x in networks:
        try:
            objs += [ipaddress.ip_network(x.decode('utf-8'))]
        except ValueError:
            LOG.error('Invalid address: %s', x)

    for net1, net2 in itertools.combinations(objs, 2):
        if (net1.overlaps(net2)):
            LOG.error('Overlapping networks detected {} {}'.format(net1, net2))


def check_allocation_pools_pairing(filedata, pools):
    for poolitem in pools:
        pooldata = filedata[poolitem]

        LOG.info('Checking allocation pool {}'.format(poolitem))
        pool_objs = [ipaddress.summarize_address_range(
            ipaddress.ip_address(x['start'].decode('utf-8')),
            ipaddress.ip_address(x['end'].decode('utf-8'))) for x in
            pooldata]

        subnet_item = poolitem.split('AllocationPools')[0] + 'NetCidr'
	try:
            subnet_obj = ipaddress.ip_network(
                filedata[subnet_item].decode('utf-8'))
        except ValueError:
            LOG.error('Invalid address: %s', subnet_item)

        for ranges in pool_objs:
            for range in ranges:
                if not subnet_obj.overlaps(range):
                    LOG.error('Allocation pool {} {} outside of subnet'
                              '{}: {}'.format(poolitem, pooldata, subnet_item,
                                              subnet_obj))
                    break


def check_vlan_ids(vlans):
    invertdict = {}
    for k, v in vlans.iteritems():
        LOG.info('Checking Vlan ID {}'.format(k))
        if v not in invertdict:
            invertdict[v] = k
        else:
            LOG.error('Vlan ID {} ({}) already exists in {}'.format(
                v, k, invertdict[v]))


def NIC_validate(resource, path):
    try:
        with open(path, 'r') as nic_file:
            nic_data = yaml.load(nic_file)
    except IOError:
        LOG.error('The resource "%s" reference file does not exist: "%s"', resource, path)

    # Look though every resources bridges and make sure there is only a single
    # bond per bridge and only 1 interface per bridge if there are no bonds.
    for item in nic_data['resources']:
        bridges = nic_data['resources'][item]['properties']['config']['os_net_config']['network_config']
        for bridge in bridges:
            LOG.debug('\n' + yaml.dump(bridge))
            if bridge['type'] == 'ovs_bridge':
                bond_count = 0
                interface_count = 0
                for bond in bridge['members']:
                    if bond['type'] == 'ovs_bond':
                        bond_count+=1
                    if bond['type'] == 'interface':
                        interface_count+=1
                if bond_count == 0:
                    # Logging could be better if we knew the bridge name
                    # Since it's passed as a paramter we would need to catch it
                    LOG.debug('There are 0 bonds for bridge %s of resource %s in %s', bridge['name'], item, path)
                if bond_count == 1:
                    LOG.debug('There is 1 bond for bridge %s of resource %s in %s', bridge['name'], item, path)
                if bond_count == 2:
                    LOG.error('Invalid bonding: There are 2 bonds for bridge %s of resource %s in %s', bridge['name'], item, path)
                if bond_count == 0 and interface_count > 1:
                    LOG.error('Invalid interface: When not using a bond, there can only be 1 interface for bridge %s of resource %s in %s', bridge['name'], item, path)


if __name__ == "__main__":
    sys.exit(main())
