Find rogue DHCP servers
=======================

We can't have running DHCP servers on networks managed by Pacemaker.
This tests accepts an optional list of Pacemaker-managed networks,
tries to discover DHCP on all interfaces and report if any are found
on the Pacemaker networks.


Dependencies
============

* scapy
* ipaddress


Usage
=====

The script needs to be run as root on an OpenStack machine that has
access to the tested networks. The "controller" node or the one
running Keystone.

If you run `dhcp-test.sh`, it will install the dependencies, run the
test script and remove the deps again:

    # ./dhcp-test.sh -p 10.15.20.0/16 -p 10.15.32.0/16

If you install the dependencies yourself, you can run the test script directly:

    # python test-pacemaker-networks.py 10.15.20.0/16 10.15.32.0/16
