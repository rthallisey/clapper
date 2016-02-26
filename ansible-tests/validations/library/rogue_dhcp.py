#!/usr/bin/env python

from ansible.module_utils.basic import *
from scapy.all import *

DOCUMENTATION = '''
---
module: rogue_dhcp
short_description: Detect rogue DHCP servers running on the specified networks.
author: "Tomas Sedovic, @tomassedovic"
requirements:
- the "scapy" Python module
options:
  networks:
    description:
    - List of network ranges in CIDR notation to validate the discovered DHCP
      servers against.
    required: true
  timeout_seconds:
    description:
    - The amount of time in seconds to wait for DHCP responses.
    required: false
    default: 30
'''


def find_dhcp_servers(timeout_sec):
    conf.checkIPaddr = False
    fam, hw = get_if_raw_hwaddr(conf.iface)
    dhcp_discover = (Ether(dst="ff:ff:ff:ff:ff:ff") /
                     IP(src="0.0.0.0", dst="255.255.255.255") /
                     UDP(sport=68, dport=67) /
                     BOOTP(chaddr=hw) /
                     DHCP(options=[("message-type", "discover"), "end"]))
    ans, unans = srp(dhcp_discover, multi=True, timeout=timeout_sec)

    return [(unicode(packet[1][IP].src), packet[1][Ether].src)
            for packet in ans]


def main():
    module = AnsibleModule(
        argument_spec={
            'networks': dict(required=True, type='list'),
            'timeout_seconds': dict(default=30, type='int'),
        }
    )

    # TODO: validate the specified networks against the discovered DHCP server
    networks = module.params.get('networks')
    if not networks:
        module.exit_json(changed=False, msg='No networks were specified.')

    dhcp_servers = find_dhcp_servers(module.params.get('timeout_seconds'))
    if dhcp_servers:
        formatted_servers = ("%s (%s)" % (ip, mac) for (ip, mac) in dhcp_servers)
        # TODO: write out the networks when we actually use them for anything:
        results = "DHCP servers: %s" % ','.join(formatted_servers)
    else:
        results = ""

    result = {
        'changed': True,
        'msg': 'Found %d DHCP servers.' % len(dhcp_servers),
        'results': results,
    }
    module.exit_json(**result)


if __name__ == '__main__':
    main()
