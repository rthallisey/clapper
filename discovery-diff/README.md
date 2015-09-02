Hardware Discovery Diff
=======================

This script is supposed to be run after baremetal discovery. It reads
the discovery data from Swift, compares each node and finds any
differences. Some of these are expected (MAC and IP addresses, etc.)
but some may hint at underlying issues.


Usage
-----

This script should be run after the `openstack baremetal introspection
bulk start` command. You run it on the undercloud (or with the
undercloud stackrc credentials).


    $ source ~/stackrc
    $ python discovery-diff/discovery-diff.py
