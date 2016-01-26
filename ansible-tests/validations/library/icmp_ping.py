#!/usr/bin/env python

from ansible.module_utils.basic import *

DOCUMENTATION = '''
---
module: icmp_ping
short_description: ICMP ping remote hosts
requirements: [ ping ]
description:
    - Check host connectivity with ICMP ping.
options:
    host:
        required: true
        description:
            - IP address or hostname of host to ping
        type: str
author: "Martin Andre (@mandre)"
'''

EXAMPLES = '''
# Ping host:
- icmp: name=somegroup state=present
- hosts: webservers
  tasks:
    - name: Check Internet connectivity
      ping: host="www.ansible.com"
'''


def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(required=True, type='str'),
        )
    )

    host = module.params.pop('host')
    result = module.run_command('ping -c 1 {}'.format(host))
    failed = (result[0] != 0)
    msg = result[1] if result[1] else result[2]

    module.exit_json(changed=False, failed=failed, msg=msg)


if __name__ == '__main__':
    main()
