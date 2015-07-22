#!/usr/bin/env python
# curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
# python get-pip.py

import argparse
import pprint
import subprocess
import sys
import os
import json
from ansible.playbook import PlayBook
import ansible.inventory
from ansible import callbacks
from ansible import utils
import re

#logging.basicConfig()
#LOG = logging.getLogger(__name__)
#LOG.setLevel(logging.DEBUG)  # JPEELER: change to INFO later

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


class CustomHandler(ansible.callbacks.PlaybookRunnerCallbacks):
    def __init__(self, stats=None):
        print 'init'
        super(CustomHandler, self).__init__(stats=stats)

    def on_ok(self, host, host_result):
        global output_data
        if host not in output_data:
            output_data[host] = []
        output_data[host].append(host_result)


def main():
    args = argParser()

    #group = ansible.inventory.group.Group(name='nodes')

    hostfile = open('hosts', 'w')
    output = os.popen('nova list').readlines()
    for line in output:
        m = re.search('\d+\.\d+\.\d+\.\d+', line)
        if m:
            ip = m.group(0)
            hostfile.write(ip)
            hostfile.write('\n')

    hostfile.close()

    stats = ansible.callbacks.AggregateStats()
    pb_callback = ansible.callbacks.PlaybookCallbacks()
    run_callback = CustomHandler(stats=stats)
    #run_callback = ansible.callbacks.PlaybookRunnerCallbacks(stats=stats)

    p = ansible.playbook.PlayBook(playbook='playbook.yml',
                                  remote_user='heat-admin',
                                  host_list='hosts',
                                  forks=1,
                                  stats=stats,
                                  callbacks=pb_callback,
                                  runner_callbacks=run_callback)
    output = p.run()

    f = open('ansible_run.json', 'w')
    f.write(json.dumps(output, sort_keys=True, indent=4))
    f.close()

    global output_data
    print('output_data: %s' % output_data)
    for key in output_data.keys():
        print('host: %s: %s' % (key, output_data[key]))

    discoverd_data = get_discoverd_data()
    print 'Ironic discoverd data:'
    for hwid, data in discoverd_data.items():
        print hwid, data


if __name__ == "__main__":
    sys.exit(main())
