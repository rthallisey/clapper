#!/usr/bin/env python

# Disable scapy's warning to stderr:
import logging
import sys
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


from scapy.all import *


def find_dhcp_servers(timeout_sec):
    conf.checkIPaddr = False
    fam, hw = get_if_raw_hwaddr(conf.iface)
    dhcp_discover = (Ether(dst="ff:ff:ff:ff:ff:ff") /
                     IP(src="0.0.0.0", dst="255.255.255.255") /
                     UDP(sport=68, dport=67) /
                     BOOTP(chaddr=hw) /
                     DHCP(options=[("message-type", "discover"), "end"]))
    ans, unans = srp(dhcp_discover, multi=True, timeout=timeout_sec, verbose=False)

    return [(unicode(packet[1][IP].src), packet[1][Ether].src)
            for packet in ans]


def main():
    dhcp_servers = find_dhcp_servers(30)
    if dhcp_servers:
        sys.stderr.write('Found %d DHCP servers:' % len(dhcp_servers))
        sys.stderr.write("\n".join(("* %s (%s)" % (ip, mac) for (ip, mac) in dhcp_servers)))
        sys.exit(1)
    else:
        print "No DHCP servers found."


if __name__ == '__main__':
    main()
