#!/usr/bin/env python
# curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py"
# python get-pip.py

import argparse
import pprint
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


class CustomHandler(ansible.callbacks.PlaybookRunnerCallbacks):
    def __init__(self, stats=None):
        print 'init'
        super(CustomHandler, self).__init__(stats=stats)

    def on_ok(self, host, host_result):
        global output_data
        #print('host: %s' % host)
        #print('host_result: %s' % host_result)
        if host not in output_data:
            output_data[host] = []
        output_data[host].append(host_result)
        output_data['asdf'] = 1
        #print 'output_data: %s' % output_data


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


if __name__ == "__main__":
    sys.exit(main())
