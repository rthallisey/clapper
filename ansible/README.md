# Ansible Playbooks for network configuration tests #

0. Install ansible on the undercloud
1. Create a `hosts` file with the IP addresses of the overcloud nodes (one IP per line)
2. Run `ansible-playbook -i hosts playbook.yml`

You'll get status of all the network interfaces for each host.


To see the list of all the facts ansible could gather, run:

    ansible -i hosts -u heat-admin --sudo -m setup

