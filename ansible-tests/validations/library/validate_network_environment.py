#!/usr/bin/env python

import collections
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
    staticipinfo = {}

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
        elif item.endswith('IPs'):
            staticipinfo[item] = data
        elif item == 'ExternalInterfaceDefaultRoute':
            routeinfo = data
        elif item == 'BondInterfaceOvsOptions':
            bondinfo = data

    errors.extend(check_cidr_overlap(cidrinfo.values()))
    errors.extend(
        check_allocation_pools_pairing(
            network_data.get('parameter_defaults', {}), poolsinfo))
    errors.extend(check_static_ip_pool_collision(staticipinfo, poolsinfo))
    errors.extend(check_vlan_ids(vlaninfo))
    errors.extend(check_static_ip_in_cidr(cidrinfo, staticipinfo))
    errors.extend(duplicate_static_ips(staticipinfo))

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


def check_static_ip_pool_collision(static_ips, pools):
    """Statically defined IP address must not conflict with allocation pools.

    The allocation pools come as a dict of items in the following format:

    InternalApiAllocationPools: [{'start': '10.35.191.150', 'end': '10.35.191.240'}]

    The static IP addresses are dicts of:

    ComputeIPs: {
        'internal_api': ['10.35.191.100', etc.],
        'storage': ['192.168.100.45', etc.]
    }
    """
    errors = []

    pool_ranges = []
    for pool_name, ranges in six.iteritems(pools):
        for allocation_range in ranges:
            ip_range = netaddr.IPRange(allocation_range['start'],
                                allocation_range['end'])
            pool_ranges.append((pool_name, ip_range))
    for role, services in six.iteritems(static_ips):
        for service, ips in six.iteritems(services):
            for ip in ips:
                ranges_with_conflict = ranges_conflicting_with_ip(
                    ip, pool_ranges)
                if ranges_with_conflict:
                    for pool_name, ip_range in ranges_with_conflict:
                        msg = "IP address {} from {}[{}] is in the {} pool."
                        errors.append(msg.format(
                            ip, role, service, pool_name))
    return errors


def ranges_conflicting_with_ip(ip_address, ip_ranges):
    """Check for all conflicts of the IP address conflicts.

    This takes a single IP address and a list of `(pool_name,
    netenv.IPRange)`s.

    We return all ranges that the IP address conflicts with. This is to
    improve the final error messages.
    """
    return [(pool_name, ip_range) for (pool_name, ip_range) in ip_ranges
            if ip_address in ip_range]


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


def check_static_ip_in_cidr(networks, static_ips):
    '''
    Verify that all the static IP addresses are from the corresponding network
    range.
    '''
    errors = []
    network_ranges = {}
    # TODO(shadower): Refactor this so networks are always valid and already
    # converted to `netaddr.IPNetwork` here. Will be useful in the other checks.
    for name, cidr in six.iteritems(networks):
        try:
            network_ranges[name] = netaddr.IPNetwork(cidr)
        except ValueError:
            errors.append("Network '{}' has an invalid CIDR: '{}'"
                          .format(name, cidr))
    for role, services in six.iteritems(static_ips):
        for service, ips in six.iteritems(services):
            range_name = service.title().replace('_', '') + 'NetCidr'
            if range_name in network_ranges:
                for ip in ips:
                    if ip not in network_ranges[range_name]:
                        errors.append(
                            "The IP address {} is outside of the {} range: {}"
                            .format(ip, range_name, networks[range_name]))
            else:
                errors.append(
                    "Service '{}' does not have a "
                    "corresponding range: '{}'.".format(service, range_name))
    return errors


def duplicate_static_ips(static_ips):
    errors = []
    ipset = collections.defaultdict(list)
    # TODO(shadower): we're doing this netsted loop multiple times. Turn it
    # into a generator or something.
    for role, services in six.iteritems(static_ips):
        for service, ips in six.iteritems(services):
            for ip in ips:
                ipset[ip].append((role, service))
    for ip, sources in six.iteritems(ipset):
        if len(sources) > 1:
            msg = "The {} IP address was entered multiple times: {}."
            formatted_sources = ("{}[{}]".format(*source) for source in sources)
            errors.append(msg.format(ip, ", ".join(formatted_sources)))
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
