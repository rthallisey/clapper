Writing Validations
===================

This document describes how to write a TripleO validation in a way that's consumable by our validation API.

The purpose of the code here is to provide checks that can find issues with a TripleO deployment. They are written in Ansible and an HTTP API is available to have them be available for the UI and the command line client.

We plan to move the API to the TripleO API efforts.

After the generic explanation is a couple of concrete examples.


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

### Dynamic inventory

We have a [dynamic inventory](http://docs.ansible.com/ansible/intro_dynamic_inventory.html), which contacts Heat to provide the addresses of the deployed nodes as well as the undercloud.

Just pass `-i tripleo-ansible-inventory.py` to `ansible-playbook`.

### Hosts file

If you need more flexibility than what the current dynamic inventory provides, you can always write the hosts file. It should look something like this:

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

    $ cd clapper/ansible-tests
    $ ansible-playbook -v -i hosts tripleo-ansible-inventory.py validations/some_validation.yaml


Example: Verify Undercloud RAM requirements
---------------------------------------------


The Undercloud has a requirement of 16GB RAM. Let's write a validation
that verifies this is indeed the case before deploying anything.

Let's create `validations/undercloud-ram.yaml` and put some metadata in there:

```
---
- hosts: undercloud
  vars:
    metadata:
      name: Minimum RAM required on the undercloud
      description: >
        Make sure the undercloud has enough RAM.
```

The `hosts` key will tell us which server should the validation run
on. The common values are `undercloud`, `overcloud` (i.e. all
overcloud nodes), `controller` and `compute` (i.e. just the controller
or the compute nodes).

The `name` and `description` metadata will show up in the API and the
TripleO UI so make sure you put something meaningful there.

Now let's add an Ansible task so we can test that it's all set up
properly. Add this under the same indentation as `hosts` and `vars`:

```
  tasks:
  - name: Test Output
    debug: msg="Hello World!"
```

Run it from inside the `clapper/ansible-tests` directory like this
`ansible-playbook -i tripleo-ansible-inventory.py
validations/undercloud-ram.yaml`.

You should see something like this:

```
$ ansible-playbook -i tripleo-ansible-inventory.py validations/undercloud-ram.yaml

PLAY [undercloud] *************************************************************

GATHERING FACTS ***************************************************************
ok: [localhost]

TASK: [Test Output] ***********************************************************
ok: [localhost] => {
    "msg": "Hello World!"
}

PLAY RECAP ********************************************************************
localhost                  : ok=2    changed=0    unreachable=0    failed=0
```

Writing the full validation code is quite easy in this case because
Ansible has done all the hard work for us already. We can use the
`ansible_memtotal_mb` fact to get the amount of RAM (in megabytes) the
tested server currently has. For other useful values, run `ansible -i
tripleo-ansible-inventory.py undercloud -m setup`.

So, let's replace the hello world task with a real one:

```
  tasks:
  - name: Verify the RAM requirements
    fail: msg="The RAM on the undercloud node is {{ ansible_memtotal_mb }} MB, the minimal recommended value is 16 GB."
    failed_when: "({{ ansible_memtotal_mb }}) < 16000"
```

Running this, I see:

```
TASK: [Verify the RAM requirements] *******************************************
failed: [localhost] => {"failed": true, "failed_when_result": true}
msg: The RAM on the undercloud node is 8778 MB, the minimal recommended value is 16 GB.
```

Because my Undercloud node really does not have enough RAM. Your
mileage may vary.

Either way, the validation works!

`failed_when` is the real hero here: it evaluates an ansible
expression (e.g. does the node have more than 16 GB of RAM) and fails
when it's true.

The `fail` line right above it lets us print a custom error in case of
a failure. If the task succeeds (becaues we do have enough RAM),
nothing will be printed out.


Now, we're almost done, but there are a few things we can do to make
this nicer on everybody.

First, let's hoist the minimum RAM requirement into a variable. That
way we'll have one place where to change it if we need to and we'll
be able to test the validation better as well!

So, let's call the variable `minimum_ram_gb` and set it to `16`. Do
this in the `vars` section:

```
  vars:
    metadata:
      name: ...
      description: ...
    minimum_ram_gb: 16
```

Make sure it's on the same indentation level as `metadata`.

Then, update `failed_when` like this:

    failed_when: "({{ ansible_memtotal_mb }}) < {{ minimum_ram_gb|int * 1024 }}"

And `fail` like so:

    fail: msg="The RAM on the undercloud node is {{ ansible_memtotal_mb }} MB, the minimal recommended value is {{ minimum_ram_gb|int * 1024 }} MB."

And re-run it again to be sure it's still working.

One benefit of using a variable instead of a hardcoded value is that
we can now change the value without editing the yaml file!

Let's do that to test both success and failure cases.

This should succeed but saying the RAM requirement is 1 GB:

    ansible-playbook -i tripleo-ansible-inventory.py validations/undercloud-ram.yaml -e minimum_ram_gb=1

And this should fail buy requiring much more RAM than is necessary:

    ansible-playbook -i tripleo-ansible-inventory.py validations/undercloud-ram.yaml -e minimum_ram_gb=128

(the actual values may be different in your configuration -- just make
sure one is low enough and the other too high)


And that's it! The validation is now finished and you can start using
it in earnest.


Please consider submitting a pull request at the
[validation repository][clapper] to make any future deployments go
smoother.

[clapper]: https://github.com/rthallisey/clapper


For reference, here's the full validation:

```
---
- hosts: undercloud
  vars:
    metadata:
      name: Minimum RAM required on the undercloud
      description: Make sure the undercloud has enough RAM.
    minimum_ram_gb: 16
  tasks:
  - name: Verify the RAM requirements
    fail: msg="The RAM on the undercloud node is {{ ansible_memtotal_mb }} MB, the minimal recommended value is {{ minimum_ram_gb|int * 1024 }} MB."
    failed_when: "({{ ansible_memtotal_mb }}) < {{ minimum_ram_gb|int * 1024 }}"
```
