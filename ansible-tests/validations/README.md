Existing validations
====================

Here are all the validations that currently exist. They're grouped by
the deployment stage they're should be run on.

* clean-undercloud
* pre-deployment
* post-deployment


## Clean Undercloud ##

(run after the undercloud installs but before uploading images, etc.
The validations run on the undercloud.)

* [Make sure the undercloud drives have 512e support](512e.yaml)
* [Verify the undercloud has anough disk space for the initial deployment](undercloud-disk-space.yaml)
* [Verify `network_gateway` is set correctly in `undercloud.conf` and is reachable](check-network-gateway.yaml)

## Pre Deployment ##

* [Verify nodes can ping the ip addresses on the isolated networks](compute_node_connectivity.yaml)
* [Highlight differences between nodes based on the discovery data from Ironic](discovery_diff.yaml)


## Post Deployment ##

(run after the OpenStack deployment finished)

* [Verify the HAProxy configuration](haproxy.yaml)
* [Verify the rabbitmq file descriptor limits are set correctly.](rabbitmq-limits.yaml)
* [Verify Nova's firewall_driver is set to NoopFirewallDriver](no-op-firewall-nova-driver.yaml)
* [Run neutron-sanity-check](neutron-sanity-check.yaml)
* [Verify MySQL Open Files limit](mysql-open-files-limit.yaml)
