import json
from subprocess import Popen, PIPE
import os
import sys


def hardware_data(hw_id):
    '''Read the discoverd data about the given node from Swift'''
    # OS_TENANT_NAME=service swift download --output - ironic-discoverd <ID>
    p = Popen(('swift', 'download', '--output', '-', 'ironic-discoverd', hw_id),
              stdout=PIPE, stderr=PIPE)
    if p.wait() == 0:
        return json.loads(p.stdout.read())


def all_equal(coll):
    if len(coll) <= 1:
        return True
    first = coll[0]
    for item in coll[1:]:
        if item != first:
            return False
    return True


if __name__ == '__main__':
    os.environ['OS_TENANT_NAME'] = 'service'
    # OS_TENANT_NAME=service swift list ironic-discoverd
    p = Popen(('swift', 'list', 'ironic-discoverd'), stdout=PIPE, stderr=PIPE)
    if p.wait() != 0:
        print "Error running `swift list ironic-discoverd`"
        print p.stderr.read()
        sys.exit(1)

    hardware_ids = [i.strip() for i in p.stdout.read().splitlines() if i.strip()]
    hardware = [hardware_data(i) for i in hardware_ids]

    hw_dicts = []
    for hw in hardware:
        hw_dict = {}
        for item in hw:
            key = '/'.join(item[:-1])
            value = item[-1]
            hw_dict[key] = value
        hw_dicts.append(hw_dict)

    all_keys = set()
    for hw in hw_dicts:
        all_keys.update(hw.keys())

    system_id_key = 'system/product/uuid'
    print "System ID by %s:" % system_id_key
    for num, hw in enumerate(hw_dicts):
        print '[%d]: %s' % (num, hw[system_id_key])
    print

    for key in all_keys:
        values = [hw.get(key) for hw in hw_dicts]
        if key != system_id_key and not all_equal(values):
            print '%s:' % key
            for num, value in enumerate(values):
                print '[%d] %s' % (num, value)
            print
