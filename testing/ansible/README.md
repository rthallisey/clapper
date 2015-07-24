# Ansible Playbooks for network configuration tests #

0. Install ansible on the undercloud
1. Create a `hosts` file with the IP addresses of the overcloud nodes (one IP per line)
2. Run `ansible-playbook -i hosts playbook.yml`

You'll get status of all the network interfaces for each host.


## Running a playbook from Python ##

    $ python
    >>> import ansible.playbook
    >>> import ansible.callbacks
    >>> p = ansible.playbook.PlayBook(playbook='playbook.yml', remote_user='heat-admin', host_list='hosts', stats=ansible.callbacks.AggregateStats(), callbacks=ansible.callbacks.PlaybookCallbacks(), runner_callbacks=ansible.callbacks.PlaybookRunnerCallbacks(stats=ansible.callbacks.AggregateStats()))
    >>> p.run()


---

To see the list of all the facts ansible could gather, run:

    ansible -i hosts -u heat-admin --sudo -m setup

