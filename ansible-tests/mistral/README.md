# Mistral PoC

This is really rough. Basically, we add a Mistral action that runs a
shell script which runs ansible with a single validation.

## Prerequisities

Mistral on the undercloud.

Doing this before installing the undercloud worked for me:

    sudo yum -y install https://trunk.rdoproject.org/centos7/ef/60/ef602aaab58630c80dfe851eeadba5e46eea9193_9dfd2a02/openstack-mistral-all-2.0.0.0b3-dev1.el7.centos.noarch.rpm https://trunk.rdoproject.org/centos7/ef/60/ef602aaab58630c80dfe851eeadba5e46eea9193_9dfd2a02/openstack-mistral-api-2.0.0.0b3-dev1.el7.centos.noarch.rpm  https://trunk.rdoproject.org/centos7/ef/60/ef602aaab58630c80dfe851eeadba5e46eea9193_9dfd2a02/openstack-mistral-common-2.0.0.0b3-dev1.el7.centos.noarch.rpm https://trunk.rdoproject.org/centos7/ef/60/ef602aaab58630c80dfe851eeadba5e46eea9193_9dfd2a02/openstack-mistral-engine-2.0.0.0b3-dev1.el7.centos.noarch.rpm  https://trunk.rdoproject.org/centos7/ef/60/ef602aaab58630c80dfe851eeadba5e46eea9193_9dfd2a02/openstack-mistral-executor-2.0.0.0b3-dev1.el7.centos.noarch.rpm https://trunk.rdoproject.org/centos7/ef/60/ef602aaab58630c80dfe851eeadba5e46eea9193_9dfd2a02/python-openstack-mistral-2.0.0.0b3-dev1.el7.centos.noarch.rpm https://trunk.rdoproject.org/centos7/ef/60/ef602aaab58630c80dfe851eeadba5e46eea9193_9dfd2a02/python-mistralclient-1.2.1-dev17.el7.centos.noarch.rpm

    cp /usr/share/instack-undercloud/undercloud.conf.sample ~/undercloud.conf || true
    sed -i -e 's/^.*enable_mistral = .*$/enable_mistral = true/' ~/undercloud.conf



## Mistral validation setup:

    # mistral runs under the `mistral` user but its $HOME doesn't exist:
    sudo mkdir -p /home/mistral/.ssh
    sudo cp /home/stack/.ssh/id_rsa /home/mistral/.ssh/
    sudo chown -R mistral:mistral /home/mistral

    sudo cp clapper/ansible-tests/mistral/run-validation /usr/local/bin/run-validation

    # register the validation in mistral:
    cd clapper/ansible-tests/mistral
    sudo ./deploy.sh

    # copy clapper to /tmp so we avoid dealing with $HOME permissions:
    mkdir /tmp/stack
    cp -r clapper /tmp/stack
    cp /home/stack/stackrc /tmp/stack

And finally, replace `export OS_PASSWORD=$(sudo hiera admin_password)` in `/tmp/stack/stackrc`

with the actual value you get by running `sudo hiera admin_password`.

Did I mention this was janky?


## Running a validation

First, check that it's in Mistral's actions:

    mistral action-list | grep tripleo

Then run it:

    mistral run-action -s tripleo.run_validations

It will be run asynchronously and store the result. Run `mistral
action-execution-list` to see the status of all Mistral runs and
`mistral action-execution-get-output <uuid>` to get a particular run's
output.

The output is whatever dict we return from our Python code converted to json.


## TODO

* update the mistral action to take a validation name as a parameter
* use python code (instead of shelling out) to run the validations
* ton of other stuff
