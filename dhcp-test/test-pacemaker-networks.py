import sys

from scapy.all import *
import ipaddress


def find_dhcp_servers():
    conf.checkIPaddr = False
    fam, hw = get_if_raw_hwaddr(conf.iface)
    dhcp_discover = (Ether(dst="ff:ff:ff:ff:ff:ff") /
                     IP(src="0.0.0.0", dst="255.255.255.255") /
                     UDP(sport=68, dport=67) /
                     BOOTP(chaddr=hw) /
                     DHCP(options=[("message-type", "discover"), "end"]))
    ans, unans = srp(dhcp_discover, multi=True, timeout=10)

    return [(unicode(packet[1][IP].src), packet[1][Ether].src)
            for packet in ans]


if __name__ == '__main__':
    result = 0

    pacemaker_networks = [ipaddress.ip_network(unicode(net))
                          for net in sys.argv[1:]]

    print "Looking for DHCP servers:"
    dhcp_servers = find_dhcp_servers()

    if len(dhcp_servers) > 0:
        print "\nFound DHCP servers:\n"
        for i, (ip, mac) in enumerate(dhcp_servers):
            print "%d. %s (mac: %s)" % (i + 1, ip, mac)
        for network in pacemaker_networks:
            if network.overlaps(ipaddress.ip_network(ip)):
                print "\tOverlaps with network %s" % network
                result = 1
    else:
        print "No DHCP servers found."

    sys.exit(result)
