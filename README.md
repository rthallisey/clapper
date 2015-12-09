Clapper
=======

Synchronize setup and deployment for the Director.

Configuration Validation
========================

After executing the below command, you can start validation.
```
openstack baremetal import --json instackenv.json
```
The script checks the json file for missing passwords and usernames, it also 
checks that the MAC addresses contained within the file are unique. 
Lastly, it tests connections to bare metal nodes and confirm they are accessible.

The only argument for instackenv-vaidator.py is -f to input a json file.
By default this will search for instackenv.json. 

In order to use the IPMI acccess checking feature, you’ll need to run the following
command to install ipmitool on the undercloud node:

```
sudo yum -y install ipmitool

./instackenv-validation.py
```

The network-validation.py script takes the network-environment.yaml file which 
will be used to launch the overcloud as its input and checks for several things:
- Subnets do not overlap
- Allocation Pools should be part of the appropriate subnet
- VLAN IDs are unique per network

```
./network-validation.py
```

End to End Network Validation
=============================

This is being done via a modification to the heat templates.  This will use all
the nodes available to ping the VLAN routers (if applicable) as well as the
controller node and the default gateways on all nodes.  If there is a failure
it will show up in heat.

To apply these patches run:

```
cat patches/000* | (cd /usr/share/openstack-tripleo-heat-templates; sudo patch -p1)
```

If you get a failure from heat in the AllNodesValidations, you can run:

```
heat resource-list -n5 overcloud | grep Deployment | grep FAILED
```

and look for the deployments with names '0'.  For each of these run:

```
heat deployment-show <uuid>
```

of a given deployment.


Overcloud Controller Settings
=============================

After deploying the overcloud, it is possible to check the controller's
settings against current best practices for several configuration file by
executing the `check_overcloud_controller_settings.py` script on it. For
example, if your overcloud controller node has IP address 192.0.2.10:

```
ssh heat-admin@192.0.2.10 'python' < ./check_overcloud_controller_settings.py
```
