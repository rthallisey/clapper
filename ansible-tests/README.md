TripleO Validation API and scripts
==================================


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


## Run the API server

    $ source .venv/bin/activate
    $ source ~/stackrc
    $ ./validation-api.py


## Notes

The API is available at: http://localhost:5000/

There is no database right now, so all the results are going to be lost when
you restart the server.

The validations are all in the `validations` directory.

The `test.html` page should contain a small snippen of JavaScript that accesses
the API using CORS.
