rm -rf /usr/lib/python2.7/site-packages/tripleo_validations*
source /home/stack/stackrc
python setup.py install
# TODO(mandre) ideally this should be installed to the right place right away
cp /usr/share/tripleo-validations/sudoers /etc/sudoers.d/tripleo-validations
systemctl restart openstack-mistral-executor
systemctl restart openstack-mistral-engine
systemctl restart openstack-mistral-api
# this loads the actions via entrypoints (puppet already runs this)
mistral-db-manage populate
# make sure the new actions got loaded
mistral action-list | grep tripleo
