This Repository Is Deprecated!
==============================

The validations were moved under TripleO to this repository:

http://git.openstack.org/cgit/openstack/tripleo-validations/

The issues and suggestions are tracked on the TripleO launchpad:

https://bugs.launchpad.net/tripleo/+bugs

with the `validations` tag.

The rest of the Clapper repository is kept here for historical reasons.


Clapper
=======

Synchronize setup and deployment for the Director.

Ansible-based Validations
-------------------------

Recently, we focused on writing automated validations that require
little human setup or interference. These are driven by
[Ansible](http://ansible.com/) we plan to provide an API that will let
us use these from the TripleO web UI and command line clients.

### Running a validation

For now, you need to run them manually. All the validations live in
the [ansible-tests/validations](ansible-tests/validations) directory.

**NOTE** We only support Ansible 2.0 and higher.

To run a validation you need to:

    $ git clone https://github.com/rthallisey/clapper.git
    $ source ~/stackrc
    $ cd clapper/ansible-tests
    $ ls validations  # pick a validation to run
    $ ansible-playbook -i tripleo-ansible-inventory.py validations/some_validation.yaml



### Contributing validations or ideas

Submit an issue or a pull request to this repository. Alternatively,
you can email <tsedovic@redhat.com>.

When writing a validation, check out our
[Writing Validations](ansible-tests/writing-validations.md) guide.



Standalone Tools
----------------

### Checking `instackenv.json` and `network-environment.yaml`

After executing the below command, you can start validation.
```
openstack baremetal import --json instackenv.json
```
The script checks the json file for missing passwords and usernames, it also
checks that the MAC addresses contained within the file are unique.
Lastly, it tests connections to bare metal nodes and confirm they are accessible.

The only argument for instackenv-vaidator.py is -f to input a json file.
By default this will search for instackenv.json.

In order to use the IPMI access checking feature, you’ll need to run the following
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


### Overcloud Controller Settings

After deploying the overcloud, it is possible to check the controller's
settings against current best practices for several configuration file by
executing the `check_overcloud_controller_settings.py` script on it. For
example, if your overcloud controller node has IP address 192.0.2.10:

```
ssh heat-admin@192.0.2.10 'python' < ./check_overcloud_controller_settings.py
```

### Discovery Diff Validation

Provides difference in configuration based on data collected in ironic-inspectorprovides difference in configuration based on data collected in ironic-inspector

#### Steps

- Update the hosts as per guidelines
- Rename validations/files/env_vars.json.sample to validations/files/env_vars.json
- Update the configuration to reflect the environment specific values
- Run the validation

```
mv validations/files/env_vars.json.sample validations/files/env_vars.json
vi validations/files/env_vars.json  #update the configuration
ansible-playbook -v -i hosts validations/discovery_diff.yaml
```
