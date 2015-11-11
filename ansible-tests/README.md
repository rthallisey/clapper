TripleO Validation API and scripts
==================================


## Setup

    $ cd ansible-tests/
    $ virtualenv --distribute .venv
    $ source .venv/bin/activate
    $ pip install -r requirements.txt


## Validation scripts setup

    $ source .venv/bin/activate
    $ cp hosts.sample hosts

Edit `hosts` and add some IP address for the "compute" and "controller" nodes,
and set the SSH username correctly. Launching a few OpenStack VMs for this
purpose is enough for testing.

    $ export ANSIBLE_HOST_KEY_CHECKING=False
    $ ansible-playbook -i hosts playbooks/dummy_a.yaml

Verify that the test run and succeeds.


## Run the API server

    $ source .venv/bin/activate
    $ ./validation-api.py


## Notes

The API is available at: http://localhost:5000/

There is no database right now, so all the results are going to be lost when
you restart the server.

The validations are all in the `playbooks` directory.

The `test.html` page should contain a small snippen of JavaScript that accesses
the API using CORS.
