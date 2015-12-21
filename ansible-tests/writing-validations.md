Writing Validations
===================

This document describes how to write a TripleO validation in a way that's consumable by our validation API.

The purpose of the code here is to provide checks that can find issues with a TripleO deployment. They are written in Ansible and an HTTP API is available to have them be available for the UI and the command line client.

We plan to move the API to the TripleO API efforts.


Directory Structure
-------------------

The validations and everything necessary to run them are located under the `ansible-tests` directory.

Here are the important files:


    ansible-tests/
    ├── hosts.sample
    ├── stages
    │   ├── hardware-discovery.yaml
    │   └── network-configuration.yaml
    └── validations
        ├── another_validation.yaml
        ├── some_validation.yaml
        ├── library
        │   ├── another_module.py
        │   └── some_module.py
        └── tasks
            └── some_task.yaml


All validations are located in the `validations` directory. It contains two subdirectories: the `library` is for custom Ansible modules available to the validations and `tasks` is for common steps that can be shared between the validations.

The validations are grouped under deployment stages (e.g. pre-hardware introspection, pre-deployment, post-deployment). The files describing these stages and which validations belong there are located in the `stages` directory.

Finally, the `hosts.sample` file represents a sample Ansible inventory file. It will contain the nodes available to TripleO to deploy the OpenStack on. These should be grouped such that a validation can specify whether it should only be run on e.g. the storage nodes.


Sample Validation
-----------------

Each validation is an Ansible playbook with a known location and some metadata. Here is what a minimal validation would look like:

    ---
    - hosts: overcloud
      vars:
        metadata:
          name: Sample validation
          description: This is a validation that doesn't actually do anything.
      tasks:
      - name: Run an echo command
        command: echo Hello World!


It should be saved as `ansible-tests/validations/sample-validation.yaml`.

As you can see, it has three top-level directives: `hosts`, `vars -> metadata` and `tasks`.

`hosts` specify which nodes to run the validation on. Based on the `hosts.sample` structure, the options can be `all` (run on all nodes), `undercloud`, `overcloud` (all overcloud nodes), `controller` and `compute`.

The `vars` section serves for storing variables that are going to be available to the Ansible playbook, but our API uses the `metadata` section to read each validation's name and description. These values are then reported by the API and shown in the UI.

`tasks` contain a list of Ansible tasks to run. Each task is a YAML dictionary that must at minimum contain a name and a module to use. Module can be any module that ships with Ansible or any of the custom ones in the `library` subdirectory.

You can go to the [Ansible documentation on playbooks to learn more](http://docs.ansible.com/ansible/playbooks.html).


Ansible Inventory
-----------------

For the time being, we need to specify an Ansible inventory file that will list and group all the nodes we want to run validations against. Eventually, the API will get this data from Ironic or Heat (likely through an API call to the `tripleo` library).

The inventory file should look something like this:

    [undercloud]
    undercloud.example.com

    [overcloud:children]
    controller
    compute

    [controller]
    controller.example.com

    [compute]
    compute-1.example.com
    compute-2.example.com

    [all:vars]
    ansible_ssh_user=stack
    ansible_sudo=true


It will have a `[group]` section for each role (`undercloud`, `controller`, `compute`) listing all the nodes belonging to that group. You can also create a group from other groups as we do with `[overcloud:children]`. If a validation specifies `hosts: overcloud`, it will be run on any node that belongs to the `compute` or `controller` groups. If a node happens to belong to both, the validation will only be run once.

Lastly, we have an `[all:vars]` section where we can configure certain Ansible-specific options.

`ansible_ssh_user` will specify the user Ansible should SSH as. If that user does not have root privileges, you can instruct it to use `sudo` by setting `ansible_sudo` to `true`.

You can learn more at the [Ansible documentation page for the Inventory](http://docs.ansible.com/ansible/intro_inventory.html)


Custom Modules
--------------

In case you want to do something that is not covered by the list of [available Ansible modules](http://docs.ansible.com/ansible/modules_by_category.html), you can write your own. Modules belong to the `ansible-tests/validations/library` directory.

Here is a sample module that will always fail:

    #!/usr/bin/env python

    from ansible.module_utils.basic import *

    if __name__ == '__main__':
        module = AnsibleModule(argument_spec={})
        module.fail_json(msg="This module always fails.")


If you save it as `ansible-tests/validations/library/my_module.py`, you can use it in a validation like so:

    tasks:
    ...  # some tasks
    - name: Running my custom module
      my_module:
    ...  # some other tasks

The name of the module in the validation `my_module` must match the file name (without extension): `my_module.py`.

The custom modules can accept parameters and do more complex reporting. Please refer to the guide on writing modules in the Ansible documentation.

You can learn more at the [Ansible documentation page about writing custom modules](http://docs.ansible.com/ansible/developing_modules.html).


Running a validation
--------------------

To run a validation, you need to some nodes to run it on, these need to be in the inventory, they must be reachable from the machine you're launching the validations from and that machine needs to have Ansible installed.

In general, Ansible and the validations will be located on the *undercloud*, because that should have connectivity to all the *overcloud* nodes.

    $ git clone https://github.com/rthallisey/clapper.git
    $ cd clapper/ansible-tests
    $ cp hosts.sample hosts
    $ $EDITOR hosts  # Put your nodes' hostnames or IP addresses here
    $ ansible-playbook -i hosts validations/some_validation.yaml
