Set the first interface for PXE boot
====================================

This is a hotfix from:

https://bugzilla.redhat.com/show_bug.cgi?id=1234601

Usage
-----

This needs to be set on the undercloud before node introspection
(`openstack baremetal introspection bulk start`). This script requires
Ansible so we need to
[install that first](http://docs.ansible.com/ansible/intro_installation.html).
Then clone the repository, configure the ansible hosts file and run
the script:

    $ cp hosts.sample hosts
    $ $EDITOR hosts  # Add your undercloud server
    $ ansible-playbook --inventory hosts multi-nic-introspection-fix/playbook.yaml
