TripleO Validations
===================


## Setup

    $ cd ansible-tests/
    $ virtualenv .venv
    $ source .venv/bin/activate
    $ pip install -r requirements.txt


## Validation scripts setup

    $ source .venv/bin/activate
    $ source ~/stackrc
    $ ansible -i tripleo-ansible-inventory.py -m ping all

Verify that the test run and succeeds. You can also run a specific validation with:

    $ ansible-playbook -i tripleo-ansible-inventory.py validations/haproxy.yaml
