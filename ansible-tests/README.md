TripleO Validation API and scripts
==================================

## Setup

    $ virtualenv --distribute .venv
    $ source .venv/bin/activate
    $ pip install -r requirements.txt


## Run the server

    $ source .venv/bin/activate
    $ ./validation-api.py


## Notes

The API is available at: http://localhost:5000/

There is no database right now, so all the results are going to be lost when
you restart the server.

The validations are all in the `playbooks` directory.

The `test.html` page should contain a small snippen of JavaScript that accesses
the API using CORS.
