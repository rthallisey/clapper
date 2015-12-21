#!/usr/bin/env python


DOCUMENTATION = '''
---
module: discovery_diff
short_description: Provide difference in hardware configuration
author: "Swapnil Kulkarni, @coolsvap"
'''

from ansible.module_utils.basic import *
import json
from subprocess import Popen, PIPE
import os
import sys


def get_node_hardware_data(hw_id, upenv):
    '''Read the inspector data about the given node from Swift'''
    p = Popen(('swift', 'download', '--output', '-', 'ironic-inspector', hw_id),
              env=upenv, stdout=PIPE, stderr=PIPE)
    if p.wait() == 0:
        return json.loads(p.stdout.read())

def main():

    module = AnsibleModule(
        argument_spec={}
    )

    upenv = os.environ.copy()

    with open("files/env_vars.json") as data_file:    
        env_data = json.load(data_file)

    upenv.update(env_data)

    p = Popen(('swift', 'list', 'ironic-inspector'), env=upenv, stdout=PIPE, stderr=PIPE)
    if p.wait() != 0:
        print "Error running `swift list ironic-inspector`"
        print p.stderr.read()
        sys.exit(1)

    hardware_ids = [i.strip() for i in p.stdout.read().splitlines() if i.strip()]
    hw_dicts = {}
    for hwid in hardware_ids:
        hw_dicts[hwid]=get_node_hardware_data(hwid, upenv)

    #TODO(coolsvap) find a way to compare the obtained data in meaningful manner
    result = {
        'changed': True,
        'msg': 'Discovery data for %d servers' % len(hw_dicts.keys()),
        'results': hw_dicts,
    }
    module.exit_json(**result)


if __name__ == '__main__':
    main()
