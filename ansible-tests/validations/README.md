Existing validations
====================

Here are all the validations that currently exist. They're grouped by
the deployment stage they're should be run on.

* prep: validations that are run on a fresh machine *before* the undercloud is installed
* pre-introspection: when the undercloud is ready to perform hardware introspection
* pre-deployment: validations that are run right before deploying the overcloud
* post-deployment: validations that are run after the overcloud deployment finished

Validations can belong to multiple groups.

## Prep ##

* [Make sure the undercloud drives have 512e support](512e.yaml)
* [Detect rogue DHCP servers](rogue-dhcp.yaml)
* [Verify the undercloud has enough CPU cores](undercloud-cpu.yaml)
* [Verify the undercloud has enough disk space for the initial deployment](undercloud-disk-space.yaml)
* [Verify the undercloud has enough RAM](undercloud-ram.yaml)

## Pre-introspection ##

* [Verify `network_gateway` is set correctly in `undercloud.conf` and is reachable](check-network-gateway.yaml)
* [Check the number of IP addresses for the overcloud nodes](ctlplane-ip-range.yaml)
* [Validate the instackenv.json file contents](instackenv.yaml)
* [Detect rogue DHCP servers](rogue-dhcp.yaml)
* [Verify the undercloud has enough CPU cores](undercloud-cpu.yaml)
* [Verify the undercloud has enough disk space for the initial deployment](undercloud-disk-space.yaml)
* [Verify the undercloud has enough RAM](undercloud-ram.yaml)

## Pre-deployment ##

* [Make sure the undercloud drives have 512e support](512e.yaml)
* [Highlight differences between nodes based on the discovery data from Ironic](discovery_diff.yaml)
* [Validate the Heat network environment files](network_environment.yaml)
* [Detect rogue DHCP servers](rogue-dhcp.yaml)
* [Verify the undercloud doesn't run too many processes](undercloud-process-count.yaml)

## Post-deployment ##

* [Check connectivity to OpenStack services](check_openstack_endpoints.yaml)
* [Verify nodes can ping the IP addresses on the isolated networks](compute_node_connectivity.yaml)
* [Verify the HAProxy configuration](haproxy.yaml)
* [Verify MySQL Open Files limit](mysql-open-files-limit.yaml)
* [Run neutron-sanity-check](neutron-sanity-check.yaml)
* [Verify Nova's firewall_driver is set to NoopFirewallDriver](no-op-firewall-nova-driver.yaml)
* [Verify all hosts have NTP configured and running](ntpstat.yaml)
* [Verify the pacemaker status on the controller nodes](pacemaker-status.yaml)
* [Verify the rabbitmq file descriptor limits are set correctly.](rabbitmq-limits.yaml)
