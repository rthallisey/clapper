#!/usr/bin/env python
# curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
# python get-pip.py

import argparse
import json
import os
import pprint
import re
import subprocess
import sys

from ansible.runner import Runner

# logging.basicConfig()
# LOG = logging.getLogger(__name__)
# LOG.setLevel(logging.DEBUG)  # JPEELER: change to INFO later


def argParser():
    parser = argparse.ArgumentParser(description='Clapper')

    # parser.add_argument('-h', '--help',
    #                     help='List help',
    #                     action='store_true')

    return vars(parser.parse_args())

output_data = {}


def run(cmd, env):
    '''Run a process in the given environment.

    Returns tuple: (return code, stdout, stderr).
    '''
    e = os.environ.copy()
    e.update(env)
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, env=e)
    stdout, stderr = process.communicate()
    return_code = process.wait()
    return (return_code, stdout, stderr)


def get_discoverd_data():
    '''Gather ironic-discoverd output from Swift.'''
    result = {}
    env = {'OS_TENANT_NAME': 'service'}
    code, stdout, stderr = run(('swift', 'list', 'ironic-discoverd'), env)
    assert code == 0
    for name in stdout.splitlines():
        cmd = ('swift', 'download', '--output', '-', 'ironic-discoverd', name)
        code, object, stderr = run(cmd, env)
        assert code == 0
        result[name] = json.loads(object)
    return result


def heat_config_check():
    heat_config_runner = Runner(host_list='hosts',
                                module_name='heat_config',
                                remote_user='heat-admin',
                                become=True,
                                module_args='')
    run_result = heat_config_runner.run()
    heat_config = {}
    for k, v in run_result['contacted'].items():
        heat_config[k] = v['ansible_facts']

    discoverd_data = get_discoverd_data()
    print '\n\nIronic discoverd data:'
    for hwid, data in discoverd_data.items():
        print hwid, data

    # NOTE(shadower): the entire heat_config is HUGE
    print '\n\nos-net-config input:'
    for ip, config in heat_config.items():
        print ip
        pprint.pprint(config['complete'].get('os_net_config', {}))
    pprint.pprint(heat_config)


def network_verify():
    heat_config_runner = Runner(host_list='hosts',
                                module_name='network_check',
                                remote_user='heat-admin',
                                become=True,
                                module_args='')
    run_result = heat_config_runner.run()
    heat_config = {}
    for k, v in run_result['contacted'].items():
        heat_config[k] = v['ansible_facts']


def main():
    # group = ansible.inventory.group.Group(name='nodes')

    hostfile = open('hosts', 'w')
    output = os.popen('nova list').readlines()
    for line in output:
        m = re.search('\d+\.\d+\.\d+\.\d+', line)
        if m:
            ip = m.group(0)
            hostfile.write(ip)
            hostfile.write('\n')

    hostfile.close()

    heat_config_check()


if __name__ == "__main__":
    sys.exit(main())
