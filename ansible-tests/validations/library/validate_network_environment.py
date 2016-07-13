#!/usr/bin/env python

import collections
import itertools
import netaddr
import os.path
import yaml

import six

from ansible.module_utils.basic import *


def open_network_environment_files(netenv_path):
    errors = []
    try:
        with open(netenv_path, 'r') as net_file:
            network_data = yaml.load(net_file)
    except Exception as e:
        return ({}, {}, ["Can't open network environment file '{}': {}"
                         .format(netenv_path, e)])
    nic_configs = []
    resource_registry = network_data.get('resource_registry', {})
    for nic_name, relative_path in six.iteritems(resource_registry):
        if nic_name.endswith("Net::SoftwareConfig"):
            nic_config_path = os.path.join(os.path.dirname(netenv_path),
                                           relative_path)
            try:
                with open(nic_config_path, 'r') as nic_file:
                    nic_configs.append(
                        (nic_name, nic_config_path, yaml.load(nic_file)))
            except Exception as e:
                errors.append(
                    "Can't open the resource '{}' reference file '{}': {}"
                    .format(nic_name, nic_config_path, e))

    return (network_data, nic_configs, errors)


def validate(netenv_path):
    network_data, nic_configs, errors = open_network_environment_files(
        netenv_path)
    errors.extend(validate_network_environment(network_data, nic_configs))
    return errors


def validate_network_environment(network_data, nic_configs):
    errors = []

    cidrinfo = {}
    poolsinfo = {}
    vlaninfo = {}
    routeinfo = {}
    bondinfo = {}
    staticipinfo = {}

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

    for nic_config_name, nic_config_path, nic_config in nic_configs:
        errors.extend(check_nic_configs(nic_config_path, nic_config))

    errors.extend(check_cidr_overlap(cidrinfo.values()))
    errors.extend(
        check_allocation_pools_pairing(
            network_data.get('parameter_defaults', {}), poolsinfo))
    errors.extend(check_static_ip_pool_collision(staticipinfo, poolsinfo))
    errors.extend(check_vlan_ids(vlaninfo))
    errors.extend(check_static_ip_in_cidr(cidrinfo, staticipinfo))
    errors.extend(duplicate_static_ips(staticipinfo))

    return errors


