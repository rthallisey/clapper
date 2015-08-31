Make sure NTP is configured in HA overcloud
===========================================

When deploying an HA OpenStack, NTP has to be configured for the
controller nodes.

Usage
-----

This script should be run wherever `openstack overcloud deploy` is
executed (typically the undercloud). It can be run directly after the
`deploy` command or any time afterwards. It will contact Heat and
verify that the `NtpServer` parameter is set in the HA scenario.


    $ source ~/stackrc
    $ python test.py


Ideally, we would run this *before* the overcloud deployment, but the
`openstack` command doesn't let us do a dry-run where we get to see
all the options without running the actual deployment.