def check_nic_configs(path, nic_data):
    errors = []

    if not isinstance(nic_data, collections.Mapping):
        return ["The nic_data parameter must be a dictionary."]

    # Look though every resources bridges and make sure there is only a single
    # bond per bridge and only 1 interface per bridge if there are no bonds.
    resources = nic_data.get('resources')
    if not isinstance(resources, collections.Mapping):
        return ["The nic_data must contain the 'resources' key and it must be "
                "a dictionary."]
    for name, resource in six.iteritems(resources):
        if not isinstance(resource, collections.Mapping):
            errors.append("'{}' is not a valid resource.".format(name))
            continue
        properties = resource.get('properties')
        if not isinstance(properties, collections.Mapping):
            errors.append("The '{}' resource must contain 'properties'."
                          .format(name))
            continue
        if 'config' not in properties:
            continue
        else:
            config = properties.get('config')
            if not isinstance(config, collections.Mapping):
                errors.append(
                    "The 'config' property of '{}' must be a dictionary."
                    .format(name))
                continue
        if 'os_net_config' not in config:
            continue
        else:
            os_net_config = config.get('os_net_config')
            if not isinstance(os_net_config, collections.Mapping):
                errors.append(
                    "The 'os_net_config' section of '{}' must be a dictionary."
                    .format(name))
                continue
        if 'network_config' in os_net_config:
            bridges = os_net_config['network_config']
        else:
            continue
        if not isinstance(bridges, collections.Iterable):
            errors.append("The 'network_config' section of '{}' must be a list."
                          .format(name))
            continue
        for bridge in bridges:
            if 'type' not in bridge:
                errors.append("The bridge item {} in {} {} must have a type."
                              .format(bridge, name, path))
                continue
            if 'name' not in bridge:
                errors.append("The bridge item {} in {} {} must have a name."
                              .format(bridge, name, path))
                continue
            if bridge['type'] == 'ovs_bridge':
                bond_count = 0
                interface_count = 0
                if not isinstance(bridge.get('members'), collections.Iterable):
                    errors.append(
                        "OVS bridge {} in {} {} must contain a 'members' list."
                        .format(bridge, name, path))
                    continue
                for bond in bridge['members']:
                    if not isinstance(bond, collections.Mapping):
                        errors.append(
                            "The {} bond in {} {} must be a dictionary."
                            .format(bond, name, path))
                        continue
                    if 'type' not in bond:
                        errors.append(
                            "The {} bond in {} {} must have a type."
                            .format(bond, name, path))
                        continue
                    if bond['type'] == 'ovs_bond':
                        bond_count += 1
                    elif bond['type'] == 'interface':
                        interface_count += 1
                    else:
                        # TODO(mandre) should we add an error for unknown bond
                        # types?
                        pass

                if bond_count == 2:
                    errors.append(
                        'Invalid bonding: There are 2 bonds for'
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
    if not isinstance(networks, collections.Iterable):
        return ["The argument must be iterable."]
    for x in networks:
        try:
            objs.append(netaddr.IPNetwork(x))
        except (ValueError, TypeError):
            errors.append('Invalid network: {}'.format(x))

    for net1, net2 in itertools.combinations(objs, 2):
        if (net1 in net2 or net2 in net1):
            errors.append(
                'Networks {} and {} overlap.'
                .format(net1, net2))
    return errors


def check_allocation_pools_pairing(filedata, pools):
    if not isinstance(filedata, collections.Mapping):
        return ["The first argument must be a dictionary."]
    if not isinstance(pools, collections.Mapping):
        return ["The second argument must be a dictionary."]
    errors = []
    for poolitem, pooldata in six.iteritems(pools):
        pool_objs = []
        if not isinstance(pooldata, collections.Iterable):
            errors.append('The IP ranges in {} must form a list.'
                          .format(poolitem))
            continue
        for dict_range in pooldata:
            try:
                pool_objs.append(netaddr.IPRange(
                    netaddr.IPAddress(dict_range['start']),
                    netaddr.IPAddress(dict_range['end'])))
            except Exception:
                errors.append("Invalid format of the IP range in {}: {}"
                              .format(poolitem, dict_range))
                continue

        subnet_item = poolitem.split('AllocationPools')[0] + 'NetCidr'
        try:
            network = filedata[subnet_item]
            subnet_obj = netaddr.IPNetwork(network)
        except KeyError:
            errors.append('The {} CIDR is not specified for {}.'
                          .format(subnet_item, poolitem))
            continue
        except Exception:
            errors.append('Invalid IP network: {}'.format(network))
            continue

        for ranges in pool_objs:
            for range in ranges:
                if range not in subnet_obj:
                    errors.append('Allocation pool {} {} outside of subnet'
                                  ' {}: {}'.format(poolitem,
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
    if not isinstance(static_ips, collections.Mapping):
        return ["The static IPs input must be a dictionary."]
    if not isinstance(pools, collections.Mapping):
        return ["The Pools input must be a dictionary."]
    errors = []
    pool_ranges = []
    for pool_name, ranges in six.iteritems(pools):
        if not isinstance(ranges, collections.Iterable):
            errors.append("The IP ranges in {} must form a list."
                          .format(pool_name))
            continue
        for allocation_range in ranges:
            try:
                ip_range = netaddr.IPRange(allocation_range['start'],
                                           allocation_range['end'])
            except Exception:
                errors.append("Invalid format of the IP range in {}: {}"
                              .format(pool_name, allocation_range))
                continue
            pool_ranges.append((pool_name, ip_range))

    for role, services in six.iteritems(static_ips):
        if not isinstance(services, collections.Mapping):
            errors.append("The {} must be a dictionary.".format(role))
            continue
        for service, ips in six.iteritems(services):
            if not isinstance(ips, collections.Iterable):
                errors.append("The {}->{} must be an array."
                              .format(role, service))
                continue
            for ip in ips:
                try:
                    ip = netaddr.IPAddress(ip)
                except netaddr.AddrFormatError as e:
                    errors.append("{} is not a valid IP address: {}"
                                  .format(ip, e))
                    continue
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
    if not isinstance(vlans, collections.Mapping):
        return ["The vlans parameter must be a dictionary."]
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
    if not isinstance(networks, collections.Mapping):
        return ["The networks argument must be a dictionary."]
    if not isinstance(static_ips, collections.Mapping):
        return ["The static_ips argument must be a dictionary."]
    errors = []
    network_ranges = {}
    # TODO(shadower): Refactor this so networks are always valid and already
    # converted to `netaddr.IPNetwork` here. Will be useful in the other checks.
    for name, cidr in six.iteritems(networks):
        try:
            network_ranges[name] = netaddr.IPNetwork(cidr)
        except Exception:
            errors.append("Network '{}' has an invalid CIDR: '{}'"
                          .format(name, cidr))
    for role, services in six.iteritems(static_ips):
        if not isinstance(services, collections.Mapping):
            errors.append("The {} must be a dictionary.".format(role))
            continue
        for service, ips in six.iteritems(services):
            range_name = service.title().replace('_', '') + 'NetCidr'
            if range_name in network_ranges:
                if not isinstance(ips, collections.Iterable):
                    errors.append("The {}->{} must be a list."
                                  .format(role, service))
                    continue
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
    if not isinstance(static_ips, collections.Mapping):
        return ["The static_ips argument must be a dictionary."]
    ipset = collections.defaultdict(list)
    # TODO(shadower): we're doing this netsted loop multiple times. Turn it
    # into a generator or something.
    for role, services in six.iteritems(static_ips):
        if not isinstance(services, collections.Mapping):
            errors.append("The {} must be a dictionary.".format(role))
            continue
        for service, ips in six.iteritems(services):
            if not isinstance(ips, collections.Iterable):
                errors.append("The {}->{} must be a list."
                              .format(role, service))
                continue
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
